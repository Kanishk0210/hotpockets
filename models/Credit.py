from pydantic import BaseModel, Field
from util import constants
from typing import Union, List, Dict

class Mode(BaseModel):
    Cash: List[Union[float, int]] = []
    Online: List[Union[float, int]] = []

class Credit(BaseModel):
    Id: str
    PlayerId: str
    Type: str = Field(default=constants.CREDIT)
    Credit: Union[float, int] = 0
    Debit: Dict[str, Mode] = {}
