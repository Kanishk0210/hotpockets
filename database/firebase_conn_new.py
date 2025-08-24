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

    def add_game_canteen(self, gt_id: str, doc: dict, audit: Audit):
        """Add or update a game canteen entry with transaction support."""
        def _update_stock(menu_items, transaction):
            """Update stock levels for menu items within the transaction."""
            for mitem in menu_items:
                menu_item_ref = self.target_coll.document(mitem["Id"])
                menu_item_doc = menu_item_ref.get(transaction=transaction).to_dict()
                if menu_item_doc:
                    menu_item_doc["Remaining"] = menu_item_doc.get("Remaining", 0) - mitem["Quan"]
                    transaction.update(menu_item_ref, menu_item_doc)

        # Use transaction to ensure data consistency
        transaction = self.store.transaction()
        
        try:
            # Get game tracker document
            gt_doc_ref = self.trans_coll.document(gt_id)
            gt_doc = gt_doc_ref.get(transaction=transaction).to_dict()
            isNew = False

            # Batch get all menu items at once
            menu_item_refs = [self.target_coll.document(item["Id"]) for item in doc["MenuItems"]]
            menu_items = [ref.get(transaction=transaction).to_dict() for ref in menu_item_refs]
            menu_items_map = {item["Id"]: item for item in menu_items if item}

            if gt_doc["CanteenTrackerId"] is None:
                # Create new canteen tracker
                new_id = constants.CANTEEN_TRACKER +'::'+str(self.get_next_id(constants.CANTEEN_TRACKER))
                ex_ct_doc = {
                    constants.MDFDTMSTMP: util.get_current_tmstmp_str(),
                    constants.CREATEDTMSTMP: util.get_current_tmstmp_str(),
                    constants.ID: new_id,
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
                ex_ct_doc_ref = self.trans_coll.document(new_id)
            else:
                # Get existing canteen tracker
                ex_ct_doc_ref = self.trans_coll.document(gt_doc["CanteenTrackerId"])
                ex_ct_doc = ex_ct_doc_ref.get(transaction=transaction).to_dict()
                ex_ct_doc_audit = ex_ct_doc.copy()

            # Process menu items based on PlayerId
            if doc["PlayerId"] is None:
                # Handle menu items for non-player orders
                menu_items_map_existing = {item["Id"]: item for item in ex_ct_doc["MenuItems"]} if not isNew else {}
                
                for mitem_to_add in doc["MenuItems"]:
                    menu_item = menu_items_map.get(mitem_to_add["Id"])
                    if not menu_item:
                        continue
                        
                    if mitem_to_add["Id"] in menu_items_map_existing:
                        existing_item = menu_items_map_existing[mitem_to_add["Id"]]
                        existing_item["Quan"] += mitem_to_add["Quan"]
                        ex_ct_doc["Cost"] += menu_item["Price"] * mitem_to_add["Quan"]
                    else:
                        mitem_to_add["Cost"] = menu_item["Price"]
                        mitem_to_add["Name"] = menu_item["Name"]
                        if isNew:
                            ex_ct_doc["MenuItems"].append(mitem_to_add)
                        else:
                            ex_ct_doc["MenuItems"].append(mitem_to_add)
                        ex_ct_doc["Cost"] += menu_item["Price"] * mitem_to_add["Quan"]
            else:
                # Handle menu items for player orders
                player = next((p for p in ex_ct_doc["Players"] if p["Id"] == doc["PlayerId"]), None) if not isNew else None
                if not player:
                    player_ref = self.target_coll.document(doc["PlayerId"])
                    player_doc = player_ref.get(transaction=transaction).to_dict()
                    player = {
                        "Id": player_doc["Id"],
                        "Name": player_doc["Name"],
                        "MenuItems": [],
                        "Cost": 0
                    }
                    if not isNew:
                        ex_ct_doc["Players"].append(player)

                # Process menu items for player
                player_items = {item["Id"]: item for item in player["MenuItems"]}
                for mitem_to_add in doc["MenuItems"]:
                    menu_item = menu_items_map.get(mitem_to_add["Id"])
                    if not menu_item:
                        continue

                    if mitem_to_add["Id"] in player_items:
                        existing_item = player_items[mitem_to_add["Id"]]
                        existing_item["Quan"] += mitem_to_add["Quan"]
                        cost_to_add = menu_item["Price"] * mitem_to_add["Quan"]
                        player["Cost"] += cost_to_add
                        ex_ct_doc["Cost"] += cost_to_add
                    else:
                        mitem_to_add["Cost"] = menu_item["Price"]
                        mitem_to_add["Name"] = menu_item["Name"]
                        cost_to_add = menu_item["Price"] * mitem_to_add["Quan"]
                        player["MenuItems"].append(mitem_to_add)
                        player["Cost"] += cost_to_add
                        ex_ct_doc["Cost"] += cost_to_add

            # Save all changes within transaction
            if isNew:
                transaction.set(ex_ct_doc_ref, ex_ct_doc)
                self.audit_log(audit, ex_ct_doc["Id"], constants.CANTEEN_TRACKER, constants.AC_ADD, None, ex_ct_doc)
            else:
                transaction.update(ex_ct_doc_ref, ex_ct_doc)
                self.audit_log(audit, ex_ct_doc["Id"], constants.CANTEEN_TRACKER, constants.AC_UPDATE, ex_ct_doc_audit, ex_ct_doc)

            gt_doc["CanteenTrackerId"] = ex_ct_doc["Id"]
            transaction.update(gt_doc_ref, gt_doc)
            self.audit_log(audit, gt_doc["Id"], gt_doc.get(constants.TYPE,""), constants.AC_UPDATE, gt_doc_ref.get().to_dict(), gt_doc)

            # Update stock within the same transaction
            _update_stock(doc["MenuItems"], transaction)

            # Commit the transaction
            transaction.commit()
            return True, ex_ct_doc

        except Exception as e:
            print(f"Transaction failed: {e}")
            return False, None
