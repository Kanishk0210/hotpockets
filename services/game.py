from database import firebase_conn as fs_db
from models.GameTracker import GameTrackerEndRequest
from models.BillTracker import BillTracker, Mode
from util import util, constants
from services import daily_collect

def process_generate_bill_old(gt_end: GameTrackerEndRequest):
    try:
        # fetch game tracker
        gt_doc = fs_db.get_by_id_trans(gt_end.Id)
        print(gt_doc)
        # update player isPlaying False
        for player in gt_doc.get('Players'):
            fs_db.update_target(player.get('Id'), {"isPlaying": False})

        canteen_cost = 0

        if gt_doc.get('CanteenTrackerId', None) is not None:
            # fetch canteen tracker
            ct_doc = fs_db.get_by_id_trans(gt_doc.get("CanteenTrackerId"))
            canteen_cost = ct_doc.get("Cost",0)
            if canteen_cost is None:
                canteen_cost = 0
        
        # fetch game
        game_doc = fs_db.get_by_id(gt_doc.get('GameId'))
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
        
        fs_db.add_trans(constants.BILL_TRACKER, bill_tracker.dict())

        # update canteen tracker 
        ct_update = {
            "isActive": False
        }
        ct_id = gt_doc.get('CanteenTrackerId', None)
        if ct_id is not None:
            fs_db.update_trans(gt_doc.get('CanteenTrackerId'), ct_update)

        return True
    except Exception as e:
        print(e)
        return False

def process_generate_bill(gt_id: str):
    try:
        # fetch game tracker
        gt_doc = fs_db.get_by_id_trans(gt_id)
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
            ct_doc = fs_db.get_by_id_trans(gt_doc.get("CanteenTrackerId"))

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
                pending_bills = fs_db.check_pending_bill(player['Id'])
                print(pending_bills)
                count = len(pending_bills)
                print(count)
                
                if count>0:
                    pending_bill = pending_bills[0]
                    pending_bill['CanteenCost'] += player['Cost']
                    if player['Id'] in gt_doc['GamePlayers']:
                        pending_bill['GameCost'] += div_game_cost
                    pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                    fs_db.update_trans(pending_bill['Id'], pending_bill)
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
                        fs_db.add_trans(constants.BILL_TRACKER, bill_tracker)
        for player in gt_doc.get('Players',[]):
            if player['Id'] not in ct_plyr_ids:
                # generate bill for all players
                # check for pending bill
                pending_bills = fs_db.check_pending_bill(player['Id'])
                count = sum(1 for doc in pending_bills)
                print(count)
                
                if count>0:
                    pending_bill = pending_bills[0]
                    if player['Id'] in gt_doc['GamePlayers']:
                        pending_bill['GameCost'] += div_game_cost
                    pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                    fs_db.update_trans(pending_bill['Id'], pending_bill)
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
                        fs_db.add_trans(constants.BILL_TRACKER, bill_tracker)

        # update game tracker
        gt_update = {
            "isBilled": True
        }
        fs_db.update_trans(gt_id, gt_update)

        # update canteen tracker 
        ct_update = {
            "isActive": False
        }
        ct_id = gt_doc.get('CanteenTrackerId', None)
        if ct_id is not None:
            fs_db.update_trans(gt_doc.get('CanteenTrackerId'), ct_update)
        return True
    except Exception as e:
        print(e)
        return False

def process_pay_bill(bt_id: str, modes: {}, discount):
    try:
        # if already paid
        bt_doc = fs_db.get_by_id_trans(bt_id)
        if bt_doc["isPaid"] is True:
            return True
        # set isPaid True
        bt_update = {
            "isPaid": True,
            "Mode": modes,
            "Discount": discount
        }
        fs_db.update_trans(bt_id, bt_update)
        # save cash to safe
        daily_collect.save_cash(sum(modes["Cash"]))

        # set Mode
        # if credit add credit to player
        return True
    except Exception as e:
        print(e)
        return False
    
def process_end_game(gt_end: GameTrackerEndRequest):
    try:
        # fetch game tracker
        gt_doc = fs_db.get_by_id_trans(gt_end.Id)
        print(gt_doc)
        # if already ended
        if gt_doc["isActive"] is False:
            print(gt_doc["Id"]," :Game already active: Return")
            return True
        
        plyr_cnt = 0
        # update player isPlaying False
        for player in gt_doc.get('Players'):
            fs_db.update_target(player.get('Id'), {"isPlaying": False})
            plyr_cnt += 1

        # calculate game cost
        game_cost = 0

        # fetch game
        game_doc = fs_db.get_by_id(gt_doc.get('GameId'))
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
        if dur<=game_doc.get('CancelTime', 0):
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
        fs_db.update_trans(gt_end.Id, gt_update)
        return True
    except Exception as e:
        print(e)
        return False

def process_ind_canteen_generate_bill(ct_id: str):
    try:
        # fetch canteen tracker
        ct_doc = fs_db.get_by_id_trans(ct_id)
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
            pending_bills = fs_db.check_pending_bill(player['Id'])
            print(pending_bills)
            count = len(pending_bills)
            print(count)
            
            if count>0:
                pending_bill = pending_bills[0]
                pending_bill['CanteenCost'] += player['Cost']
                pending_bill['GameCost'] += div_game_cost
                pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                fs_db.update_trans(pending_bill['Id'], pending_bill)
            else:
                bill_tracker = BillTracker(ct_id, None, None, player['Id'])
                bill_tracker = bill_tracker.dict()
                bill_tracker['CanteenCost'] = player['Cost']
                bill_tracker['GameCost'] = div_game_cost
                bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                bill_tracker['Player'] = player
                if bill_tracker['TotalCost'] != 0:
                    fs_db.add_trans(constants.BILL_TRACKER, bill_tracker)

        # update canteen tracker 
        ct_update = {
            "isActive": False,
            "isBilled": True
        }
        fs_db.update_trans(ct_id, ct_update)
        return True
    except Exception as e:
        print(e)
        return False
