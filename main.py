import random
import string
import base64
# import ngrok

from fastapi import FastAPI, APIRouter, Body, Depends

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

import uvicorn

from database.firebase_conn import FirebaseConn
from services.game import GameService
from services.daily_collect import DailyCollectService
from models.Player import Player
from models.Game import Game
from models.Employee import Employee
from models.Inventory import Inventory
from models.Menu import RawMtrl
from models.Menu import Menu
from models.UserLoginSchema import UserLoginSchema
from models.GameTracker import GameTracker, GameTrackerEndRequest
from models.CanteenTracker import CanteenTracker
from models.DailyCollect import DailyCollect
from models.Branch import Branch
from util import util, constants
# from auth import auth_bearer, auth_handler
from auth.auth_bearer import JWTBearer
from auth.auth_handler import signJWT, decodeJWT

app = FastAPI()

# global fs_db
# fs_db = FirebaseConn("")

# authb = auth_bearer()

class BranchMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(request.headers)
        global fs_db, game, daily_collect
        if request.url.path == "/user/login":
            fs_db = FirebaseConn("")
            return await call_next(request)
        b,token = request.headers.get("authorization","").split(" ")
        dec_token = decodeJWT(token) 
        br = dec_token.get("branch","")
        fs_db = FirebaseConn(dec_token.get("branch",""))
        game = GameService(fs_db)
        daily_collect = DailyCollectService(fs_db)

        print(fs_db.target_coll_str)

        return await call_next(request)

origins = [
    "http://localhost:3000",
    "https://hot-pocket-47985.web.app"
]

app.add_middleware(BranchMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_methods = ["GET","POST","PUT","DELETE"],
    allow_headers = ["*"]
)




# @app.middleware("http")
# def pre_setup(request: Request, call_next):
#     print(request.headers)
#     global fs_db
#     if request.url.path == "/user/login":
#         fs_db = FirebaseConn("")
#         return call_next(request)
#     b,token = request.headers.get("authorization","").split(" ")
#     dec_token = decodeJWT(token) 
#     br = dec_token.get("branch","")
#     fs_db = FirebaseConn(dec_token.get("branch",""))

    # print(fs_db.target_coll_str)

    # return call_next(request)

def check_user(data: UserLoginSchema):
    users = fs_db.get_all(constants.EMPLOYEE)
    br_cd = ""
    for usr in users:
        user = usr.to_dict()
        user_dec_pass = util.decode_pass(user["Password"])
        if user["Email"] == data.email and user_dec_pass == data.password:
            br_cd = user["Branch"]
            perms = user["Permission"]
            return True, br_cd, perms
    return False, None, None

@app.get("/", dependencies= [Depends(JWTBearer())] ,tags=["root"])
async def root():
    return {"message": "Hot Pockets"}

@app.post("/user/login", tags=["user"])
def user_login(user: UserLoginSchema = Body(...)):
    is_user, br_cd, perms = check_user(user)
    if is_user:
        return signJWT(user.email, br_cd, perms)
    return {
        "error": "Wrong login details!"
    }

@app.delete("/delete/{doc_id}", dependencies=[Depends(JWTBearer())])
def delete_target(doc_id: str):
    isDeleted = fs_db.delete_target(doc_id)
    
    if not isDeleted:
        JSONResponse(content='Failed to Delete.', status_code=500)
    return JSONResponse(content='Successfully Deleted.', status_code=200)

@app.get("/players", dependencies=[Depends(JWTBearer())])
def get_players():

    players = fs_db.get_all(constants.PLAYER)

    players_res = {'Players':[]}
    for player in players:
        players_res['Players'].append(player.to_dict())
    return JSONResponse(content=players_res, status_code=200)

@app.post("/player", dependencies=[Depends(JWTBearer())])
def add_player(player: Player):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.PLAYER, player.dict())

    if not isAdded: 
        JSONResponse(content='Failed to Add Player.', status_code=500)
    return JSONResponse(content='Successfully added Player.', status_code=201)

@app.get("/games", dependencies=[Depends(JWTBearer())])
def get_games():

    games = fs_db.get_all_games(constants.GAME)

    return JSONResponse(content=games, status_code=200)

