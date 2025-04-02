from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from util import constants

class Audit(BaseModel):
    Id: str = None
    Type: str = constants.AUDIT
    DocId: str = None
    DocType: str = None
    Action: str = None # "ADD", "EDIT", "DELETE"
    EmployeeId: str
    EmployeeName: str
    Branch: str 
    CreatedTmStmp: str = None
    PreviousValue: Optional[dict] = None
    NewValue: Optional[dict] = None
    