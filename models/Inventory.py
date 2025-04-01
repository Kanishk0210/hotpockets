from pydantic import BaseModel, Field
from typing import Union
from util import constants

class Inventory(BaseModel):
    Id: str = None
    Name: str
    Type: str = Field(default=constants.INVENTORY)
    Quantity: Union[float, int]
    Cost: Union[float, int] #Rs
    Condition: str 
    #= Field(regex='^(Good|Average|Poor)$')
    Remark: str = None