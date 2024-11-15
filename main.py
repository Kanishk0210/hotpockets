import random
import string
# import ngrok

from fastapi import FastAPI, APIRouter, Body, Depends

from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

import uvicorn

from database import firebase_conn as fs_db
from services import game
from models.Player import Player
from models.Game import Game
from models.Employee import Employee
from models.Inventory import Inventory
from models.Menu import RawMtrl
from models.Menu import Menu
from models.UserLoginSchema import UserLoginSchema
from models.GameTracker import GameTracker, GameTrackerEndRequest
from models.CanteenTracker import CanteenTracker
from util import util, constants
# from auth import auth_bearer, auth_handler
from auth.auth_bearer import JWTBearer
from auth.auth_handler import signJWT

app = FastAPI()

# authb = auth_bearer()

origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

def check_user(data: UserLoginSchema):
    for user in users:
        if user.email == data.email and user.password == data.password:
            return True
    return False

@app.get("/")
async def root():
    return {"message": "Hot Pockets"}

@app.post("/user/login", tags=["user"])
def user_login(user: UserLoginSchema = Body(...)):
    if check_user(user):
        return signJWT(user.email)
    return {
        "error": "Wrong login details!"
    }

@app.get("/players")
def get_players():

    players = fs_db.get_all(constants.PLAYER)

    players_res = {'Players':[]}
    for player in players:
        players_res['Players'].append(player.to_dict())
    return JSONResponse(content=players_res, status_code=200)

@app.post("/player")
def add_player(player: Player):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.PLAYER, player.dict())

    if not isAdded: 
        JSONResponse(content='Failed to Add Player.', status_code=500)
    return JSONResponse(content='Successfully added Player.', status_code=201)

@app.get("/games")
def get_games():

    games = fs_db.get_all_games(constants.GAME)

    return JSONResponse(content=games, status_code=200)

@app.post("/game")
def add_game(game: Game):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.GAME, game.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Game.', status_code=500)
    return JSONResponse(content='Successfully added Game.', status_code=201)

@app.post("/employee")
def add_emp(emp: Employee):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.EMPLOYEE, emp.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Employee.', status_code=500)
    return JSONResponse(content='Successfully added Employee.', status_code=201) 

@app.get("/employees")
def get_emps():

    emps = fs_db.get_all(constants.EMPLOYEE)

    emp_res = {'Employees':[]}
    for e in emps:
        emp_res['Employees'].append(e.to_dict())
    return JSONResponse(content=emp_res, status_code=200)

@app.post("/inventory")
def add_inv(inv: Inventory):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.INVENTORY, inv.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Inventory.', status_code=500)
    return JSONResponse(content='Successfully added Inventory.', status_code=201)

@app.get("/inventories")
def get_invs():

    invs = fs_db.get_all(constants.INVENTORY)

    inv_res = {'Inventories':[]}
    for i in invs:
        inv_res['Inventories'].append(i.to_dict())
    return JSONResponse(content=inv_res, status_code=200)

@app.post("/rawMtrl")
def add_raw(rawMtrl: RawMtrl):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.RAWMTRL, rawMtrl.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Raw Material.', status_code=500)
    return JSONResponse(content='Successfully added Raw Material.', status_code=201)

@app.get("/rawMtrls")
def get_raw_mtrls():

    rawMtrls = fs_db.get_all(constants.RAWMTRL)

    rawMtrls_res = {'RawMtrls':[]}
    for rawMtrl in rawMtrls:
        rawMtrls_res['RawMtrls'].append(rawMtrl.to_dict())
    return JSONResponse(content=rawMtrls_res, status_code=200)

@app.post("/menuItem")
def add_menu_item(menu: Menu):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp
    isAdded = fs_db.add(constants.MENU, menu.dict())

    if not isAdded:
        JSONResponse(content='Failed to Add Menu Item.', status_code=500)
    return JSONResponse(content='Successfully added Menu Item.', status_code=200)

@app.get("/menuItems")
def get_menu_items():

    menu_items = fs_db.get_all(constants.MENU)

    menu_items_res = {'MenuItems':[]}
    for menu_item in menu_items:
        menu_items_res['MenuItems'].append(menu_item.to_dict())
    return JSONResponse(content=menu_items_res, status_code=200)

