from pydantic import BaseModel, Field
from typing import Union, List
from util import constants


class Branch(BaseModel):
    Address: str
    Name: str
    Id: str = None
    Type: str = constants.BRANCH
    isActive: bool = True