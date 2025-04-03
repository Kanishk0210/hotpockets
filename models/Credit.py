from pydantic import BaseModel, Field
from util import constants
from typing import Union, List, Dict

class Credit(BaseModel):
    Id: str
    PlayerId: str
    Type: str = Field(default=constants.CREDIT)
    Credit: Union[float, int] = 0
    Debit: dict = {}