@app.put("/update/{doc_id}")
def update(doc_id: str, doc: dict):
    print(doc_id)
    isUpdated = fs_db.update_target(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

# Transaction

@app.put("/trans/update/{doc_id}")
def update_trans(doc_id: str, doc: dict):
    print(doc_id)
    isUpdated = fs_db.update_trans(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

@app.get("/game/track") 
def get_game_trackers():

    gt_docs = fs_db.get_all_trans(constants.GAME_TRACKER)

    gt_docs_res = {'GameTrackers':[]}
    for gt_doc in gt_docs:
        gt_docs_res['GameTrackers'].append(gt_doc.to_dict())
    return JSONResponse(content=gt_docs_res, status_code=200)

@app.get("/game/track/active")
def get_active_game_trackers():

    gt_docs = fs_db.get_active_game_trackers(constants.GAME_TRACKER)

    gt_docs_res = {'GameTrackers':[]}
    for gt_doc in gt_docs:
        gt_docs_res['GameTrackers'].append(gt_doc.to_dict())
    return JSONResponse(content=gt_docs_res, status_code=200)

@app.get("/game/track/{gt_id}")
def get_game_tracker(gt_id: str):

    gt_doc = fs_db.get_by_id_trans(gt_id)
    if gt_doc is None:
        return JSONResponse(content='Document not present in DB.', status_code=500)
    return JSONResponse(content=gt_doc, status_code=200)

@app.post("/game/start")
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

@app.get("/game/generate_bill/{gt_id}")
def generate_bill(gt_id: str):
    if not game.process_generate_bill(gt_id):
        return JSONResponse(content='Failed to End Game.', status_code=500)
    return JSONResponse(content="Game ended successfully.", status_code=200)

@app.post("/game/end")
def end_game(gt_end: GameTrackerEndRequest):
    if not game.process_end_game(gt_end):
        return JSONResponse(content='Failed to End Game.', status_code=500)
    return JSONResponse(content="Game ended successfully.", status_code=200)

@app.post("/canteen")
def add_canteen(canteen_dict: CanteenTracker):
    #chars = string.ascii_letters + string.digits
    # doc_id = 'Player::'+ player.name[:3].upper()+'_'+player.phone[-4:]+'_'+''.join(random.choices(chars, k=4)) # Player::ASH_6891_oWtp

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

@app.put("/canteen/update/{doc_id}")
def update_ct(doc_id: str, doc: dict):
    print(doc_id, doc)

    isUpdated, doc_res = fs_db.update_ct(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content=doc_res, status_code=200)

@app.get("/canteen/track")
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

@app.get("/canteen/track/{gt_id}")
def get_canteen_tracker_by_gt_id(gt_id: str):

    ct_docs = fs_db.get_ct_by_gt_id(gt_id)
    ct_doc = {}
    for ct_doc in ct_docs:
        ct_doc = ct_doc.to_dict()
    return JSONResponse(content=ct_doc, status_code=200)

@app.put("/game/update/{doc_id}")
def update_game(doc_id: str, doc: dict):
    print(doc_id)
    isUpdated = fs_db.update_trans(doc_id, doc)

    if not isUpdated:
        JSONResponse(content='Failed to Update.', status_code=500)
    return JSONResponse(content='Successfully Updated.', status_code=200)

@app.get("/game/bills")
def get_game_all_bills():

    bt_docs = fs_db.get_all_trans(constants.BILL_TRACKER)

    bt_docs_res = {'BillTrackers':[]}
    for bt_doc in bt_docs:
        bt_docs_res['BillTrackers'].append(bt_doc.to_dict())
    return JSONResponse(content=bt_docs_res, status_code=200)

@app.get("/game/bills/pending")
def get_game_all_pending_bills():

    bt_docs = fs_db.get_all_pending_bills(constants.BILL_TRACKER)

    bt_docs_res = {'PendingBillTrackers':[]}
    for bt_doc in bt_docs:
        bt_docs_res['PendingBillTrackers'].append(bt_doc.to_dict())
    return JSONResponse(content=bt_docs_res, status_code=200)

@app.get("/game/closed_not_billed")
def get_closed_not_billed_games():
    docs = fs_db.get_closed_not_billed_games()
    return JSONResponse(content=docs, status_code=200)




# @app.exception_handler(ValidationError)
# def validation_exception_handler(request: Request, exc: ValidationError):
#     return JSONResponse(status_code=422, content={'detail':'Validation Failed.','Validation Errors': exc.errors()})

# @app.exception_handler(HTTPException)
# def http_exception_handler(request: Request, exc: HTTPException):
#     return JSONResponse(status_code=exc.status_code, content={'Server Error': exc.errors()})
    
if __name__ == "__main__":
    # listener = ngrok.forward(8000, authtoken = '2jcb2Za6XtLuFkJ0GoenNZ1cNNo_3GRT9swyPEPZrC1v6wX5A')
    # print(listener.url())
    # uvicorn.run("main:app", host=listener.url(), reload= True)
    uvicorn.run("main:app", port=8000, reload= True)

