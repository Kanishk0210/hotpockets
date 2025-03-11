from database.firebase_conn import FirebaseConn
from util import util, constants

class DailyCollectService:
    def __init__(self, fs_db: FirebaseConn):
        self.fs_db = fs_db

    def update_safe(self, dc: dict):
        safe_id = constants.SAFE_ID
        safe = self.fs_db.get_safe()

        safe[constants.MDFDTMSTMP] = dc.get("CurrentCollectTmstmp")
        safe["CurrentCollectTmstmp"] = dc.get("CurrentCollectTmstmp")
        safe["LastCollectTmstmp"] = dc.get("LastCollectTmstmp")
        safe["AvailableCash"] = safe.get("AvailableCash", 0) - dc["Collection"]
        safe["LastDailyCollectId"] = dc.get("Id")
        safe["MdfdById"] = "Collector"

        self.fs_db.update_safe(safe_id, safe)
        return True

    def save_cash(self, cash):
        safe_id = constants.SAFE_ID
        safe = self.fs_db.get_safe()

        safe[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
        safe["MdfdById"] = "Service"
        safe["AvailableCash"] = safe["AvailableCash"] + cash

        self.fs_db.update_safe(safe_id, safe)
        return True