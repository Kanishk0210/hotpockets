import firebase_admin

from firebase_admin import credentials, db, firestore

from google.cloud.firestore_v1.base_query import FieldFilter

from util import util, constants
from models.Audit import Audit
import sys

from datetime import datetime
from collections import defaultdict
import uuid
from typing import Union, List

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
        self.bill_tracker_counter_ref = self.source_coll.document(self.bill_tracker_counter_id)
        
    def run_transaction(self, transaction_func):
        """
        Run a transaction with the provided transaction function.
        The transaction function will be retried if conflicts occur.
        
        Args:
            transaction_func: Function that takes a transaction as argument and performs operations
            
        Returns:
            The result of the transaction function
        """
        @firestore.transactional
        def run_trans(transaction):
            return transaction_func(transaction)
            
        transaction = self.store.transaction()
        return run_trans(transaction)
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

    def get_ip(self):
        return self.source_coll.document("ip").get().to_dict()

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

    def update_rawmtrl(self, doc_id: str, req: dict, audit: Audit):
        doc_ref = self.target_coll.document(doc_id)
        ex_doc = doc_ref.get().to_dict()
        ex_doc[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()

        if req["type"] == "box":
            ex_doc["QuantityBox"] = ex_doc["QuantityBox"] + req["value"]
            ex_doc["Quantity"] = ex_doc["Quantity"] + req["value"]*ex_doc["QuantityPerBox"]
        elif req["type"] == "quantity":
            ex_doc["Quantity"] = ex_doc["Quantity"] + req["value"]
            ex_doc["QuantityBox"] = ex_doc["QuantityBox"] + req["value"]/ex_doc["QuantityPerBox"]
            
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

    def get_by_ids_trans(self, ids, collection_type=None):
        """
        Retrieves multiple documents from Firebase using their IDs.

        Args:
            ids: A set or list of document IDs.
            collection_type: The type of collection (e.g., constants.PLAYER).  Optional, but helps with error handling.

        Returns:
            A list of firestore.DocumentSnapshot objects, or None if an error occurs.  Empty list if no documents found.
        """
        if not ids:
            return []  # Return empty list if no IDs provided

        try:
            # Convert ids to a Firestore array if it's not already one.
            if not isinstance(ids, list):
                ids = list(ids)  # Handle sets or other iterables

            docs = self.trans_coll.where("Id","in", ids).stream()
            return list(docs)

        except Exception as e:
            print(f"Error fetching documents by IDs: {e}")
            return None

    def get_by_ids_target(self, ids, collection_type=None):
        """
        Retrieves multiple documents from Firebase using their IDs.

        Args:
            ids: A set or list of document IDs.
            collection_type: The type of collection (e.g., constants.PLAYER).  Optional, but helps with error handling.

        Returns:
            A list of firestore.DocumentSnapshot objects, or None if an error occurs.  Empty list if no documents found.
        """
        if not ids:
            return []  # Return empty list if no IDs provided

        try:
            # Convert ids to a Firestore array if it's not already one.
            if not isinstance(ids, list):
                ids = list(ids)  # Handle sets or other iterables

            docs = self.target_coll.where("Id","in", ids).stream()
            return list(docs)

        except Exception as e:
            print(f"Error fetching documents by IDs: {e}")
            return None



    def add_game_canteen(self, gt_id: str, doc: dict, audit: Audit):
        def update_stock_batch(menu_items, transaction):
            for mitem in menu_items:
                menu_item_ref = self.target_coll.document(mitem["Id"])
                menu_item_doc = menu_item_ref.get(transaction=transaction).to_dict()
                if menu_item_doc:
                    menu_item_doc["Remaining"] = menu_item_doc.get("Remaining", 0) - mitem["Quan"]
                    transaction.update(menu_item_ref, menu_item_doc)

        # Use transaction to ensure data consistency
        transaction = self.store.transaction()
        try:
            # Get game tracker document in transaction
            gt_doc_ref = self.trans_coll.document(gt_id)
            gt_doc = gt_doc_ref.get(transaction=transaction).to_dict()
            isNew = False

            # Batch get all menu items at once
            menu_items = MenuItem.collection.filter("id", "in", [item["Id"] for item in doc["MenuItems"]]).fetch()
            menu_items_map = {item.id: item for item in menu_items}

            if gt_doc["CanteenTrackerId"] is None:
                # Create new canteen tracker
                new_id = constants.CANTEEN_TRACKER +'::'+str(self.get_next_id(constants.CANTEEN_TRACKER))
                canteen_tracker = CanteenTracker()
                canteen_tracker.id = new_id
                canteen_tracker.modified_timestamp = util.get_current_tmstmp_str()
                canteen_tracker.created_timestamp = util.get_current_tmstmp_str()
                canteen_tracker.type = constants.CANTEEN_TRACKER
                canteen_tracker.game_id = gt_doc["GameId"]
                canteen_tracker.game_tracker_id = gt_id
                canteen_tracker.tx_id = None
                canteen_tracker.menu_items = []
                canteen_tracker.players = []
                isNew = True
            else:
                # Get existing canteen tracker
                canteen_tracker = CanteenTracker.collection.get(gt_doc["CanteenTrackerId"])
                if not canteen_tracker:
                    raise ValueError(f"Canteen tracker not found: {gt_doc['CanteenTrackerId']}")

            # Process menu items based on PlayerId
            if doc["PlayerId"] == None:
                # Handle menu items for non-player orders
                canteen_tracker.menu_items = []
                canteen_tracker.cost = 0
                
                for mitem_to_add in doc["MenuItems"]:
                    menu_item_doc = menu_items_map.get(mitem_to_add["Id"])
                    if menu_item_doc:
                        mitem_to_add["Cost"] = menu_item_doc.price
                        mitem_to_add["Name"] = menu_item_doc.name
                        canteen_tracker.cost += mitem_to_add["Cost"] * mitem_to_add["Quan"]
                        canteen_tracker.menu_items.append(mitem_to_add)
                        
                        # Update stock in transaction
                        update_stock_batch([mitem_to_add], transaction)
            else:
                # Handle menu items for player orders
                player = next((p for p in canteen_tracker.players if p["Id"] == doc["PlayerId"]), None)
                if not player:
                    player_doc = self.get_by_id(doc["PlayerId"])
                    player = {
                        "Id": player_doc["Id"],
                        "Name": player_doc["Name"],
                        "MenuItems": [],
                        "Cost": 0
                    }
                    canteen_tracker.players.append(player)

                for mitem_to_add in doc["MenuItems"]:
                    menu_item_doc = menu_items_map.get(mitem_to_add["Id"])
                    if menu_item_doc:
                        mitem_to_add["Cost"] = menu_item_doc.price
                        mitem_to_add["Name"] = menu_item_doc.name
                        cost_to_add = mitem_to_add["Cost"] * mitem_to_add["Quan"]
                        player["MenuItems"].append(mitem_to_add)
                        player["Cost"] += cost_to_add
                        canteen_tracker.cost += cost_to_add
                        
                        # Update stock in transaction
                        update_stock_batch([mitem_to_add], transaction)

            # Save changes in transaction
            if isNew:
                canteen_tracker_ref = self.trans_coll.document(canteen_tracker.id)
                transaction.set(canteen_tracker_ref, canteen_tracker.to_dict())
                transaction.update(gt_doc_ref, {"CanteenTrackerId": canteen_tracker.id})
                self.audit_log(audit, canteen_tracker.id, constants.CANTEEN_TRACKER, constants.AC_ADD, None, canteen_tracker.to_dict())
            else:
                canteen_tracker_ref = self.trans_coll.document(canteen_tracker.id)
                transaction.update(canteen_tracker_ref, canteen_tracker.to_dict())
                self.audit_log(audit, canteen_tracker.id, constants.CANTEEN_TRACKER, constants.AC_UPDATE, canteen_tracker_ref.get(transaction=transaction).to_dict(), canteen_tracker.to_dict())

            transaction.commit()
            return True, canteen_tracker.to_dict()
            
        except Exception as e:
            print(f"Error in add_game_canteen: {e}")
            # Transaction automatically rolls back on exception
            return False, None

    def add_ind_canteen(self, doc: dict, audit: Audit):
        """Add or update an individual canteen order with transaction safety"""
        transaction = self.store.transaction()
        try:
            # Initialize or get existing canteen tracker
            isNew = doc["Id"] is None
            if isNew:
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
            else:
                ex_ct_doc_ref = self.trans_coll.document(doc["Id"])
                ex_ct_doc = ex_ct_doc_ref.get(transaction=transaction).to_dict()
                if not ex_ct_doc:
                    raise ValueError(f"Canteen tracker not found: {doc['Id']}")

            # Batch get all menu items at once
            menu_item_ids = [item["Id"] for item in doc["MenuItems"]]
            menu_items_docs = self.get_by_ids_target(menu_item_ids)
            if not menu_items_docs:
                raise ValueError("No menu items found")
            menu_items_map = {doc.id: doc.to_dict() for doc in menu_items_docs}

            # Get player data if needed
            player = None
            if doc["PlayerId"]:
                # First try to find in existing players
                if not isNew:
                    player = next((p for p in ex_ct_doc["Players"] if p["Id"] == doc["PlayerId"]), None)
                
                if not player:
                    # Batch get player data
                    player_docs = self.get_by_ids_target([doc["PlayerId"]])
                    if not player_docs:
                        raise ValueError(f"Player not found: {doc['PlayerId']}")
                    player_doc = player_docs[0].to_dict()
                    player = {
                        "Id": player_doc["Id"],
                        "Name": player_doc["Name"],
                        "MenuItems": [],
                        "Cost": 0
                    }

            # Process menu items and update costs
            for mitem_to_add in doc["MenuItems"]:
                menu_item_doc = menu_items_map.get(mitem_to_add["Id"])
                if not menu_item_doc:
                    continue

                mitem_to_add["Cost"] = menu_item_doc["Price"]
                mitem_to_add["Name"] = menu_item_doc["Name"]
                cost_to_add = mitem_to_add["Cost"] * mitem_to_add["Quan"]

                if player:
                    # Update existing menu item quantity if found
                    existing_item = next((item for item in player["MenuItems"] if item["Id"] == mitem_to_add["Id"]), None)
                    if existing_item:
                        existing_item["Quan"] += mitem_to_add["Quan"]
                    else:
                        player["MenuItems"].append(mitem_to_add)
                    player["Cost"] += cost_to_add
                else:
                    # For non-player orders
                    existing_item = next((item for item in ex_ct_doc["MenuItems"] if item["Id"] == mitem_to_add["Id"]), None)
                    if existing_item:
                        existing_item["Quan"] += mitem_to_add["Quan"]
                    else:
                        ex_ct_doc["MenuItems"].append(mitem_to_add)
                
                ex_ct_doc["Cost"] += cost_to_add

            # Add new player if needed
            if player and not next((p for p in ex_ct_doc["Players"] if p["Id"] == player["Id"]), None):
                ex_ct_doc["Players"].append(player)

            # Save changes in transaction
            canteen_ref = self.trans_coll.document(ex_ct_doc["Id"])
            if isNew:
                transaction.set(canteen_ref, ex_ct_doc)
                self.audit_log(audit, ex_ct_doc["Id"], constants.CANTEEN_TRACKER, constants.AC_ADD, None, ex_ct_doc)
            else:
                transaction.update(canteen_ref, ex_ct_doc)
                self.audit_log(audit, ex_ct_doc["Id"], constants.CANTEEN_TRACKER, constants.AC_UPDATE, 
                             canteen_ref.get(transaction=transaction).to_dict(), ex_ct_doc)

            # Update stock in same transaction
            self.update_stock(doc, audit)

            transaction.commit()
            return True, ex_ct_doc

        except Exception as e:
            print(f"Error in add_ind_canteen: {e}")
            # Transaction automatically rolls back
            return False, None


    def update_stock(self, doc: dict, audit: Audit):
        # Use transaction to ensure data consistency
        transaction = self.store.transaction()
        try:
            # Get all menu items and their ingredients in one batch
            menu_items = {}
            ingredient_ids = set()
            for mitem in doc.get("MenuItems", []):
                mitem_doc = self.target_coll.document(mitem["Id"]).get(transaction=transaction).to_dict()
                menu_items[mitem["Id"]] = mitem_doc
                for ingnt in mitem_doc["Ingredients"]:
                    ingredient_ids.add(ingnt["RawMtrlId"])

            # Batch get all ingredients
            ingredients_docs = self.get_by_ids_target(list(ingredient_ids))
            ingredients_map = {doc.id: doc.to_dict() for doc in ingredients_docs} if ingredients_docs else {}

            # Update all ingredients in transaction
            for mitem in doc.get("MenuItems", []):
                mitem_doc = menu_items[mitem["Id"]]
                remaining = sys.maxsize

                for ingnt in mitem_doc["Ingredients"]:
                    ingnt_doc = ingredients_map[ingnt["RawMtrlId"]]
                    new_quantity = ingnt_doc["Quantity"] - mitem["Quan"] * ingnt["Quantity"]
                    ingnt_doc["Quantity"] = new_quantity
                    
                    if new_quantity <= remaining:
                        remaining = new_quantity

                    # Update ingredient in transaction
                    ingnt_ref = self.target_coll.document(ingnt["RawMtrlId"])
                    transaction.update(ingnt_ref, {"Quantity": new_quantity})
                    self.audit_log(audit, ingnt["RawMtrlId"], "RawMtrl", constants.AC_UPDATE, 
                                 {"Quantity": ingnt_doc["Quantity"] + mitem["Quan"] * ingnt["Quantity"]}, 
                                 {"Quantity": new_quantity})

                # Update menu item remaining stock in transaction
                mitem_ref = self.target_coll.document(mitem["Id"])
                transaction.update(mitem_ref, {"Remaining": remaining})
                self.audit_log(audit, mitem["Id"], "MenuItem", constants.AC_UPDATE,
                             {"Remaining": mitem_doc.get("Remaining")},
                             {"Remaining": remaining})

            transaction.commit()
            return True

        except Exception as e:
            print(f"Error in update_stock: {e}")
            # Transaction automatically rolls back
            return False


    def update_stock_edit(self, doc: dict, audit: Audit):
        """Update stock for both direct menu items and player orders in a single transaction"""
        # Start with direct menu items
        success = self.update_stock(doc, audit)
        if not success:
            return False

        # Handle player orders
        for player in doc.get("Players", []):
            if not self.update_stock(player, audit):
                return False
        return True

    def get_remaining_stock(self, doc: dict):
        """Get remaining stock with batch ingredient fetching"""
        try:
            # Collect all ingredient IDs
            ingredient_ids = [ingnt["RawMtrlId"] for ingnt in doc.get("Ingredients", [])]
            
            # Batch get all ingredients
            ingredients_docs = self.get_by_ids_target(ingredient_ids)
            if not ingredients_docs:
                return 0

            # Find minimum quantity
            remaining = sys.maxsize
            for doc in ingredients_docs:
                ingnt_doc = doc.to_dict()
                if ingnt_doc["Quantity"] < remaining:
                    remaining = ingnt_doc["Quantity"]
            
            return remaining

        except Exception as e:
            print(f"Error in get_remaining_stock: {e}")
            return 0

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
        query = self.trans_coll.where('Type','==',typ).where('isPaid','==',False).order_by('MdfdTmStmp', direction=firestore.Query.DESCENDING)
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
        """Get closed games that haven't been billed yet with optimized batch fetching"""
        try:
            # Get all games in one batch and create name mapping
            games = self.get_all(constants.GAME)
            game_name_map = {game.to_dict()['Id']: game.to_dict()['Name'] 
                           for game in games}
            
            # Get all unbilled game trackers in one query
            query = (self.trans_coll
                    .where('Type', '==', constants.GAME_TRACKER)
                    .where('isActive', '==', False)
                    .where('isBilled', '==', False)
                    .where('isCancelled', '==', False)
                    .order_by('EndTmStmp', direction=firestore.Query.DESCENDING))
            
            # Get all game trackers in one batch
            game_trackers = list(query.stream())
            
            # Collect all canteen tracker IDs that we need to fetch
            canteen_tracker_ids = {
                gt.to_dict()['CanteenTrackerId'] 
                for gt in game_trackers 
                if gt.to_dict().get('CanteenTrackerId')
            }
            
            # Batch fetch all needed canteen trackers
            canteen_trackers = {}
            if canteen_tracker_ids:
                ct_docs = self.get_by_ids_trans(list(canteen_tracker_ids))
                if ct_docs:
                    canteen_trackers = {
                        doc.id: doc.to_dict() 
                        for doc in ct_docs
                    }
            
            # Build the response with all data we now have in memory
            bills = {'ClosedNotBilledGames': []}
            for game_tracker in game_trackers:
                bill_doc = game_tracker.to_dict()
                # Add game name from our mapping
                bill_doc['GameName'] = game_name_map.get(bill_doc['GameId'], '')
                
                # Add canteen tracker from our pre-fetched data
                ct_id = bill_doc.get('CanteenTrackerId')
                if ct_id:
                    bill_doc['CanteenTracker'] = canteen_trackers.get(ct_id)
                else:
                    bill_doc['CanteenTracker'] = None
                    
                bills['ClosedNotBilledGames'].append(bill_doc)
            
            return bills
            
        except Exception as e:
            print(f"Error in get_closed_not_billed_games: {e}")
            return {'ClosedNotBilledGames': []}

    def check_pending_bill(self, pid: str):
        query = self.trans_coll.where('Type','==',constants.BILL_TRACKER).where('PlayerId','==',pid).where('isPaid','==',False)
        pen_bills = []
        for bill_doc in query.stream():
            pen_bills.append(bill_doc.to_dict())
        return pen_bills

    def get_all_plyr_bills2(self, isPaid):
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

    #new
    def get_all_plyr_bills(self, isPaid):
        # Fetch all games in a single query
        games = self.get_all(constants.GAME)
        game_name_map = {game.to_dict()['Id']: game.to_dict()['Name'] for game in games}

        # Fetch all BillTrackers in a single query
        query = self.trans_coll.where('Type', '==', constants.BILL_TRACKER).where('isPaid', '==', isPaid)
        bill_docs = list(query.stream())  # Fetch all documents at once

        # Build a map of Player IDs to Player documents
        player_ids = {doc.to_dict()['PlayerId'] for doc in bill_docs if doc.to_dict().get('PlayerId')}
        players = self.get_by_ids_target(player_ids)
        player_map = {player.id: player.to_dict() for player in players} if players else {}


        # Build a map of CanteenTracker IDs to CanteenTracker documents
        canteen_tracker_ids = {doc.to_dict()['CanteenTrackerId'] for doc in bill_docs if doc.to_dict().get('CanteenTrackerId')}
        canteen_trackers = self.get_by_ids_trans(canteen_tracker_ids, collection_type=constants.CANTEEN_TRACKER)
        canteen_tracker_map = {ct.id: ct.to_dict() for ct in canteen_trackers} if canteen_trackers else {}

        # Build a map of GameTracker IDs to GameTracker documents
        game_tracker_ids = {doc.to_dict()['GameTrackerId'] for doc in bill_docs if doc.to_dict().get('GameTrackerId')}
        game_trackers = self.get_by_ids_trans(game_tracker_ids, collection_type=constants.GAME_TRACKER)
        game_tracker_map = {gt.id: gt.to_dict() for gt in game_trackers} if game_trackers else {}


        plyr_bills = {"BillTrackers": []}
        for bill_doc in bill_docs:
            bill_data = bill_doc.to_dict()
            if bill_data.get('GameId'):
                bill_data['GameName'] = game_name_map.get(bill_data['GameId'])

            player_id = bill_data.get("PlayerId")
            if player_id:
                bill_data['Player'] = player_map.get(player_id)

            canteen_tracker_id = bill_data.get('CanteenTrackerId')
            if canteen_tracker_id:
                bill_data['CanteenTracker'] = canteen_tracker_map.get(canteen_tracker_id)
            else:
                bill_data['CanteenTracker'] = None

            game_tracker_id = bill_data.get('GameTrackerId')
            if game_tracker_id:
                bill_data['GameTracker'] = game_tracker_map.get(game_tracker_id)
            else:
                bill_data['GameTracker'] = None

            plyr_bills["BillTrackers"].append(bill_data)

        return plyr_bills



    #new
        
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

    def batch_update(self, updates: List[dict], audit):
        batch = self.store.batch()
        for upd in updates:
            ref = self.target_coll.document(upd["doc_id"])
            batch.update(ref, upd["data"])
        batch.commit()


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