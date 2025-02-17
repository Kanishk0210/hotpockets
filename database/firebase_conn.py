import firebase_admin

from firebase_admin import credentials, db, firestore

from google.cloud.firestore_v1.base_query import FieldFilter

from util import util, constants
import sys

cred = credentials.Certificate('resources/hotpockets-test-firebase-adminsdk-4gr44-d3d84f282d.json')

#cred = credentials.Certificate('resources/firebasse-adminsdk-prod.json')

firebase_app = firebase_admin.initialize_app(cred)

store = firestore.client()

target_coll_str = 'masterdata-target'
source_coll_str = 'masterdata-source'
trans_coll_str = 'transaction-data'

player_counter_id = 'player_counter'
game_counter_id = 'game_counter'
emp_counter_id = 'emp_counter'
inv_counter_id = 'inv_counter'
rawMtrl_counter_id = 'rawMtrl_counter'
menu_item_counter_id = 'menu_item_counter'
game_tracker_counter_id = 'game_tracker_counter'
bill_tracker_counter_id = 'bill_tracker_counter'
canteen_tracker_counter_id = 'canteen_tracker_counter'

target_coll = store.collection(target_coll_str)
source_coll = store.collection(source_coll_str)
trans_coll = store.collection(trans_coll_str)

player_counter_ref = source_coll.document(player_counter_id)
game_counter_ref = source_coll.document(game_counter_id)
emp_counter_ref = source_coll.document(emp_counter_id)
inv_counter_ref = source_coll.document(inv_counter_id)
rawMtrl_counter_ref = source_coll.document(rawMtrl_counter_id)
menu_item_counter_ref = source_coll.document(menu_item_counter_id)
game_tracker_counter_ref = source_coll.document(game_tracker_counter_id)
bill_tracker_counter_ref = source_coll.document(bill_tracker_counter_id)
canteen_tracker_counter_ref = source_coll.document(canteen_tracker_counter_id)

# source
def add_dailycollect(dc: dict):
    doc_id = constants.DAILY_COLLECT+'::'+dc.get("CurrentCollectTmstmp")
    dc[constants.ID] = doc_id
    dc[constants.MDFDTMSTMP] = dc.get("CurrentCollectTmstmp")
    dc[constants.CREATEDTMSTMP] = dc.get("CurrentCollectTmstmp")
    trans_coll.add(dc, doc_id)
    return True, dc

def get_safe():
    return source_coll.document(constants.SAFE_ID).get().to_dict()

def update_safe(doc_id: str, doc: dict):
    doc_ref = source_coll.document(doc_id)
    
    doc_ref.update(doc)
    return True

# target

def get_counter_ref(typ: str):
    if typ == constants.MENU:
        return menu_item_counter_ref
    if typ == constants.INVENTORY:
        return inv_counter_ref
    if typ == constants.PLAYER:
        return player_counter_ref
    if typ == constants.GAME:
        return game_counter_ref
    if typ == constants.EMPLOYEE:
        return emp_counter_ref
    if typ == constants.RAWMTRL:
        return rawMtrl_counter_ref
    if typ == constants.GAME_TRACKER:
        return game_tracker_counter_ref
    if typ == constants.BILL_TRACKER:
        return bill_tracker_counter_ref
    if typ == constants.CANTEEN_TRACKER:
        return canteen_tracker_counter_ref
    raise Exception

def get_next_id(typ: str):
    counter_ref = get_counter_ref(typ)
    next_id = int(counter_ref.get().to_dict()[constants.CURRENTID]) + 1
    counter_ref.update({constants.CURRENTID: next_id, constants.MDFDTMSTMP: util.get_current_tmstmp_str()})
    return next_id

def get_all(typ: str):
    query = target_coll.where(filter=FieldFilter('Type','==',typ))
    return query.stream()

def get_by_id(doc_id: str):
    return target_coll.document(doc_id).get().to_dict()

def get_ct_by_gt_id(gt_id: str):
    query = trans_coll.where(filter=FieldFilter('Type','==',constants.CANTEEN_TRACKER)).where(filter=FieldFilter('isActive','==', True)).where(filter=FieldFilter('GameTrackerId','==',gt_id))
    res = query.stream()
    print(res)
    return res

def add(typ: str, doc: dict):
    doc_id = typ+'::'+str(get_next_id(typ))
    doc[constants.ID] = doc_id
    doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
    target_coll.add(doc, doc_id)
    return True, doc

