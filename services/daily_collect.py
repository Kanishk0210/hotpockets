from database import firebase_conn as fs_db
from util import util, constants

def update_safe(dc: dict):
    safe_id = constants.SAFE_ID
    safe = fs_db.get_safe()

    safe[constants.MDFDTMSTMP] = dc.get("CurrentCollectTmstmp")
    safe["CurrentCollectTmstmp"] = dc.get("CurrentCollectTmstmp")
    safe["LastCollectTmstmp"] = dc.get("LastCollectTmstmp")
    safe["AvailableCash"] = safe.get("AvailableCash", 0) - dc["Collection"]
    safe["LastDailyCollectId"] = dc.get("Id")
    safe["MdfdById"] = "Collector"

    fs_db.update_safe(safe_id, safe)
    return True

def save_cash(cash):
    safe_id = constants.SAFE_ID
    safe = fs_db.get_safe()

    safe[constants.MDFDTMSTMP] = util.get_current_tmstmp_str()
    safe["MdfdById"] = "Service"
    safe["AvailableCash"] = safe["AvailableCash"] + cash

    fs_db.update_safe(safe_id, safe)
    return True