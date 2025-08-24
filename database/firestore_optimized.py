from firebase_admin import firestore
from typing import Dict, List, Optional
import sys
import uuid
from models.Audit import Audit
import util.constants as constants
import util.util as util
from models.firestore.canteen_tracker import CanteenTracker
from models.firestore.menu_item import MenuItem
from fireo.transaction import Transaction

class FirebaseConn:
    def add_game_canteen(self, gt_id: str, doc: dict, audit: Audit):
        def update_stock_batch(menu_items, batch):
            for mitem in menu_items:
                menu_item = MenuItem.collection.get(mitem["Id"])
                if menu_item:
                    menu_item.remaining -= mitem["Quan"]
                    batch.update(menu_item)

        # Use transaction to ensure data consistency
        with Transaction() as transaction:
            # Get game tracker document
            gt_doc_ref = self.trans_coll.document(gt_id)
            gt_doc = gt_doc_ref.get().to_dict()
            isNew = False

            # Batch get all menu items at once
            menu_items = MenuItem.collection.filter("Id", "in", [item["Id"] for item in doc["MenuItems"]]).fetch()
            menu_items_map = {item.Id: item for item in menu_items}

            if gt_doc["CanteenTrackerId"] is None:
                # Create new canteen tracker
                new_id = constants.CANTEEN_TRACKER +'::'+str(self.get_next_id(constants.CANTEEN_TRACKER))
                canteen_tracker = CanteenTracker()
                canteen_tracker.Id = new_id
                canteen_tracker.MdfdTmStmp = util.get_current_tmstmp_str()
                canteen_tracker.CreatedTmStmp = util.get_current_tmstmp_str()
                canteen_tracker.Type = constants.CANTEEN_TRACKER
                canteen_tracker.GameId = gt_doc["GameId"]
                canteen_tracker.GameTrackerId = gt_id
                canteen_tracker.TxId = None
                canteen_tracker.MenuItems = []
                canteen_tracker.Players = []
                isNew = True
            else:
                # Get existing canteen tracker
                canteen_tracker = CanteenTracker.collection.get(gt_doc["CanteenTrackerId"])
                if not canteen_tracker:
                    raise ValueError(f"Canteen tracker not found: {gt_doc['CanteenTrackerId']}")

            # Process menu items based on PlayerId
            if doc["PlayerId"] is None:
                # Handle menu items for non-player orders
                existing_items = {item["Id"]: item for item in canteen_tracker.MenuItems}
                
                for mitem_to_add in doc["MenuItems"]:
                    menu_item = menu_items_map.get(mitem_to_add["Id"])
                    if not menu_item:
                        continue
                        
                    if mitem_to_add["Id"] in existing_items:
                        existing_item = existing_items[mitem_to_add["Id"]]
                        existing_item["Quan"] += mitem_to_add["Quan"]
                        canteen_tracker.Cost += menu_item.Price * mitem_to_add["Quan"]
                    else:
                        mitem_to_add["Cost"] = menu_item.Price
                        mitem_to_add["Name"] = menu_item.Name
                        canteen_tracker.MenuItems.append(mitem_to_add)
                        canteen_tracker.Cost += menu_item.Price * mitem_to_add["Quan"]
            else:
                # Handle menu items for player orders
                # Get player info if needed
                player = next((p for p in canteen_tracker.Players if p["Id"] == doc["PlayerId"]), None)
                if not player:
                    player_doc = self.get_by_id(doc["PlayerId"])  # Single player lookup
                    player = {
                        "Id": player_doc["Id"],
                        "Name": player_doc["Name"],
                        "MenuItems": [],
                        "Cost": 0
                    }
                    canteen_tracker.Players.append(player)

                # Process menu items for player
                player_items = {item["Id"]: item for item in player["MenuItems"]}
                
                for mitem_to_add in doc["MenuItems"]:
                    menu_item = menu_items_map.get(mitem_to_add["Id"])
                    if not menu_item:
                        continue

                    if mitem_to_add["Id"] in player_items:
                        existing_item = player_items[mitem_to_add["Id"]]
                        existing_item["Quan"] += mitem_to_add["Quan"]
                        cost_to_add = menu_item.Price * mitem_to_add["Quan"]
                        player["Cost"] += cost_to_add
                        canteen_tracker.Cost += cost_to_add
                    else:
                        mitem_to_add["Cost"] = menu_item.Price
                        mitem_to_add["Name"] = menu_item.Name
                        cost_to_add = menu_item.Price * mitem_to_add["Quan"]
                        player["MenuItems"].append(mitem_to_add)
                        player["Cost"] += cost_to_add
                        canteen_tracker.Cost += cost_to_add

            # Save changes within transaction
            if isNew:
                canteen_tracker.save(transaction=transaction)
                self.audit_log(audit, canteen_tracker.id, constants.CANTEEN_TRACKER, constants.AC_ADD, None, canteen_tracker.to_dict())
            else:
                transaction.update(canteen_tracker)
                self.audit_log(audit, canteen_tracker.id, constants.CANTEEN_TRACKER, constants.AC_UPDATE, canteen_tracker.to_dict(), canteen_tracker.to_dict())

            gt_doc["CanteenTrackerId"] = canteen_tracker.id
            gt_doc_ref.update(gt_doc)
            self.audit_log(audit, gt_doc["Id"], gt_doc.get(constants.TYPE,""), constants.AC_UPDATE, gt_doc_ref.get().to_dict(), gt_doc)

            # Update stock in the same transaction for data consistency
            update_stock_batch(doc["MenuItems"], transaction)

            # Everything is successful, return the result
            return True, canteen_tracker.to_dict()
