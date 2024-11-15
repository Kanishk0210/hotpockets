from pydantic import BaseModel, Field
from typing import Union, List
from util import constants

class RawMtrl(BaseModel):
    Id: str = None
    Name: str
    Type: str = Field(default=constants.RAWMTRL)
    Quantity: Union[float, int] = None
    CostPerItem: Union[float, int] =None #Rs
    QuantityBox: Union[float, int] = None
    QuantityPerBox: Union[float, int] = None
    CostPerBox: Union[float, int] =None #Rs
    Expiry: str = None

class Ingredient(BaseModel):
    Name: str
    Quantity: Union[float, int]
    RawMtrlId: str
    CostPerItem: Union[float, int] =None

class Menu(BaseModel):
    Id: str = None
    Name: str
    Type: str = Field(default=constants.MENU)
    Ingredients: List[Ingredient] 
    Price: Union[float, int]