def update(doc_id: str, doc: dict):
    doc_ref = target_coll.document(doc_id)
    doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    doc_ref.update(doc)
    return True

def update_rawmtrl(doc_id: str, doc: dict):
    doc_ref = target_coll.document(doc_id)
    ex_doc = doc_ref.get().to_dict()
    ex_doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    ex_doc["QuantityBox"] = ex_doc["QuantityBox"] + doc["QuantityBox"]
    ex_doc["Quantity"] = ex_doc["Quantity"] + doc["QuantityBox"]*ex_doc["QuantityPerBox"]
    doc_ref.update(ex_doc)
    return True

def delete_target(doc_id: str):
    doc_ref = target_coll.document(doc_id)
    doc_ref.delete()
    return True

# Transaction

def add_trans(typ: str, doc: dict):
    doc_id = typ+'::'+str(get_next_id(typ))
    doc[constants.ID] = doc_id
    doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
    trans_coll.add(doc, doc_id)
    return True, doc

def get_all_trans(typ: str):
    query = trans_coll.where('Type','==',typ)
    return query.stream()

def get_by_id_trans(doc_id: str):
    return trans_coll.document(doc_id).get().to_dict()

def start_game(doc: dict):
    typ = constants.GAME_TRACKER

    # duplicate check
    query = trans_coll.where('Type','==',typ).where('GameId','==',doc.get('GameId')).where('isActive','==',True)
    dup_docs = query.stream()
    count = sum(1 for d in dup_docs)
    if count >0:
        return False, doc

    doc_id = typ+'::'+str(get_next_id(typ))
    doc[constants.ID] = doc_id
    doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
    trans_coll.add(doc, doc_id)
    return True, doc

def update_target(doc_id: str, doc: dict):
    doc_ref = target_coll.document(doc_id)
    doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    doc_ref.update(doc)
    return True, doc

def update_trans(doc_id: str, doc: dict):
    doc_ref = trans_coll.document(doc_id)    
    doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    doc_ref.update(doc)
    return True, doc

