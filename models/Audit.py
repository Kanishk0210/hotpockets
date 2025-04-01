from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from util import constants

class RawMaterialAudit(BaseModel):
    Id: str = None
    Type: str = constants.RAWMTRL_AUDIT
    RawMaterialId: str
    Action: str  # "ADD", "EDIT", "DELETE"
    EmployeeId: str
    CreatedAt: str
    CreatedBy: str
    PreviousValue: Optional[dict] = None
    NewValue: Optional[dict] = None
    Branch: str 