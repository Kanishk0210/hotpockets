from database import firebase_conn as fs_db
from models.GameTracker import GameTrackerEndRequest
from models.BillTracker import BillTracker
from util import util, constants

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
        game_cost = (dur*cost_per_min) + game_doc.get('BaseCost', 0) + game_doc.get('XPlayerCharge', 0)
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
        # update player isPlaying False
        for player in gt_doc.get('Players'):
            fs_db.update_target(player.get('Id'), {"isPlaying": False})

        # calculate game cost
        game_cost = 0

        # fetch game
        game_doc = fs_db.get_by_id(gt_doc.get('GameId'))
        cost_per_min = game_doc.get('CostPerT')/game_doc.get('T',1)
        
        # calculate dur
        dur = util.get_duration(gt_doc.get('StrtTmStmp'), gt_doc.get('EndTmStmp'), game_doc.get('CancelTime', 0))

        # calculate bill
        print(dur,cost_per_min,game_doc.get('BaseCost', 0),game_doc.get('XPlayerCharge', 0))
        game_cost = (dur*cost_per_min) + game_doc.get('BaseCost', 0) + game_doc.get('XPlayerCharge', 0)

        div_game_cost = game_cost//len(gt_doc['GamePlayers'])

        if gt_doc.get('CanteenTrackerId', None) is not None:
            # fetch canteen tracker
            ct_doc = fs_db.get_by_id_trans(gt_doc.get("CanteenTrackerId"))

            # generate bill for all players
            for player in ct_doc.get('Players',[]):
                # check for pending bill
                pending_bills = fs_db.check_pending_bill(player['Id'])
                count = sum(1 for doc in pending_bills)
                print(count)
                pending_bill = pending_bills[0].to_dict()
                if count>0:
                    pending_bill['CanteenCost'] += player['Cost']
                    if player['Id'] in gt_doc['GamePlayers']:
                        pending_bill['GameCost'] += div_game_cost
                    pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                    fs_db.update_trans(pending_bill['Id'], pending_bill)
                else:
                    bill_tracker = BillTracker(gt_doc.get('CanteenTrackerId', None), gt_doc.get('Id'), gt_doc.get("GameId"))
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
        else:
            for player in gt_doc.get('Players',[]):
                # generate bill for all players
                # check for pending bill
                pending_bills = fs_db.check_pending_bill(player['Id'])
                count = sum(1 for doc in pending_bills)
                print(count)
                pending_bill = pending_bills[0].to_dict()
                if count>0:
                    if player['Id'] in gt_doc['GamePlayers']:
                        pending_bill['GameCost'] += div_game_cost
                    pending_bill['TotalCost'] = pending_bill['CanteenCost'] + pending_bill['GameCost']
                    fs_db.update_trans(pending_bill['Id'], pending_bill)
                else:
                    bill_tracker = BillTracker(gt_doc.get('CanteenTrackerId', None), gt_doc.get('Id'), gt_doc.get("GameId"))
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
            "DurationInMin": dur,
            "Cost": game_cost,
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



def process_end_game(gt_end: GameTrackerEndRequest):
    # update game tracker end tmstmp, dur, bill
    gt_update = {
        "EndTmStmp": gt_end.EndTmStmp,
        #"DurationInMin": dur,
        #"Cost": game_cost,
        "isActive": False
    }
    fs_db.update_trans(gt_end.Id, gt_update)
    return True
