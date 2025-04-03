import firebase_admin

from firebase_admin import credentials, db, firestore

from google.cloud.firestore_v1.base_query import FieldFilter

from util import util, constants
from models.Audit import Audit
import sys

from datetime import datetime
from collections import defaultdict
import uuid

cred = credentials.Certificate('resources/hotpockets-test-firebase-adminsdk-4gr44-d3d84f282d.json')

#cred = credentials.Certificate('resources/firebasse-adminsdk-prod.json')

firebase_app = firebase_admin.initialize_app(cred)

class FirebaseConn:
    def __init__(self, br_cd: str):
        if br_cd == "":
            sep = ""
        else:
            sep = "-"
        self.target_coll_str = br_cd+sep+'masterdata-target'
        self.source_coll_str = br_cd+sep+'masterdata-source'
        self.trans_coll_str = br_cd+sep+'transaction-data'
    
        self.store = firestore.client()

        self.player_counter_id = 'player_counter'
        self.game_counter_id = 'game_counter'
        self.emp_counter_id = 'emp_counter'
        self.inv_counter_id = 'inv_counter'
        self.rawMtrl_counter_id = 'rawMtrl_counter'
        self.menu_item_counter_id = 'menu_item_counter'
        self.game_tracker_counter_id = 'game_tracker_counter'
        self.bill_tracker_counter_id = 'bill_tracker_counter'
        self.canteen_tracker_counter_id = 'canteen_tracker_counter'
        self.branch_counter_id = 'branch_counter'

        self.target_coll = self.store.collection(self.target_coll_str)
        self.source_coll = self.store.collection(self.source_coll_str)
        self.trans_coll = self.store.collection(self.trans_coll_str)

        self.player_counter_ref = self.source_coll.document(self.player_counter_id)
        self.game_counter_ref = self.source_coll.document(self.game_counter_id)
        self.emp_counter_ref = self.source_coll.document(self.emp_counter_id)
        self.inv_counter_ref = self.source_coll.document(self.inv_counter_id)
        self.rawMtrl_counter_ref = self.source_coll.document(self.rawMtrl_counter_id)
        self.menu_item_counter_ref = self.source_coll.document(self.menu_item_counter_id)
        self.game_tracker_counter_ref = self.source_coll.document(self.game_tracker_counter_id)
        self.bill_tracker_counter_ref = self.source_coll.document(self.bill_tracker_counter_id)
        self.canteen_tracker_counter_ref = self.source_coll.document(self.canteen_tracker_counter_id)
        self.branch_counter_ref = self.source_coll.document(self.branch_counter_id)

    # admin

    def setup_source(self, coll):
        #safe
        safe_doc_id = "Safe"
        safe_doc = {
            "AvailableCash": 0,
            "CurrentCollectTmstmp": "",
            "Id": "Safe",
            "LastCollectTmstmp": "",
            "LastDailyCollectId": "",
            "MdfdById": "Svc/Create",
            "MdfdTmstmp": ""
        }
        coll.add(safe_doc, safe_doc_id)

        #counters:
        
        counter_doc = {
            "CurrentId": 0
        }

        #bill_tracker_counter
        coll.add(counter_doc, self.bill_tracker_counter_id)

        #canteen_tracker_counter
        coll.add(counter_doc, self.canteen_tracker_counter_id)

        #game_tracker_counter
        coll.add(counter_doc, self.game_tracker_counter_id)

        #menu_item_counter
        coll.add(counter_doc, self.menu_item_counter_id)

        #rawMtrl_counter
        coll.add(counter_doc, self.rawMtrl_counter_id)

        #inv_counter
        coll.add(counter_doc, self.inv_counter_id)

        #emp_counter
        coll.add(counter_doc, self.emp_counter_id)

        #game_counter
        coll.add(counter_doc, self.game_counter_id)

        #player_counter
        coll.add(counter_doc, self.player_counter_id)


    # create collection
    def create_collection(self, coll_name: str):

        if "source" in coll_name:
            doc_ref = self.store.collection(coll_name).document(coll_name+"::0")
            doc_ref.set({
                "Id": coll_name+"::0",
                constants.CREATEDTMSTMP: util.get_current_tmstmp_str()
            })
            self.setup_source(self.store.collection(coll_name))

            print("Collection "+ coll_name + " created")

        doc_ref = self.store.collection(coll_name).document(coll_name+"::0")
        doc_ref.set({
            "Id": coll_name+"::0",
            constants.CREATEDTMSTMP: util.get_current_tmstmp_str()
        })
        print("Collection "+ coll_name + " created")


    # source
    def add_dailycollect(self, dc: dict, audit: Audit):
        doc_id = constants.DAILY_COLLECT+'::'+dc.get("CurrentCollectTmstmp")
        dc[constants.ID] = doc_id
        dc[constants.MDFDTMSTMP] = dc.get("CurrentCollectTmstmp")
        dc[constants.CREATEDTMSTMP] = dc.get("CurrentCollectTmstmp")
        self.trans_coll.add(dc, doc_id)
        self.audit_log(audit, doc_id, constants.DAILY_COLLECT, constants.AC_ADD, None, dc)
        return True, dc

    def get_safe(self):
        return self.source_coll.document(constants.SAFE_ID).get().to_dict()

    def update_safe(self, doc_id: str, doc: dict, audit: Audit):
        doc_ref = self.source_coll.document(doc_id)
        self.audit_log(audit, doc_id, doc.get("Type",""), constants.AC_UPDATE, doc_ref.get().to_dict(), doc)
        doc_ref.update(doc)
        return True

    # target

    def get_counter_ref(self, typ: str):
        if typ == constants.MENU:
            return self.menu_item_counter_ref
        if typ == constants.INVENTORY:
            return self.inv_counter_ref
        if typ == constants.PLAYER:
            return self.player_counter_ref
        if typ == constants.GAME:
            return self.game_counter_ref
        if typ == constants.EMPLOYEE:
            return self.emp_counter_ref
        if typ == constants.RAWMTRL:
            return self.rawMtrl_counter_ref
        if typ == constants.GAME_TRACKER:
            return self.game_tracker_counter_ref
        if typ == constants.BILL_TRACKER:
            return self.bill_tracker_counter_ref
        if typ == constants.CANTEEN_TRACKER:
            return self.canteen_tracker_counter_ref
        if typ == constants.BRANCH:
            return self.branch_counter_ref
        raise Exception

    def get_next_id(self, typ: str):
        counter_ref = self.get_counter_ref(typ)
        next_id = int(counter_ref.get().to_dict()[constants.CURRENTID]) + 1
        counter_ref.update({constants.CURRENTID: next_id, constants.MDFDTMSTMP: util.get_current_tmstmp_str()})
        return next_id

    def get_all(self, typ: str):
        query = self.target_coll.where(filter=FieldFilter('Type','==',typ))
        return query.stream()

    def get_all_users(self):
        query = self.target_coll.where(filter=FieldFilter('Type','==',"Employee"))
        return query.stream()

    def get_all_admins(self):
        query = self.target_coll.where(filter=FieldFilter('Type','==',"Admin"))
        return query.stream()

    def get_by_id(self, doc_id: str):
        return self.target_coll.document(doc_id).get().to_dict()

    def get_ct_by_gt_id(self, gt_id: str):
        query = self.trans_coll.where(filter=FieldFilter('Type','==',constants.CANTEEN_TRACKER)).where(filter=FieldFilter('isActive','==', True)).where(filter=FieldFilter('GameTrackerId','==',gt_id))
        res = query.stream()
        print(res)
        return res

    def add(self, typ: str, doc: dict, audit: Audit):
        doc_id = typ+'::'+str(self.get_next_id(typ))
        doc[constants.ID] = doc_id
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
        self.target_coll.add(doc, doc_id)
        self.audit_log(audit, doc_id, typ, constants.AC_ADD, None, doc)
        return True, doc

    def update(self, doc_id: str, doc: dict, audit: Audit):
        doc_ref = self.target_coll.document(doc_id)
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        self.audit_log(audit, doc_id, doc.get(constants.TYPE,""), constants.AC_UPDATE, doc_ref.get().to_dict(), doc)
        doc_ref.update(doc)
        return True

    def update_rawmtrl(self, doc_id: str, doc: dict, audit: Audit):
        doc_ref = self.target_coll.document(doc_id)
        ex_doc = doc_ref.get().to_dict()
        ex_doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        ex_doc["QuantityBox"] = ex_doc["QuantityBox"] + doc["QuantityBox"]
        ex_doc["Quantity"] = ex_doc["Quantity"] + doc["QuantityBox"]*ex_doc["QuantityPerBox"]
        self.audit_log(audit, doc_id, ex_doc.get("Type",""), constants.AC_UPDATE, doc_ref.get().to_dict(), ex_doc)
        doc_ref.update(ex_doc)
        return True

    def delete_target(self, doc_id: str, audit: Audit):
        
        doc_ref = self.target_coll.document(doc_id)
        doc = doc_ref.get().to_dict()
        self.audit_log(audit, doc_id, doc.get("Type",""), constants.AC_DELETE, doc, None)

        doc_ref.delete()
        return True

    # Transaction

    def add_trans(self, typ: str, doc: dict, audit: Audit):
        doc_id = typ+'::'+str(self.get_next_id(typ))
        doc[constants.ID] = doc_id
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
        self.trans_coll.add(doc, doc_id)
        self.audit_log(audit, doc_id, typ, constants.AC_ADD, None, doc)
        return True, doc

    def add_trans_by_id(self, doc_id: str, doc: dict, audit: Audit):
        doc[constants.ID] = doc_id
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
        self.trans_coll.add(doc, doc_id)
        self.audit_log(audit, doc_id, doc["Type"], constants.AC_ADD, None, doc)
        return True, doc

    def get_all_trans(self, typ: str):
        query = self.trans_coll.where('Type','==',typ)
        return query.stream()

    def get_by_id_trans(self, doc_id: str):
        return self.trans_coll.document(doc_id).get().to_dict()

    def start_game(self, doc: dict):
        typ = constants.GAME_TRACKER

        # duplicate check
        query = self.trans_coll.where('Type','==',typ).where('GameId','==',doc.get('GameId')).where('isActive','==',True)
        dup_docs = query.stream()
        count = sum(1 for d in dup_docs)
        if count >0:
            return False, doc

        doc_id = typ+'::'+str(self.get_next_id(typ))
        doc[constants.ID] = doc_id
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        doc[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
        self.trans_coll.add(doc, doc_id)
        return True, doc

    def update_target(self, doc_id: str, doc: dict, audit: Audit):
        doc_ref = self.target_coll.document(doc_id)
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        doc_ref.update(doc)
        self.audit_log(audit, doc_id, doc.get(constants.TYPE,""), constants.AC_UPDATE, doc_ref.get().to_dict(), doc)
        return True, doc

    def update_trans(self, doc_id: str, doc: dict, audit: Audit):
        doc_ref = self.trans_coll.document(doc_id)
        doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        doc_ref.update(doc)
        self.audit_log(audit, doc_id, doc.get(constants.TYPE,""), constants.AC_UPDATE, doc_ref.get().to_dict(), doc)
        return True, doc

    def add_game_canteen(self, gt_id: str, doc: dict, audit: Audit):
        gt_doc_ref = self.trans_coll.document(gt_id)
        gt_doc = gt_doc_ref.get().to_dict()
        isNew = False
        if gt_doc["CanteenTrackerId"] == None:
            gt_doc["CanteenTrackerId"] = constants.CANTEEN_TRACKER +'::'+str(self.get_next_id(constants.CANTEEN_TRACKER))
            ex_ct_doc = {
                constants.MDFDTMSTMP: util.get_current_tmstmp_str(),
                constants.CREATEDTMSTMP: util.get_current_tmstmp_str(),
                constants.ID: gt_doc["CanteenTrackerId"],
                "Type": constants.CANTEEN_TRACKER,
                "GameId": gt_doc["GameId"],
                "GameTrackerId": gt_id,
                "TxId": None,
                "isActive": True,
                "isBilled": False,
                "isCancelled": False,
                "MenuItems": [],
                "Players": [],
                "Cost": 0
            }
            isNew = True
        else:
            ex_ct_doc_ref = self.trans_coll.document(gt_doc["CanteenTrackerId"])
            ex_ct_doc = ex_ct_doc_ref.get().to_dict()
            ex_ct_doc_audit = ex_ct_doc_ref.get().to_dict()

        if doc["PlayerId"] == None:
            for mitem_to_add in doc["MenuItems"]:
                found = False
                for mitem in ex_ct_doc["MenuItems"]:
                    if mitem["Id"] == mitem_to_add["Id"]:
                        mitem["Quan"] += mitem_to_add["Quan"]
                        ex_ct_doc["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                        found = True
                        break
                if not found:
                    mitem_to_add_doc = self.get_by_id(mitem_to_add["Id"])
                    mitem_to_add["Cost"] = mitem_to_add_doc["Price"]
                    mitem_to_add["Name"] = mitem_to_add_doc["Name"]
                    ex_ct_doc["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                    ex_ct_doc["MenuItems"].append(mitem_to_add)
        else:
            plyrFound = False
            player = {}
            for plyr in ex_ct_doc["Players"]:
                if plyr["Id"] == doc["PlayerId"]:
                    plyrFound = True
                    player = plyr
            
            if not plyrFound:
                plyr_doc = self.get_by_id(doc["PlayerId"])
                player = {
                    "Id": plyr_doc["Id"],
                    "Name": plyr_doc["Name"],
                    "MenuItems": [],
                    "Cost": 0
                }

            for mitem_to_add in doc["MenuItems"]:
                found = False
                for mitem in player["MenuItems"]:
                    if mitem["Id"] == mitem_to_add["Id"]:
                        mitem["Quan"] += mitem_to_add["Quan"]
                        player["Cost"] += mitem["Cost"] * mitem_to_add["Quan"]
                        ex_ct_doc["Cost"] += mitem["Cost"] * mitem_to_add["Quan"]
                        found = True
                        break
                if not found:
                    mitem_to_add_doc = self.get_by_id(mitem_to_add["Id"])
                    mitem_to_add["Cost"] = mitem_to_add_doc["Price"]
                    mitem_to_add["Name"] = mitem_to_add_doc["Name"]
                    player["MenuItems"].append(mitem_to_add)
                    player["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                    ex_ct_doc["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
            
            if not plyrFound:
                ex_ct_doc["Players"].append(player)

        if isNew:
            self.trans_coll.add(ex_ct_doc, ex_ct_doc["Id"])
            self.audit_log(audit, ex_ct_doc["Id"], ex_ct_doc["Type"], constants.AC_ADD, None, ex_ct_doc)
        else:
            ex_ct_doc_ref.update(ex_ct_doc)
            self.audit_log(audit, ex_ct_doc["Id"], ex_ct_doc.get(constants.TYPE,""), constants.AC_UPDATE, ex_ct_doc_audit, ex_ct_doc)
        
        gt_doc["CanteenTrackerId"] = ex_ct_doc["Id"]
        self.audit_log(audit, gt_doc["Id"], gt_doc.get(constants.TYPE,""), constants.AC_UPDATE, gt_doc_ref.get().to_dict(), gt_doc)
        gt_doc_ref.update(gt_doc)

        self.update_stock(doc, audit)
        return True, ex_ct_doc

    def add_ind_canteen(self, doc: dict, audit: Audit):
        isNew = False
        if doc["Id"] == None:
            ct_id = constants.CANTEEN_TRACKER +'::'+str(self.get_next_id(constants.CANTEEN_TRACKER))
            ex_ct_doc = {
                constants.MDFDTMSTMP: util.get_current_tmstmp_str(),
                constants.CREATEDTMSTMP: util.get_current_tmstmp_str(),
                constants.ID: ct_id,
                "Type": constants.CANTEEN_TRACKER,
                "GameId": None,
                "GameTrackerId": None,
                "TxId": None,
                "isActive": True,
                "isBilled": False,
                "isCancelled": False,
                "MenuItems": [],
                "Players": [],
                "Cost": 0
            }
            isNew = True
        else:
            ex_ct_doc_ref = self.trans_coll.document(doc["Id"])
            ex_ct_doc = ex_ct_doc_ref.get().to_dict()
            ex_ct_doc_audit = ex_ct_doc_ref.get().to_dict()
            

        plyrFound = False
        player = {}
        for plyr in ex_ct_doc["Players"]:
            if plyr["Id"] == doc["PlayerId"]:
                plyrFound = True
                player = plyr
        
        if not plyrFound:
            plyr_doc = self.get_by_id(doc["PlayerId"])
            player = {
                "Id": plyr_doc["Id"],
                "Name": plyr_doc["Name"],
                "MenuItems": [],
                "Cost": 0
            }

        for mitem_to_add in doc["MenuItems"]:
            found = False
            for mitem in player["MenuItems"]:
                if mitem["Id"] == mitem_to_add["Id"]:
                    mitem["Quan"] += mitem_to_add["Quan"]
                    player["Cost"] += mitem["Cost"] * mitem_to_add["Quan"]
                    ex_ct_doc["Cost"] += mitem["Cost"] * mitem_to_add["Quan"]
                    found = True
                    break
            if not found:
                mitem_to_add_doc = self.get_by_id(mitem_to_add["Id"])
                mitem_to_add["Cost"] = mitem_to_add_doc["Price"]
                mitem_to_add["Name"] = mitem_to_add_doc["Name"]
                player["MenuItems"].append(mitem_to_add)
                player["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                ex_ct_doc["Cost"] += mitem_to_add["Cost"] * mitem_to_add["Quan"]
        
        if not plyrFound:
            ex_ct_doc["Players"].append(player)

        if isNew:
            self.trans_coll.add(ex_ct_doc, ex_ct_doc["Id"])
            self.audit_log(audit, ex_ct_doc["Id"], ex_ct_doc["Type"], constants.AC_ADD, None, doc)
        else:
            ex_ct_doc_ref.update(ex_ct_doc)
            self.audit_log(audit, doc["Id"], doc.get(constants.TYPE,""), constants.AC_UPDATE, ex_ct_doc_audit, ex_ct_doc)

        self.update_stock(doc, audit)
        return True, ex_ct_doc


    def update_stock(self, doc: dict, audit: Audit):
        for mitem in doc.get("MenuItems",[]):
            mitem_doc = self.get_by_id(mitem["Id"])
            remaining = sys.maxsize
            for ingnt in mitem_doc["Ingredients"]:
                ingnt_doc = self.get_by_id(ingnt["RawMtrlId"])
                ingnt_doc["Quantity"] -= mitem["Quan"]*ingnt["Quantity"]
                self.update(ingnt_doc["Id"], ingnt_doc, audit)

                if ingnt_doc["Quantity"] <= remaining:
                    remaining = ingnt_doc["Quantity"]
            mitem_doc["Remaining"] = remaining
            self.update(mitem_doc["Id"], mitem_doc, audit)


    def update_stock_edit(self, doc: dict, audit: Audit):
        self.update_stock(doc, audit)

        for player in doc["Players"]:
            self.update_stock(player, audit)

    def get_remaining_stock(self, doc: dict):
        remaining = sys.maxsize
        for ingnt in doc["Ingredients"]:
            ingnt_doc = self.get_by_id(ingnt["RawMtrlId"])
            if ingnt_doc["Quantity"] < remaining:
                remaining = ingnt_doc["Quantity"]
        return remaining

    def update_ct(self, doc_id: str, doc: dict, audit: Audit):
        doc_ref = self.trans_coll.document(doc_id)
        ex_doc = doc_ref.get().to_dict()
        ex_doc_audit = doc_ref.get().to_dict()
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
        self.audit_log(audit, ex_doc["Id"], ex_doc.get(constants.TYPE,""), constants.AC_UPDATE, ex_doc_audit, ex_doc)

        self.update_stock_edit(ex_doc, audit)
        return True, ex_doc

    def get_all_ind_canteen(self):
        query = self.trans_coll.where('Type','==',constants.CANTEEN_TRACKER).where('GameId','==',None)
        return query.stream()

    def get_all_pending_bills(self, typ: str):
        query = self.trans_coll.where('Type','==',typ).where('isPaid','==',False)
        return query.stream()

    def get_all_paid_bills(self, typ: str):
        query = self.trans_coll.where('Type','==',typ).where('isPaid','==',True)
        return query.stream()

    def get_active_game_trackers(self, typ: str):
        query = self.trans_coll.where('Type','==',typ).where('isActive','==',True)
        return query.stream()

    def get_all_games(self, typ: str):
        games = self.get_all(constants.GAME)
        act_games_lst = self.get_active_game_trackers(constants.GAME_TRACKER)
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

    def get_closed_not_billed_games(self):
        # add game name
        games = self.get_all(constants.GAME)
        nm_tr_map = {}
        for game in games:
            game_dict = game.to_dict()
            nm_tr_map[game_dict['Id']] = game_dict['Name']
        
        query = self.trans_coll.where('Type','==',constants.GAME_TRACKER).where('isActive','==',False).where('isBilled','==',False).where('isCancelled','==',False)
        bills = {'ClosedNotBilledGames':[]}
        for bill in query.stream():
            bill_doc = bill.to_dict()
            bill_doc['GameName'] = nm_tr_map[bill_doc['GameId']]
            if bill_doc['CanteenTrackerId'] is not None:
                ct_doc = self.get_by_id_trans(bill_doc['CanteenTrackerId'])
                bill_doc['CanteenTracker'] = ct_doc
            else:
                bill_doc['CanteenTracker'] = None
            bills['ClosedNotBilledGames'].append(bill_doc)

        return bills

    def check_pending_bill(self, pid: str):
        query = self.trans_coll.where('Type','==',constants.BILL_TRACKER).where('PlayerId','==',pid).where('isPaid','==',False)
        pen_bills = []
        for bill_doc in query.stream():
            pen_bills.append(bill_doc.to_dict())
        return pen_bills

    def get_all_plyr_bills(self, isPaid):
        # add game name
        games = self.get_all(constants.GAME)
        nm_tr_map = {}
        for game in games:
            game_dict = game.to_dict()
            nm_tr_map[game_dict['Id']] = game_dict['Name']

        query = self.trans_coll.where('Type','==',constants.BILL_TRACKER).where('isPaid','==',isPaid)
        plyr_bills = {"BillTrackers": []}
        for bill_doc_st in query.stream():
            bill_doc = bill_doc_st.to_dict()
            
            plyr_exst = bill_doc.get("PlayerId",None)
            if plyr_exst is None:
                continue
            
            if bill_doc.get('GameId',None) is not None:
                bill_doc['GameName'] = nm_tr_map[bill_doc.get('GameId',None)]

            # send only phone and credit
            plyr_doc = self.get_by_id(bill_doc["PlayerId"])
            # plyr = {
            #     "Name": plyr_doc.get("Name",None),
            #     "Phone": plyr_doc.get("Phone",None),
            #     "Credit": plyr_doc.get("Credit",None),
            #     "isPlaying": plyr_doc.get("isPlaying",None)
            # }
            bill_doc['Player'] = plyr_doc

            if bill_doc['CanteenTrackerId'] is not None:
                ct_doc = self.get_by_id_trans(bill_doc['CanteenTrackerId'])
                bill_doc['CanteenTracker'] = ct_doc
            else:
                bill_doc['CanteenTracker'] = None
            
            if bill_doc['GameTrackerId'] is not None:
                gt_doc = self.get_by_id_trans(bill_doc['GameTrackerId'])
                bill_doc['GameTracker'] = gt_doc
            else:
                bill_doc['GameTracker'] = None
            plyr_bills["BillTrackers"].append(bill_doc)
        return plyr_bills
        
    def trash(self, menu_itms: dict, audit: Audit):
        try:
            self.update_stock(menu_itms, audit)
            trash_ref = self.target_coll.document("Trash")
            if not trash_ref.get().exists:
                tmstmp = util.get_current_tmstmp_str()
                trash = {
                    "Id": "Trash",
                    "Type": "Trash",
                    tmstmp: menu_itms
                }
                self.target_coll.add(trash, "Trash")
            else:
                trash = trash_ref.get().to_dict()
                tmstmp = util.get_current_tmstmp_str()
                trash[tmstmp]= menu_itms
                self.update_target("Trash", trash, audit)
        except Exception as e:
            print(e)
            return False
        return True

    def get_trash(self):
        return self.target_coll.document("Trash").get().to_dict()

    def add_branch(self, branch_pld: dict):
        doc_id = constants.BRANCH+'::'+str(self.get_next_id(constants.BRANCH))
        branch_pld["Id"] = doc_id
        branch_pld[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        branch_pld[constants.CREATEDTMSTMP] = util.get_current_tmstmp_str()
        branch_pld["Code"] = branch_pld["Name"][:5].upper()

        self.target_coll.add(branch_pld, doc_id)

        self.create_collection(branch_pld["Code"]+"-masterdata-source")
        self.create_collection(branch_pld["Code"]+"-masterdata-target")
        self.create_collection(branch_pld["Code"]+"-transaction-data")

        return True

    def get_revenue(self, start_timestamp, end_timestamp):
        # Fetch documents without inequality filters
        query = (
            self.trans_coll
            .where('Type', '==', constants.BILL_TRACKER)
            .where('isPaid', '==', True)
        )

        query = self.trans_coll.where(
                filter=FieldFilter('Type', '==', constants.BILL_TRACKER)
            ).where(
                filter=FieldFilter('isPaid', '==', True)
            ).where(
                filter=FieldFilter('MdfdTmStmp', '>=', start_timestamp)
            ).where(
                filter=FieldFilter('MdfdTmStmp', '<=', end_timestamp)
            )

        revenue = {
            "data":[],
            "revenue_summary" : {
                "GameRevenue": 0,
                "CanteenRevenue": 0,
                "TotalRevenue": 0,
                "Total":0,
                "Discount":0,
                "BillCount": 0,
                "Credit":0,
                "Cash":0,
                "Online":0
            }
        }

        date_revenue_map = defaultdict(float)

        for bill_doc_st in query.stream():
            bill_doc = bill_doc_st.to_dict()

            # Ensure createdTimestamp is a valid number before comparison
            created_ts = datetime.strptime(bill_doc.get("MdfdTmStmp"), "%Y-%m-%d %H:%M:%S").timestamp()
            created_date = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d")
            discount = bill_doc.get("Discount",0)

            total_amount = bill_doc.get("TotalCost", 0) - discount
            date_revenue_map[created_date] += total_amount

            revenue["data"].append({
                "date":"",
                "total":""
            })

            revenue["revenue_summary"]["GameRevenue"] += bill_doc.get("GameCost", 0)
            revenue["revenue_summary"]["CanteenRevenue"] += bill_doc.get("CanteenCost", 0)
            revenue["revenue_summary"]["TotalRevenue"] += bill_doc.get("TotalCost", 0)
            revenue["revenue_summary"]["Total"] += ( bill_doc.get("TotalCost", 0) - discount )
            revenue["revenue_summary"]["Discount"] += bill_doc.get("Discount", 0)
            revenue["revenue_summary"]["BillCount"] += 1
            revenue["revenue_summary"]["Cash"] += sum(bill_doc.get("Mode")["Cash"])
            revenue["revenue_summary"]["Credit"] += sum(bill_doc.get("Mode")["Credit"])
            revenue["revenue_summary"]["Online"] += sum(bill_doc.get("Mode")["Online"])

        revenue["data"] = [{"date": date, "amount": amount} for date, amount in date_revenue_map.items()]

        return revenue

    def audit_log(self, audit: Audit, doc_id, doc_type, action, pr_value, nw_value):
        audit.Id = constants.AUDIT + "::" + str(uuid.uuid4())
        audit.CreatedTmStmp = util.get_current_tmstmp_str()
        audit.DocId = doc_id
        audit.Action = action
        audit.PreviousValue = pr_value
        audit.NewValue = nw_value
        audit.DocType = doc_type

        self.store.collection("audit-logs").add(audit.dict(), audit.Id)


    def get_audit_logs(self, req: dict):
        print(req)
        # start_time = datetime.strptime(req['start_timestamp'], "%Y-%m-%d %H:%M:%S")
        # end_time = datetime.strptime(req['end_timestamp'], "%Y-%m-%d %H:%M:%S")
        # actionn = req["action"]

        return {}

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