from pydantic import BaseModel, Field
from typing import Union, List
from util import constants
import uuid

class MenuItem(BaseModel):
    Id: str
    name: str
    Cost: Union[float, int]
    Quan: Union[float, int]

class Player(BaseModel):
    Id: str
    Name: str
    MenuItems: List[MenuItem]
    Cost: Union[float, int] = None # sum of([Cost * Quan])

class CanteenTracker(BaseModel):
    Id: str = None
    Type: str = constants.CANTEEN_TRACKER
    TxId: str = None
    Players: List[Player] = None
    GameId: str
    GameTrackerId: str
    MenuItems: List[MenuItem] = None
    Cost: Union[float, int] = None # sum of(player costs)
    isActive: bool = True