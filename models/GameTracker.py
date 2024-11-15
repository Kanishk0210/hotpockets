from pydantic import BaseModel, Field
from typing import Union, List
from util import constants
import uuid

class GameTrackerEndRequest(BaseModel):
    Id: str
    EndTmStmp: str

class Player(BaseModel):
    Id: str
    Phone: str = Field(min_length=10)
    Name: str
    UniqueKey: str

class GameTracker(BaseModel):
    # def __init__(self):
    #     pass
    # def get_txid(self):
    #     return constants.GAME_TRACKER + '::' + str(uuid.uuid1())

    Id: str = None
    Type: str = constants.GAME_TRACKER
    TxId: str = None
    StrtTmStmp: str
    EndTmStmp: str = None
    DurationInMin: Union[float, int] = None
    Players: List[Player] = None
    GameId: str
    Cost: Union[float, int] = None
    CanteenTrackerId: str = None
    BillTrackerId: str = None
    isActive: bool = True
    isBilled: bool = False
    GamePlayers: List[str] = None