@app.post("/game", dependencies=[Depends(JWTBearer())])
def add_game(game: Game):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.GAME, game.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Game.', status_code=500)
    return JSONResponse(content='Successfully added Game.', status_code=201)

@app.post("/employee", dependencies=[Depends(JWTBearer())])
def add_emp(emp: Employee):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp

    emp.Password = util.encode_pass(emp.Password)

    isAdded = fs_db.add(constants.EMPLOYEE, emp.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Employee.', status_code=500)
    return JSONResponse(content='Successfully added Employee.', status_code=201) 

@app.get("/employees", dependencies=[Depends(JWTBearer())])
def get_emps():

    emps = fs_db.get_all(constants.EMPLOYEE)

    emp_res = {'Employees':[]}
    for e in emps:
        emp_res['Employees'].append(e.to_dict())
    return JSONResponse(content=emp_res, status_code=200)

@app.post("/inventory", dependencies=[Depends(JWTBearer())])
def add_inv(inv: Inventory):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.INVENTORY, inv.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Inventory.', status_code=500)
    return JSONResponse(content='Successfully added Inventory.', status_code=201)

@app.get("/inventories", dependencies=[Depends(JWTBearer())])
def get_invs():

    invs = fs_db.get_all(constants.INVENTORY)

    inv_res = {'Inventories':[]}
    for i in invs:
        inv_res['Inventories'].append(i.to_dict())
    return JSONResponse(content=inv_res, status_code=200)

@app.post("/rawMtrl", dependencies=[Depends(JWTBearer())])
def add_raw(rawMtrl: RawMtrl):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    rm_dict = rawMtrl.dict()
    if rm_dict.get("CostPerBox",None) is not None:
        rm_dict["CostPerItem"] = rm_dict["CostPerBox"]//rm_dict["QuantityPerBox"]
        rm_dict["Quantity"] = rm_dict["QuantityBox"]*rm_dict["QuantityPerBox"]
    isAdded, doc = fs_db.add(constants.RAWMTRL, rm_dict)

    if not isAdded:
        JSONResponse(content='Failed to Add Raw Material.', status_code=500)
    return JSONResponse(content=doc, status_code=201)

@app.put("/rawMtrl/update/{doc_id}", dependencies=[Depends(JWTBearer())])
def update_raw(doc_id: str, doc: dict):
    isUpdated = fs_db.update_rawmtrl(doc_id, doc)
    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

@app.get("/rawMtrls", dependencies=[Depends(JWTBearer())])
def get_raw_mtrls():

    rawMtrls = fs_db.get_all(constants.RAWMTRL)

    rawMtrls_res = {'RawMtrls':[]}
    for rawMtrl in rawMtrls:
        rawMtrls_res['RawMtrls'].append(rawMtrl.to_dict())
    return JSONResponse(content=rawMtrls_res, status_code=200)

@app.post("/menuItem", dependencies=[Depends(JWTBearer())])
def add_menu_item(menu: Menu):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.MENU, menu.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Menu Item.', status_code=500)
    return JSONResponse(content='Successfully added Menu Item.', status_code=200)

@app.get("/menuItems", dependencies=[Depends(JWTBearer())])
def get_menu_items():

    menu_items = fs_db.get_all(constants.MENU)

    menu_items_res = {'MenuItems':[]}
    for menu_item in menu_items:
        menu = menu_item.to_dict()
        menu["Remaining"] = fs_db.get_remaining_stock(menu)
        menu_items_res['MenuItems'].append(menu)
    return JSONResponse(content=menu_items_res, status_code=200)

@app.put("/update/{doc_id}", dependencies=[Depends(JWTBearer())])
def update(doc_id: str, doc: dict):
    print(doc_id)
    isUpdated = fs_db.update_target(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

# Transaction

@app.put("/trans/update/{doc_id}", dependencies=[Depends(JWTBearer())])
def update_trans(doc_id: str, doc: dict):
    print(doc_id)
    
    # if game tracker update
    if constants.GAME_TRACKER in doc_id:
        gt_doc = fs_db.get_by_id_trans(doc_id)
        if gt_doc.get("isActive"):
            if gt_doc.get("Players",[]) is None:
                gt_plyrs = []
            else:
                gt_plyrs = gt_doc.get("Players",[])
            del_plyrs = [plyr for plyr in gt_plyrs if plyr not in doc.get("Players",[])]

            # update player not playing
            for plyr_upd in del_plyrs:
                fs_db.update_target(plyr_upd["Id"], {"isPlaying": False})
            # update player playing
            if doc["Players"] is not None:
                for player in doc["Players"]:
                    fs_db.update_target(player["Id"], {"isPlaying": True})

    # if canteen tracker update
    if constants.CANTEEN_TRACKER in doc_id:
        # update Cost
        cost = 0
        players = doc["Players"]
        if players is not None:
            for player in players:
                player["Cost"] = 0
                menus = player["MenuItems"]
                if menus is not None:
                    for menu in menus:
                        player["Cost"] += menu["Cost"] * menu["Quan"]
                        cost += menu["Cost"] * menu["Quan"]
        doc["Players"] = players

        menus = doc["MenuItems"]
        
        if menus is not None:
            for menu in menus:
                cost += menu["Cost"]* menu["Quan"]
        doc["Cost"] = cost
        fs_db.update_stock_edit(doc)

    isUpdated = fs_db.update_trans(doc_id, doc)

    

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

@app.get("/game/track", dependencies=[Depends(JWTBearer())]) 
def get_game_trackers():

    gt_docs = fs_db.get_all_trans(constants.GAME_TRACKER)

    gt_docs_res = {'GameTrackers':[]}
    for gt_doc in gt_docs:
        gt_docs_res['GameTrackers'].append(gt_doc.to_dict())
    return JSONResponse(content=gt_docs_res, status_code=200)

@app.get("/game/track/active", dependencies=[Depends(JWTBearer())])
def get_active_game_trackers():

    gt_docs = fs_db.get_active_game_trackers(constants.GAME_TRACKER)

    gt_docs_res = {'GameTrackers':[]}
    for gt_doc in gt_docs:
        gt_docs_res['GameTrackers'].append(gt_doc.to_dict())
    return JSONResponse(content=gt_docs_res, status_code=200)

@app.get("/game/track/{gt_id}", dependencies=[Depends(JWTBearer())])
def get_game_tracker(gt_id: str):

    gt_doc = fs_db.get_by_id_trans(gt_id)
    if gt_doc is None:
        return JSONResponse(content='Document not present in DB.', status_code=500)
    return JSONResponse(content=gt_doc, status_code=200)

@app.post("/game/start", dependencies=[Depends(JWTBearer())])
def start_game(gt_doc: GameTracker):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded, doc = fs_db.start_game(gt_doc.dict())

    # update player playing
    if isAdded and gt_doc.Players is not None:
        for player in gt_doc.Players:
            fs_db.update_target(player.Id, {"isPlaying": True})

    if not isAdded:
        return JSONResponse(content='Failed to Start Game.', status_code=500)
    return JSONResponse(content=doc, status_code=200)

@app.get("/game/generate_bill/{gt_id}", dependencies=[Depends(JWTBearer())])
def generate_bill(gt_id: str):
    if not game.process_generate_bill(gt_id):
        return JSONResponse(content='Failed to generate bill.', status_code=500)
    return JSONResponse(content="Bill Generated successfully.", status_code=200)

@app.post("/game/bill/pay/{bt_id}", dependencies=[Depends(JWTBearer())])
def pay_bill(bt_id:str, modes: dict):
    if not game.process_pay_bill(bt_id, modes, modes.pop("discount")):
        return JSONResponse(content='Failed to pay bill.', status_code=500)
    return JSONResponse(content="Bill Paid.", status_code=200)

@app.post("/game/end", dependencies=[Depends(JWTBearer())])
def end_game(gt_end: GameTrackerEndRequest):
    if not game.process_end_game(gt_end):
        return JSONResponse(content='Failed to End Game.', status_code=500)
    return JSONResponse(content="Game ended successfully.", status_code=200)

@app.post("/canteen", dependencies=[Depends(JWTBearer())])
def add_canteen(canteen_dict: CanteenTracker):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = False
    doc = None
    # check already present
    gt_doc = fs_db.get_by_id_trans(canteen_dict.GameTrackerId)
    if gt_doc["CanteenTrackerId"] is None:
        # update Cost
        cost = 0
        players = canteen_dict.Players
        if players is not None:
            for player in canteen_dict.Players:
                player.Cost = 0
                menus = player.MenuItems
                if menus is not None:
                    for menu in menus:
                        player.Cost += menu.Cost * menu.Quan
                        cost += menu.Cost * menu.Quan
        canteen_dict.Players = players

        menus = canteen_dict.MenuItems
        
        if menus is not None:
            for menu in canteen_dict.MenuItems:
                cost += menu.Cost* menu.Quan
        canteen_dict.Cost = cost


        isAdded, doc = fs_db.add_trans(constants.CANTEEN_TRACKER, canteen_dict.dict())

        # update game tracker with ct id
        gt_update = {
                "CanteenTrackerId" : doc['Id']
            }

        fs_db.update_trans(canteen_dict.GameTrackerId, gt_update)

    if not isAdded:
        JSONResponse(content='Failed to Add Canteen', status_code=500)
    return JSONResponse(content=doc, status_code=201)

@app.put("/canteen/update/{doc_id}", dependencies=[Depends(JWTBearer())])
def update_ct(doc_id: str, doc: dict):
    print(doc_id, doc)

    isUpdated, doc_res = fs_db.update_ct(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content=doc_res, status_code=200)

@app.post("/game/canteen/{gt_id}", dependencies=[Depends(JWTBearer())])
def add_game_canteen(gt_id: str, doc: dict):
    isAdded, doc = fs_db.add_game_canteen(gt_id, doc)
    if not isAdded:
        JSONResponse(content='Failed to Add.', status_code=500)
    return JSONResponse(content=doc, status_code=200)

@app.post("/ind/canteen", dependencies=[Depends(JWTBearer())])
def add_ind_canteen(doc: dict):
    isAdded, doc = fs_db.add_ind_canteen(doc)
    if not isAdded:
        JSONResponse(content='Failed to Ind Add.', status_code=500)
    return JSONResponse(content=doc, status_code=200)

@app.get("/ind/canteen/track", dependencies=[Depends(JWTBearer())])
def get_ind_canteen_trackers():

    ct_docs = fs_db.get_all_ind_canteen()

    ct_docs_res = {'CanteenTrackers':[]}
    for ct_doc in ct_docs:
        ct_docs_res['CanteenTrackers'].append(ct_doc.to_dict())
    return JSONResponse(content=ct_docs_res, status_code=200)

@app.get("/ind/canteen/generate_bill/{ct_id}", dependencies=[Depends(JWTBearer())])
def ind_canteen_generate_bill(ct_id: str):
    if not game.process_ind_canteen_generate_bill(ct_id):
        return JSONResponse(content='Failed to generate bill.', status_code=500)
    return JSONResponse(content="Bill Generated successfully.", status_code=200)

@app.get("/canteen/track", dependencies=[Depends(JWTBearer())])
def get_canteen_trackers():

    ct_docs = fs_db.get_all(constants.CANTEEN_TRACKER)

    ct_docs_res = {'CanteenTrackers':[]}
    for ct_doc in ct_docs:
        ct_docs_res['CanteenTrackers'].append(ct_doc.to_dict())
    return JSONResponse(content=ct_docs_res, status_code=200)

# @app.get("/canteen/track/{ct_id}")
# def get_canteen_tracker_by_id(ct_id: str):

#     ct_doc = fs_db.get_by_id(ct_id)

#     return JSONResponse(content=ct_doc, status_code=200)

@app.get("/canteen/track/{gt_id}", dependencies=[Depends(JWTBearer())])
def get_canteen_tracker_by_gt_id(gt_id: str):

    ct_docs = fs_db.get_ct_by_gt_id(gt_id)
    ct_doc = {}
    for ct_doc in ct_docs:
        ct_doc = ct_doc.to_dict()
    return JSONResponse(content=ct_doc, status_code=200)

@app.put("/game/update/{doc_id}", dependencies=[Depends(JWTBearer())])
def update_game(doc_id: str, doc: dict):
    print(doc_id)
    isUpdated = fs_db.update_trans(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

@app.get("/game/bills", dependencies=[Depends(JWTBearer())])
def get_game_all_bills():

    bt_docs = fs_db.get_all_plyr_bills(False)

    return JSONResponse(content=bt_docs, status_code=200)

@app.get("/game/bills/pending", dependencies=[Depends(JWTBearer())])
def get_game_all_pending_bills():
    try:

        bt_docs = fs_db.get_all_pending_bills(constants.BILL_TRACKER)

        bt_docs_res = {'PendingBillTrackers':[]}
        for bt_doc in bt_docs:
            bt_docs_res['PendingBillTrackers'].append(bt_doc.to_dict())
    except Exception as e:
        print(e)
    return JSONResponse(content=bt_docs_res, status_code=200)

@app.get("/game/closed_not_billed", dependencies=[Depends(JWTBearer())])
def get_closed_not_billed_games():
    docs = fs_db.get_closed_not_billed_games()
    return JSONResponse(content=docs, status_code=200)

@app.get("/game/bills/paid", dependencies=[Depends(JWTBearer())])
def get_game_paid_bills():

    bt_docs = fs_db.get_all_plyr_bills(True)
    return JSONResponse(content=bt_docs, status_code=200)

@app.get("/dailycollections", dependencies=[Depends(JWTBearer())])
def get_daily_collections():
    dc_docs = fs_db.get_all_trans(constants.DAILY_COLLECT)

    dc_docs_res = {'DailyCollections':[]}
    for dc_doc in dc_docs:
        dc_docs_res['DailyCollections'].append(dc_doc.to_dict())
    return JSONResponse(content=dc_docs_res, status_code=200)

@app.post("/dailycollect", dependencies=[Depends(JWTBearer())])
def save_dailycollect(dailyCollect: DailyCollect):
    isAdded, dc = fs_db.add_dailycollect(dailyCollect.dict())
    isUpdated = daily_collect.update_safe(dc)
    if not isAdded:
        JSONResponse(content='Failed to Add DailyCollect.', status_code=500)
    if not isUpdated:
        JSONResponse(content='Failed to Update Safe.', status_code=500)
    return JSONResponse(content='Successfully added DailyCollect.', status_code=201)

@app.get("/safe", dependencies=[Depends(JWTBearer())])
def get_safe():
    safe = fs_db.get_safe()
    if safe is None:
        return JSONResponse(content='Document not present in DB.', status_code=500)
    return JSONResponse(content=safe, status_code=200)

@app.post("/trash", dependencies=[Depends(JWTBearer())])
def trash(itm: dict):
    is_trashed = fs_db.trash(itm)
    if not is_trashed:
        JSONResponse(content='Failed to Update Trash.', status_code=500)
    return JSONResponse(content='Successfully Updated Trash.', status_code=200)

@app.get("/trash", dependencies=[Depends(JWTBearer())])
def get_trash():
    trash = fs_db.get_trash()
    if trash is None:
        return JSONResponse(content='Document not present in DB.', status_code=500)
    return JSONResponse(content=trash, status_code=200)

@app.post("/branch", dependencies=[Depends(JWTBearer())])
def add_branch(branch: Branch):
    is_added = fs_db.add_branch(branch.dict())
    if not is_added:
        return JSONResponse(content='Branch not created.', status_code=500)
    return JSONResponse(content="Branch Created Successfully.", status_code=200)

@app.get("/branches", dependencies=[Depends(JWTBearer())])
def get_all_branches():
    branches = fs_db.get_all(constants.BRANCH)
    branches_res = {'Branches':[]}
    for branch in branches:
        branches_res['Branches'].append(branch.to_dict())
    return JSONResponse(content=branches_res, status_code=200)


# @app.exception_handler(ValidationError)
# def validation_exception_handler(request: Request, exc: ValidationError):
#     return JSONResponse(status_code=422, content={'detail':'Validation Failed.','Validation Errors': exc.errors()})

# @app.exception_handler(HTTPException)
# def http_exception_handler(request: Request, exc: HTTPException):
#     return JSONResponse(status_code=exc.status_code, content={'Server Error': exc.errors()})
    
if __name__ == "__main__":
#     # listener = ngrok.forward(8000, authtoken = '2jcb2Za6XtLuFkJ0GoenNZ1cNNo_3GRT9swyPEPZrC1v6wX5A')
#     # print(listener.url())
#     # uvicorn.run("main:app", host=listener.url(), reload= True)
    uvicorn.run("main:app", port=8000, reload= True)

