from pydantic import BaseModel, Field
from util import constants

class Player(BaseModel):
    Id: str = None
    Name: str
    Gender: str 
    #= Field(regex='^(M|F|O)$')
    Phone: str = Field(min_length=10)
    Type: str = Field(default=constants.PLAYER)
    AadharCard: str = None
    UniqueKey: str = None
    isPlaying: bool = False
    Image: str = None

    #TODO:: unique key default value KAN0007
    #def get_unq_key(self):
