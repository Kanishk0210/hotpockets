from pydantic import BaseModel, Field
from typing import Union, List
from util import constants


class DailyCollect(BaseModel):
    LastCollectTmstmp: str
    CurrentCollectTmstmp: str
    Collection: Union[float, int]
    AvailableCash: Union[float, int] = 0
    Note: str = ""
    Type: str = constants.DAILY_COLLECT