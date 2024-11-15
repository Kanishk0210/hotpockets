from pydantic import BaseModel, Field
from typing import Union, List
from util import constants
import uuid

from models.CanteenTracker import Player

class Mode(BaseModel):
    Cash: List[Union[float, int]] = []
    Online: List[Union[float, int]] = []
    Credit: List[Union[float, int]] = []

class MenuItem(BaseModel):
    Id: str
    Cost: Union[float, int]
    Quan: Union[float, int]

class BillTracker(BaseModel):
    def __init__(self, canteenTrackerId: str, gameTrackerId: str, gameId: str):
        super().__init__(Type = constants.BILL_TRACKER, CanteenTrackerId = canteenTrackerId,
            GameTrackerId = gameTrackerId, GameId = gameId)
    
    def get_txid(self):
        return constants.BILL_TRACKER + '::' + str(uuid.uuid1())  


    Id: str = None
    Player: Player = None
    Type: str = constants.BILL_TRACKER
    TxId: str = None
    CanteenTrackerId: str = None
    GameTrackerId: str = None
    GameId: str = None
    GameCost: Union[float, int] = 0
    CanteenCost: Union[float, int] = 0
    TotalCost: Union[float, int] = 0 # sum of canteencost, gamecost
    isPaid: bool = False
    Mode: Mode = None
