from database.firebase_conn import FirebaseConn
from models.GameTracker import GameTrackerEndRequest
from models.BillTracker import BillTracker, Mode
from models.Audit import Audit
from models.Credit import Credit
from util import util, constants
from services.daily_collect import DailyCollectService
from google.cloud.firestore_v1.base_query import FieldFilter

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
        """Generate bills for game and canteen with transaction safety"""
        def transaction_operation(transaction):
            # Fetch game tracker within transaction
            gt_ref = self.fs_db.trans_coll.document(gt_id)
            gt_doc = gt_ref.get(transaction=transaction).to_dict()
            
            # Early return if already billed
            if gt_doc["isBilled"] is True:
                return True

            game_cost = gt_doc["Cost"]
            div_game_cost = round(game_cost // len(gt_doc['GamePlayers']))
            ct_plyr_ids = set()  # Using set for faster lookups
            bills_to_create = []
            bills_to_update = {}

            if gt_doc.get('CanteenTrackerId'):
                # Fetch canteen tracker within transaction
                ct_ref = self.fs_db.trans_coll.document(gt_doc['CanteenTrackerId'])
                ct_doc = ct_ref.get(transaction=transaction).to_dict()

                # Calculate table canteen cost
                table_canteen_cost = sum(
                    menu["Cost"] * menu["Quan"]
                    for menu in ct_doc.get("MenuItems", []) or []
                )
                div_game_cost = round((game_cost + table_canteen_cost) / len(gt_doc['GamePlayers']))

                # Process canteen players
                for player in ct_doc.get('Players', []):
                    player_id = player['Id']
                    ct_plyr_ids.add(player_id)
                    
                    # Get pending bills in transaction
                    query = (self.fs_db.trans_coll
                            .where(filter=FieldFilter('Type', '==', constants.BILL_TRACKER))
                            .where(filter=FieldFilter('PlayerId', '==', player_id))
                            .where(filter=FieldFilter('isPaid', '==', False))
                            .limit(1))
                    pending_bills = list(query.stream(transaction=transaction))

                    if pending_bills:
                        # Update existing bill
                        pending_bill = pending_bills[0].to_dict()
                        pending_bill['CanteenCost'] += player['Cost']
                        if player_id in gt_doc['GamePlayers']:
                            pending_bill['GameCost'] += div_game_cost
                        pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                        bills_to_update[pending_bills[0].id] = pending_bill
                    else:
                        # Create new bill
                        bill_tracker = BillTracker(
                            gt_doc.get('CanteenTrackerId'), 
                            gt_doc.get('Id'), 
                            gt_doc.get("GameId"), 
                            player_id
                        ).dict()
                        bill_tracker['CanteenCost'] = player['Cost']
                        bill_tracker['GameCost'] = div_game_cost if player_id in gt_doc['GamePlayers'] else 0
                        bill_tracker['TotalCost'] = bill_tracker['CanteenCost'] + bill_tracker['GameCost']
                        bill_tracker['Player'] = player
                        if bill_tracker['TotalCost'] != 0:
                            bills_to_create.append(bill_tracker)

            # Process game players not in canteen
            for player in gt_doc.get('Players',[]):
                player_id = player['Id']
                if player_id not in ct_plyr_ids:
                    query = (self.fs_db.trans_coll
                            .where(filter=FieldFilter('Type', '==', constants.BILL_TRACKER))
                            .where(filter=FieldFilter('PlayerId', '==', player_id))
                            .where(filter=FieldFilter('isPaid', '==', False))
                            .limit(1))
                    pending_bills = list(query.stream(transaction=transaction))

                    if pending_bills:
                        pending_bill = pending_bills[0].to_dict()
                        if player_id in gt_doc['GamePlayers']:
                            pending_bill['GameCost'] += div_game_cost
                            pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                            bills_to_update[pending_bills[0].id] = pending_bill
                    else:
                        bill_tracker = BillTracker(
                            gt_doc.get('CanteenTrackerId'),
                            gt_doc.get('Id'),
                            gt_doc.get("GameId"),
                            player_id
                        ).dict()
                        bill_tracker['CanteenCost'] = 0
                        bill_tracker['GameCost'] = div_game_cost if player_id in gt_doc['GamePlayers'] else 0
                        bill_tracker['TotalCost'] = bill_tracker['GameCost']
                        if bill_tracker['TotalCost'] != 0:
                            bills_to_create.append(bill_tracker)

            # Execute all updates in transaction
            # Update existing bills
            for bill_id, bill_data in bills_to_update.items():
                bill_ref = self.fs_db.trans_coll.document(bill_id)
                transaction.update(bill_ref, bill_data)
                self.fs_db.audit_log(audit, bill_id, constants.BILL_TRACKER, 
                                   constants.AC_UPDATE, bill_ref.get(transaction=transaction).to_dict(), bill_data)

            # Create new bills
            for bill_data in bills_to_create:
                bill_id = self.fs_db.get_next_id(constants.BILL_TRACKER)
                bill_ref = self.fs_db.trans_coll.document(f"{constants.BILL_TRACKER}::{bill_id}")
                transaction.set(bill_ref, bill_data)
                self.fs_db.audit_log(audit, bill_id, constants.BILL_TRACKER, 
                                   constants.AC_ADD, None, bill_data)

            # Update game tracker
            transaction.update(gt_ref, {"isBilled": True})
            self.fs_db.audit_log(audit, gt_id, constants.GAME_TRACKER, 
                               constants.AC_UPDATE, gt_doc, {"isBilled": True})

            # Update canteen tracker if exists
            if gt_doc.get('CanteenTrackerId'):
                ct_ref = self.fs_db.trans_coll.document(gt_doc['CanteenTrackerId'])
                transaction.update(ct_ref, {"isActive": False})
                self.fs_db.audit_log(audit, gt_doc['CanteenTrackerId'], 
                                   constants.CANTEEN_TRACKER, constants.AC_UPDATE, 
                                   ct_doc, {"isActive": False})
            
            return True

        try:
            # Run the transaction using the FirebaseConn transaction runner
            result = self.fs_db.run_transaction(transaction_operation)
            return result if result is not None else True
        except Exception as e:
            print(f"Error in process_generate_bill: {e}")
            return False




#new

    def process_pay_bill(self, bt_id: str, modes: dict = None, discount=0, audit: Audit = None):
        """Process bill payment with transaction safety"""
        try:
            # Validate bt_id
            if not bt_id or bt_id == "null" or bt_id.lower() == "null":
                print(f"Invalid bill tracker ID provided: {bt_id}")
                return False
                
            if not audit:
                print("Audit parameter is required")
                return False

            # Print debug info
            print(f"Processing bill payment for ID: {bt_id}")
            print(f"Payment modes: {modes}")
            print(f"Discount: {discount}")

            # Initialize modes if None
            modes = modes or {}
            
            def transaction_operation(transaction):
                # Fetch bill tracker within transaction
                try:
                    bt_ref = self.fs_db.trans_coll.document(bt_id)
                    bt_snapshot = bt_ref.get(transaction=transaction)
                    if not bt_snapshot.exists:
                        print(f"Bill tracker document does not exist: {bt_id}")
                        return False
                        
                    bt_doc = bt_snapshot.to_dict()
                    if not bt_doc:
                        print(f"Bill tracker document is empty: {bt_id}")
                        return False
                        
                    print(f"Successfully fetched bill tracker: {bt_id}")
                    print(f"Document data: {bt_doc}")
                except Exception as e:
                    print(f"Error fetching bill tracker {bt_id}: {str(e)}")
                    return False
                
                # Early return if already paid
                if bt_doc.get("isPaid", False):
                    return True

                # Update bill tracker with payment info
                bt_update = {
                    "isPaid": True,
                    "Mode": modes,
                    "Discount": discount or 0
                }
                transaction.update(bt_ref, bt_update)
                self.fs_db.audit_log(audit, bt_id, constants.BILL_TRACKER, 
                                   constants.AC_UPDATE, bt_doc, bt_update)

                # Handle credit if it exists
                credit_list = modes.get("Credit", [])
                if credit_list and isinstance(credit_list, list) and sum(credit_list) > 0:
                    credit_amount = sum(credit_list)
                    player_id = bt_doc.get("PlayerId")
                    
                    if not player_id:
                        print("Player ID not found in bill tracker")
                        return False
                    
                    # Get player document within transaction
                    player_ref = self.fs_db.target_coll.document(player_id)
                    player_doc = player_ref.get(transaction=transaction).to_dict()
                    
                    if player_doc:
                        # Update player's credit
                        current_credit = player_doc.get("Credit", 0)
                        new_credit = current_credit + credit_amount
                        player_update = {"Credit": new_credit}
                        
                        transaction.update(player_ref, player_update)
                        self.fs_db.audit_log(audit, player_id, "Player", 
                                           constants.AC_UPDATE, player_doc, player_update)

                        # Handle credit document
                        credit_id = f"{constants.CREDIT}::{player_id}"
                        credit_ref = self.fs_db.trans_coll.document(credit_id)
                        credit_doc = credit_ref.get(transaction=transaction).to_dict()

                        if not credit_doc:
                            # Create new credit document
                            credit_doc = Credit(
                                Id=credit_id, 
                                PlayerId=player_id, 
                                Credit=new_credit
                            ).dict()
                            transaction.set(credit_ref, credit_doc)
                            self.fs_db.audit_log(audit, credit_id, constants.CREDIT, 
                                               constants.AC_ADD, None, credit_doc)
                        else:
                            # Update existing credit document
                            credit_doc["Credit"] = new_credit
                            transaction.update(credit_ref, credit_doc)
                            self.fs_db.audit_log(audit, credit_id, constants.CREDIT, 
                                               constants.AC_UPDATE, credit_doc, {"Credit": new_credit})
                
                return True

            # Run the transaction
            result = self.fs_db.run_transaction(transaction_operation)
            
            # Handle cash separately after transaction success since it's a different service
            if result and isinstance(modes.get("Cash"), list) and modes["Cash"]:
                try:
                    cash_amount = sum(modes["Cash"])
                    if cash_amount > 0:
                        self.daily_collect.save_cash(cash_amount, audit)
                except Exception as cash_error:
                    print(f"Error processing cash payment: {cash_error}")
                    # Don't fail the whole operation if cash processing fails
                    # The transaction was successful, and this is a separate operation
                
            return result if result is not None else True
            
        except Exception as e:
            print(f"Error in process_pay_bill: {e}")
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
