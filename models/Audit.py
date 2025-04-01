from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from util import constants

class Audit(BaseModel):
    Id: str = None
    Type: str = constants.AUDIT
    DocId: str
    Action: str  # "ADD", "EDIT", "DELETE"
    EmployeeId: str
    EmployeeName: str
    Branch: str 
    CreatedTmStmp: str = None
    PreviousValue: Optional[dict] = None
    NewValue: Optional[dict] = None
    

    def __init__(self, empId, empName, branch):
        self.EmployeeId = empId
        self.EmployeeName = empName
        self.Branch = branch