def add_game_canteen(gt_id: str, doc: dict):
    gt_doc_ref = trans_coll.document(gt_id)
    gt_doc = doc_ref.get().to_dict()
    isNew = False
    if gt_doc["CanteenTrackerId"] == None:
        gt_doc["CanteenTrackerId"] = constants.CANTEEN_TRACKER +'::'+str(get_next_id(typ))
        ex_ct_doc = {
            constants.MDFDTMSTMP: util.get_current_tmstmp_str(),
            constants.CREATEDTMSTMP: util.get_current_tmstmp_str(),
            constants.ID: gt_doc["CanteenTrackerId"],
            constants.TYPE: constants.CANTEEN_TRACKER,
            "GameId": gt_doc["GameId"],
            "GameTrackerId": gt_id,
            "TxId": None,
            "isActive": True,
            "isBilled": False,
            "isCancelled": False,
            "MenuItems": [],
            "Players": []
        }
        isNew = True
    else:
        ex_ct_doc_ref = trans_coll.document(gt_doc["CanteenTrackerId"])
        ex_ct_doc = ex_ct_doc_ref.get().to_dict()

    if "PlayerId" not in doc and "PlayerId" == None:
        for mitem_to_add in doc["MenuItems"]:
            found = False
            for mitem in ex_ct_doc["MenuItems"]:
                if mitem["Id"] == mitem_to_add["Id"]:
                    mitem["Quan"] += mitem_to_add["Quan"]
                    ex_ct_doc["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                    found = True
                    break
            if not found:
                mitem_to_add_doc = get_by_id(mitem_to_add["Id"])
                mitem_to_add["Cost"] = mitem_to_add_doc["Cost"]
                mitem_to_add["Name"] = mitem_to_add_doc["Name"]
                ex_ct_doc["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                ex_ct_doc["MenuItems"].append(mitem_to_add)
    else:
        for player in ex_ct_doc["Players"]:
            if player["Id"] == doc["PlayerId"]:
                for mitem_to_add in doc["MenuItems"]:
                    found = False
                    for mitem in player["MenuItems"]:
                        if mitem["Id"] == mitem_to_add["Id"]:
                            mitem["Quan"] += mitem_to_add["Quan"]
                            player["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                            found = True
                            break
                    if not found:
                        mitem_to_add_doc = get_by_id(mitem_to_add["Id"])
                        mitem_to_add["Cost"] = mitem_to_add_doc["Cost"]
                        mitem_to_add["Name"] = mitem_to_add_doc["Name"]
                        player["MenuItems"].append(mitem_to_add)
                        player["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                break
    if isNew:
        trans_coll.add(ex_ct_doc, ex_ct_doc["ID"])
    else:
        gt_doc["CanteenTrackerId"] = ex_ct_doc["ID"]
        gt_doc_ref.update(gt_doc)
        ex_ct_doc_ref.update(ex_ct_doc)

    update_stock(doc)
    return True, ex_ct_doc

def update_stock(doc: dict):
    for mitem in doc.get("MenuItems",[]):
        mitem_doc = get_by_id(mitem["Id"])
        remaining = sys.maxsize
        for ingnt in mitem_doc["Ingredients"]:
            ingnt_doc = get_by_id(mitem_doc["RawMtrlId"])
            ingnt_doc["Quantity"] -= mitem["Quan"]*ingnt["Quantity"]
            update(ingnt_doc["Id"], ingnt_doc)

            if ingnt_doc["Quantity"] <= remaining:
                remaining = ingnt_doc["Quantity"]
        mitem_doc["Remaining"] = remaining
        update(mitem_doc["Id"], mitem_doc)

def update_stock_edit(doc: dict):
    update_stock(doc)

    for player in doc["Players"]:
        update_stock(player)

def get_remaining_stock(doc: dict):
    remaining = sys.maxsize
    for ingnt in doc["Ingredients"]:
        ingnt_doc = get_by_id(ingnt["RawMtrlId"])
        if ingnt_doc["Quantity"] < remaining:
            remaining = ingnt_doc["Quantity"]
    return remaining

def update_ct(doc_id: str, doc: dict):
    doc_ref = trans_coll.document(doc_id)
    ex_doc = doc_ref.get().to_dict()
    print(ex_doc)

    if "MenuItems" in doc and doc["MenuItems"] is not None and doc["MenuItems"] != []:
        if "MenuItems" in ex_doc and ex_doc["MenuItems"] is not None and ex_doc["MenuItems"] != []:
            for menu in doc["MenuItems"]:
                for i, ex_menu in enumerate(ex_doc["MenuItems"]):
                    if ex_menu["Id"] == menu["Id"]:
                        ex_doc["MenuItems"][i]["Quan"] += menu["Quan"]
                        break
                    else:
                        ex_doc["MenuItems"].append(menu)
    if "MenuItems" not in ex_doc or ex_doc["MenuItems"] is None or ex_doc["MenuItems"] == []:
        ex_doc["MenuItems"] = doc["MenuItems"]
    new_players = []
    for player in doc["Players"]:
        player_found = False
        if ex_doc["Players"] is None or ex_doc["Players"] == []:
            ex_doc["Players"] = []
            ex_doc["Players"].append(player)
            continue
        for ex_player in ex_doc["Players"]:
            if player["Id"] == ex_player["Id"]:
                player_found = True
                break
        if player_found:
            for menu in player["MenuItems"]:
                menu_found = False
                for i, ex_menu in enumerate(ex_player["MenuItems"]):
                    if ex_menu["Id"] == menu["Id"]:
                        ex_player["MenuItems"][i]["Quan"] += menu["Quan"]
                        menu_found = True
                        break
                if not menu_found:
                    ex_player["MenuItems"].append(menu)
                
        else:
            ex_doc["Players"].append(player)

    ex_doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    print(ex_doc)

    # update cost
    cost = 0
    players = ex_doc.get("Players", None)
    if players is not None:
        for player in players:
            player["Cost"] = 0
            menus = player.get("MenuItems", None)
            if menus is not None:
                for menu in menus:
                    if "Cost" not in player:
                        player["Cost"] = 0
                    player["Cost"] += menu["Cost"] * menu["Quan"]
                    cost += menu["Cost"] * menu["Quan"]
    ex_doc["Players"] = players

    menus = ex_doc["MenuItems"]
    
    if menus is not None:
        for menu in menus:
            cost += menu["Cost"]* menu["Quan"]
    ex_doc["Cost"] = cost

    doc_ref.update(ex_doc)
    update_stock_edit(ex_doc)
    return True, ex_doc

def get_all_pending_bills(typ: str):
    query = trans_coll.where('Type','==',typ).where('isPaid','==',False)
    return query.stream()

def get_all_paid_bills(typ: str):
    query = trans_coll.where('Type','==',typ).where('isPaid','==',True)
    return query.stream()

def get_active_game_trackers(typ: str):
    query = trans_coll.where('Type','==',typ).where('isActive','==',True)
    return query.stream()

def get_all_games(typ: str):
    games = get_all(constants.GAME)
    act_games_lst = get_active_game_trackers(constants.GAME_TRACKER)
    act_games = {}
    for act_game in act_games_lst:
        act_game_dict = act_game.to_dict()
        act_games[act_game_dict['GameId']] = act_game_dict
    games_res = {'Games':[]}
    for game in games:
        game_dict = game.to_dict()
        if game_dict['Id'] in act_games:
            game_dict['active'] = act_games[game_dict['Id']]
        games_res['Games'].append(game_dict)
    return games_res

def get_closed_not_billed_games():
    # add game name
    games = get_all(constants.GAME)
    nm_tr_map = {}
    for game in games:
        game_dict = game.to_dict()
        nm_tr_map[game_dict['Id']] = game_dict['Name']
    
    query = trans_coll.where('Type','==',constants.GAME_TRACKER).where('isActive','==',False).where('isBilled','==',False).where('isCancelled','==',False)
    bills = {'ClosedNotBilledGames':[]}
    for bill in query.stream():
        bill_doc = bill.to_dict()
        bill_doc['GameName'] = nm_tr_map[bill_doc['GameId']]
        if bill_doc['CanteenTrackerId'] is not None:
            ct_doc = get_by_id_trans(bill_doc['CanteenTrackerId'])
            bill_doc['CanteenTracker'] = ct_doc
        else:
            bill_doc['CanteenTracker'] = None
        bills['ClosedNotBilledGames'].append(bill_doc)

    return bills

def check_pending_bill(pid: str):
    query = trans_coll.where('Type','==',constants.BILL_TRACKER).where('PlayerId','==',pid).where('isPaid','==',False)
    pen_bills = []
    for bill_doc in query.stream():
        pen_bills.append(bill_doc.to_dict())
    return pen_bills

def get_all_plyr_bills(isPaid):
    # add game name
    games = get_all(constants.GAME)
    nm_tr_map = {}
    for game in games:
        game_dict = game.to_dict()
        nm_tr_map[game_dict['Id']] = game_dict['Name']

    query = trans_coll.where('Type','==',constants.BILL_TRACKER).where('isPaid','==',isPaid)
    plyr_bills = {"BillTrackers": []}
    for bill_doc_st in query.stream():
        bill_doc = bill_doc_st.to_dict()
        
        plyr_exst = bill_doc.get("PlayerId",None)
        if plyr_exst is None:
            continue

        bill_doc['GameName'] = nm_tr_map[bill_doc['GameId']]

        # send only phone and credit
        plyr_doc = get_by_id(bill_doc["PlayerId"])
        # plyr = {
        #     "Name": plyr_doc.get("Name",None),
        #     "Phone": plyr_doc.get("Phone",None),
        #     "Credit": plyr_doc.get("Credit",None),
        #     "isPlaying": plyr_doc.get("isPlaying",None)
        # }
        bill_doc['Player'] = plyr_doc

        if bill_doc['CanteenTrackerId'] is not None:
            ct_doc = get_by_id_trans(bill_doc['CanteenTrackerId'])
            bill_doc['CanteenTracker'] = ct_doc
        else:
            bill_doc['CanteenTracker'] = None
        
        if bill_doc['GameTrackerId'] is not None:
            gt_doc = get_by_id_trans(bill_doc['GameTrackerId'])
            bill_doc['GameTracker'] = gt_doc
        else:
            bill_doc['CanteenTracker'] = None
        plyr_bills["BillTrackers"].append(bill_doc)
    return plyr_bills
    

# def get_next_id_transactional():
#     with store.transaction() as transaction:
#         snapshot = counter_ref.get(transaction=transaction)
#         if snapshot.exists:
#             current_id = snapshot.get('current_id')
#         else:
#             current_id = 0
#         next_id = current_id + 1

#         transaction.update(counter_ref, {'current_id': next_id})
#     return next_id