from pydantic import BaseModel, Field
from util import constants
from typing import Union, List

class Player(BaseModel):
    Id: str = None
    Name: str
    Gender: str = None #Field(regex='^(M|F|O)$')
    Phone: str = Field(min_length=10)
    Type: str = Field(default=constants.PLAYER)
    AadharCard: str = None
    UniqueKey: str = None
    isPlaying: bool = False
    Image: str = None
    Credit: Union[float, int] = 0

    #TODO:: unique key default value KAN0007
    #def get_unq_key(self):
