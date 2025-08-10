from database.firebase_conn import FirebaseConn
from models.GameTracker import GameTrackerEndRequest
from models.BillTracker import BillTracker, Mode
from models.Audit import Audit
from models.Credit import Credit
from util import util, constants
from services.daily_collect import DailyCollectService

class GameService:
    def __init__(self, fs_db: FirebaseConn):
        self.fs_db = fs_db
        self.daily_collect = DailyCollectService(fs_db)

    def process_generate_bill_old(self, gt_end: GameTrackerEndRequest, audit: Audit):
        try:
            # fetch game tracker
            gt_doc = self.fs_db.get_by_id_trans(gt_end.Id)
            print(gt_doc)
            # update player isPlaying False
            for player in gt_doc.get('Players'):
                self.fs_db.update_target(player.get('Id'), {"isPlaying": False}, audit)

            canteen_cost = 0

            if gt_doc.get('CanteenTrackerId', None) is not None:
                # fetch canteen tracker
                ct_doc = self.fs_db.get_by_id_trans(gt_doc.get("CanteenTrackerId"))
                canteen_cost = ct_doc.get("Cost",0)
                if canteen_cost is None:
                    canteen_cost = 0
            
            # fetch game
            game_doc = self.fs_db.get_by_id(gt_doc.get('GameId'))
            cost_per_min = game_doc.get('CostPerT')/game_doc.get('T',1)
            
            # calculate dur
            dur = util.get_duration(gt_doc.get('StrtTmStmp'), gt_end.EndTmStmp, game_doc.get('CancelTime', 0))

            # calculate bill
            print(dur,cost_per_min,game_doc.get('BaseCost', 0),game_doc.get('XPlayerCharge', 0))
            game_cost = (dur*cost_per_min) + game_doc.get('XPlayerCharge', 0)
            if  game_cost < game_doc.get('BaseCost', 0):
                game_cost = game_doc.get('BaseCost', 0)
            print(game_cost,canteen_cost)
            # calculate total cost
            total_cost = game_cost + canteen_cost

            # generate bill tracker
            bill_tracker = BillTracker(None, gt_doc.get('Id'), game_cost, canteen_cost, 
                total_cost, False, gt_doc.get("GameId"))
            
            self.fs_db.add_trans(constants.BILL_TRACKER, bill_tracker.dict(), audit)

            # update canteen tracker 
            ct_update = {
                "isActive": False
            }
            ct_id = gt_doc.get('CanteenTrackerId', None)
            if ct_id is not None:
                self.fs_db.update_trans(gt_doc.get('CanteenTrackerId'), ct_update, audit)

            return True
        except Exception as e:
            print(e)
            return False

    def process_generate_bill2(self, gt_id: str, audit: Audit):
        try:
            # fetch game tracker
            gt_doc = self.fs_db.get_by_id_trans(gt_id)
            print(gt_doc)
            # if already billed
            if gt_doc["isBilled"] is True:
                return True
            
            game_cost = gt_doc["Cost"]

            dur = gt_doc["DurationInMin"]

            div_game_cost = round(game_cost//len(gt_doc['GamePlayers']))

            ct_plyr_ids=[]

            if gt_doc.get('CanteenTrackerId', None) is not None:
                # fetch canteen tracker
                ct_doc = self.fs_db.get_by_id_trans(gt_doc.get("CanteenTrackerId"))

                # add table canteen cost if present
                menus = ct_doc.get("MenuItems", None)
                table_canteen_cost = 0
                if menus is not None:
                    for menu in menus:
                        table_canteen_cost += menu["Cost"]* menu["Quan"]

                div_game_cost = round((game_cost+table_canteen_cost)/len(gt_doc['GamePlayers']))

                # generate bill for all players
                for player in ct_doc.get('Players',[]):
                    ct_plyr_ids.append(player['Id'])
                    # check for pending bill
                    pending_bills = self.fs_db.check_pending_bill(player['Id'])
                    print(pending_bills)
                    count = len(pending_bills)
                    print(count)
                    
                    if count>0:
                        pending_bill = pending_bills[0]
                        pending_bill['CanteenCost'] += player['Cost']
                        if player['Id'] in gt_doc['GamePlayers']:
                            pending_bill['GameCost'] += div_game_cost
                        pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                        self.fs_db.update_trans(pending_bill['Id'], pending_bill, audit)
                    else:
                        bill_tracker = BillTracker(gt_doc.get('CanteenTrackerId', None), gt_doc.get('Id'), gt_doc.get("GameId"), player['Id'])
                        bill_tracker = bill_tracker.dict()
                        bill_tracker['CanteenCost'] = player['Cost']
                        if player['Id'] in gt_doc['GamePlayers']:
                            bill_tracker['GameCost'] = div_game_cost
                        else:
                            bill_tracker['GameCost'] = 0
                        bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                        bill_tracker['Player'] = player
                        if bill_tracker['TotalCost'] != 0:
                            self.fs_db.add_trans(constants.BILL_TRACKER, bill_tracker, audit)
            for player in gt_doc.get('Players',[]):
                if player['Id'] not in ct_plyr_ids:
                    # generate bill for all players
                    # check for pending bill
                    pending_bills = self.fs_db.check_pending_bill(player['Id'])
                    count = sum(1 for doc in pending_bills)
                    print(count)
                    
                    if count>0:
                        pending_bill = pending_bills[0]
                        if player['Id'] in gt_doc['GamePlayers']:
                            pending_bill['GameCost'] += div_game_cost
                        pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                        self.fs_db.update_trans(pending_bill['Id'], pending_bill, audit)
                    else:
                        bill_tracker = BillTracker(gt_doc.get('CanteenTrackerId', None), gt_doc.get('Id'), gt_doc.get("GameId"),player['Id'])
                        bill_tracker = bill_tracker.dict()
                        bill_tracker['CanteenCost'] = 0
                        if player['Id'] in gt_doc['GamePlayers']:
                            bill_tracker['GameCost'] = div_game_cost
                        else:
                            bill_tracker['GameCost'] = 0
                        bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                        if bill_tracker['TotalCost'] != 0:
                            self.fs_db.add_trans(constants.BILL_TRACKER, bill_tracker, audit)

            # update game tracker
            gt_update = {
                "isBilled": True
            }
            self.fs_db.update_trans(gt_id, gt_update, audit)

            # update canteen tracker 
            ct_update = {
                "isActive": False
            }
            ct_id = gt_doc.get('CanteenTrackerId', None)
            if ct_id is not None:
                self.fs_db.update_trans(gt_doc.get('CanteenTrackerId'), ct_update, audit)
            return True
        except Exception as e:
            print(e)
            return False

#new
    def process_generate_bill(self, gt_id: str, audit: Audit):
        try:
            # fetch game tracker
            gt_doc = self.fs_db.get_by_id_trans(gt_id)
            print(gt_doc)
            # if already billed
            if gt_doc["isBilled"] is True:
                return True

            game_cost = gt_doc["Cost"]
            dur = gt_doc["DurationInMin"]
            div_game_cost = round(game_cost // len(gt_doc['GamePlayers']))
            ct_plyr_ids = []

            if gt_doc.get('CanteenTrackerId', None) is not None:
                # fetch canteen tracker
                ct_doc = self.fs_db.get_by_id_trans(gt_doc.get("CanteenTrackerId"))

                # add table canteen cost if present
                menus = ct_doc.get("MenuItems", None)
                table_canteen_cost = 0
                if menus is not None:
                    for menu in menus:
                        table_canteen_cost += menu["Cost"] * menu["Quan"]

                div_game_cost = round((game_cost + table_canteen_cost) / len(gt_doc['GamePlayers']))

                # generate bill for all players
                for player in ct_doc.get('Players', []):
                    player_id = player['Id']
                    ct_plyr_ids.append(player_id)
                    # check for pending bill
                    pending_bills = self.fs_db.check_pending_bill(player_id)
                    count = len(pending_bills)

                    if count > 0:
                        pending_bill = pending_bills[0]
                        pending_bill['CanteenCost'] += player['Cost']
                        if player_id in gt_doc['GamePlayers']:
                            pending_bill['GameCost'] += div_game_cost
                        pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                        self.fs_db.update_trans(pending_bill['Id'], pending_bill, audit)
                    else:
                        bill_tracker = BillTracker(gt_doc.get('CanteenTrackerId', None), gt_doc.get('Id'), gt_doc.get("GameId"), player_id)
                        bill_tracker = bill_tracker.dict()
                        bill_tracker['CanteenCost'] = player['Cost']
                        if player_id in gt_doc['GamePlayers']:
                            bill_tracker['GameCost'] = div_game_cost
                        else:
                            bill_tracker['GameCost'] = 0
                        bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                        bill_tracker['Player'] = player
                        if bill_tracker['TotalCost'] != 0:
                            self.fs_db.add_trans(constants.BILL_TRACKER, bill_tracker, audit)

            for player in gt_doc.get('Players',[]):
                if player['Id'] not in ct_plyr_ids:
                    # generate bill for all players
                    # check for pending bill
                    pending_bills = self.fs_db.check_pending_bill(player['Id'])
                    count = sum(1 for doc in pending_bills)
                    print(count)
                    
                    if count>0:
                        pending_bill = pending_bills[0]
                        if player['Id'] in gt_doc['GamePlayers']:
                            pending_bill['GameCost'] += div_game_cost
                        pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                        self.fs_db.update_trans(pending_bill['Id'], pending_bill, audit)
                    else:
                        bill_tracker = BillTracker(gt_doc.get('CanteenTrackerId', None), gt_doc.get('Id'), gt_doc.get("GameId"),player['Id'])
                        bill_tracker = bill_tracker.dict()
                        bill_tracker['CanteenCost'] = 0
                        if player['Id'] in gt_doc['GamePlayers']:
                            bill_tracker['GameCost'] = div_game_cost
                        else:
                            bill_tracker['GameCost'] = 0
                        bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                        if bill_tracker['TotalCost'] != 0:
                            self.fs_db.add_trans(constants.BILL_TRACKER, bill_tracker, audit)

            # update game tracker
            gt_update = {
                "isBilled": True
            }
            self.fs_db.update_trans(gt_id, gt_update, audit)

            # update canteen tracker 
            ct_update = {
                "isActive": False
            }
            ct_id = gt_doc.get('CanteenTrackerId', None)
            if ct_id is not None:
                self.fs_db.update_trans(gt_doc.get('CanteenTrackerId'), ct_update, audit)
            return True
        except Exception as e:
            print(e)
            return False




#new

    def process_pay_bill(self, bt_id: str, modes: {}, discount, audit: Audit):
        try:
            # if already paid
            bt_doc = self.fs_db.get_by_id_trans(bt_id)
            if bt_doc["isPaid"] is True:
                return True
            # set isPaid True
            bt_update = {
                "isPaid": True,
                "Mode": modes,
                "Discount": discount
            }
            self.fs_db.update_trans(bt_id, bt_update, audit)
            # save cash to safe
            print(modes["Cash"])
            print(sum(modes["Cash"]))
            self.daily_collect.save_cash(sum(modes["Cash"]), audit)

            # set Mode
            # if credit add credit to player
            if modes.get("Credit") and sum(modes["Credit"]) > 0:
                player_id = bt_doc["PlayerId"]
                player_doc = self.fs_db.get_by_id(player_id)
                if player_doc:
                    current_credit = player_doc.get("Credit", 0)
                    new_credit = current_credit + sum(modes["Credit"])
                    player_update = {"Credit": new_credit}
                    self.fs_db.update_target(player_id, player_update, audit)

                    # Check if a Credit document already exists for this player.  If not, create one.
                    credit_id = constants.CREDIT + "::" + player_id
                    credit_doc = self.fs_db.get_by_id_trans(credit_id)
                    if not credit_doc:
                        cr = player_doc["Credit"]
                        credit_doc = Credit(Id=credit_id, PlayerId=player_id, Credit=cr).dict()
                        self.fs_db.add_trans_by_id(credit_id, credit_doc, audit)
                    else:
                        credit_doc["Credit"] = new_credit
                        self.fs_db.update_trans(credit_id, credit_doc, audit)
            return True
        except Exception as e:
            print(e)
            return False
        
    def process_end_game(self, gt_end: GameTrackerEndRequest, audit: Audit):
        try:
            # fetch game tracker
            gt_doc = self.fs_db.get_by_id_trans(gt_end.Id)
            print(gt_doc)
            # if already ended
            if gt_doc["isActive"] is False:
                print(gt_doc["Id"]," :Game already active: Return")
                return True
            
            plyr_cnt = 0
            # update player isPlaying False
            for player in gt_doc.get('Players'):
                self.fs_db.update_target(player.get('Id'), {"isPlaying": False}, audit)
                plyr_cnt += 1

            # calculate game cost
            game_cost = 0

            # fetch game
            game_doc = self.fs_db.get_by_id(gt_doc.get('GameId'))
            cost_per_min = game_doc.get('CostPerT')/game_doc.get('T',1)
            
            # calculate dur
            dur = util.get_duration(gt_doc.get('StrtTmStmp'), gt_end.EndTmStmp, game_doc.get('CancelTime', 0))

            # calculate bill
            print(dur,cost_per_min,game_doc.get('BaseCost', 0),game_doc.get('XPlayerCharge', 0))
            game_cost = (dur*cost_per_min)

            if game_cost < game_doc.get('BaseCost', 0):
                game_cost = game_doc.get('BaseCost', 0)
            x_plyr_chrg = 0

            if plyr_cnt >4:
                x_plyr_chrg = game_doc.get('XPlayerCharge', 0) * (plyr_cnt-4)

            game_cost += x_plyr_chrg
            
            game_cost = round(game_cost)

            isCancelled = False
            if dur<=game_doc.get('CancelTime', 0) and gt_doc.get('CanteenTrackerId') is None:
                isCancelled = True

            # update game tracker end tmstmp, dur, bill
            gt_update = {
                "EndTmStmp": gt_end.EndTmStmp,
                "DurationInMin": dur,
                "Cost": game_cost,
                "isActive": False,
                "BaseCost": game_doc.get('BaseCost', 0),
                "XPlayerCharge": x_plyr_chrg,
                "GamePlayCost": round(dur*cost_per_min),
                "isCancelled": isCancelled,
                "GamePlayers": gt_end.GamePlayers
            }
            self.fs_db.update_trans(gt_end.Id, gt_update, audit)
            return True
        except Exception as e:
            print(e)
            return False

    def process_ind_canteen_generate_bill(self, ct_id: str, audit: Audit):
        try:
            # fetch canteen tracker
            ct_doc = self.fs_db.get_by_id_trans(ct_id)
            print(ct_doc)
            # if already billed
            if ct_doc["isBilled"] is True:
                return True

            ct_plyr_ids=[]
            div_game_cost = 0

            # generate bill for ind canteen player
            for player in ct_doc.get('Players',[]):
                ct_plyr_ids.append(player['Id'])
                # check for pending bill
                pending_bills = self.fs_db.check_pending_bill(player['Id'])
                print(pending_bills)
                count = len(pending_bills)
                print(count)
                
                if count>0:
                    pending_bill = pending_bills[0]
                    pending_bill['CanteenCost'] += player['Cost']
                    pending_bill['GameCost'] += div_game_cost
                    pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                    self.fs_db.update_trans(pending_bill['Id'], pending_bill, audit)
                else:
                    bill_tracker = BillTracker(ct_id, None, None, player['Id'])
                    bill_tracker = bill_tracker.dict()
                    bill_tracker['CanteenCost'] = player['Cost']
                    bill_tracker['GameCost'] = div_game_cost
                    bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                    bill_tracker['Player'] = player
                    if bill_tracker['TotalCost'] != 0:
                        self.fs_db.add_trans(constants.BILL_TRACKER, bill_tracker, audit)

            # update canteen tracker 
            ct_update = {
                "isActive": False,
                "isBilled": True
            }
            self.fs_db.update_trans(ct_id, ct_update, audit)
            return True
        except Exception as e:
            print(e)
            return False
