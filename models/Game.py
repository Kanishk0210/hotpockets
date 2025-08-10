from pydantic import BaseModel, Field
from typing import Union
from util import constants

class Game(BaseModel):
    Id: str = None
    Name: str
    Type: str = constants.GAME
    Category: str = Field(default='Others')
    CostPerT: Union[float, int] #Rs
    T: Union[float, int] #mins
    BaseCost: Union[float, int] = 20 #Rs
    isActive: bool
    CancelTime: Union[float, int] # mins
    XPlayerCharge: Union[float, int]
    Image: str = None
    GpioNo: str = None