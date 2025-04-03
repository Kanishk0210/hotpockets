from pydantic import BaseModel, Field, EmailStr
from util import constants

class BankDetail(BaseModel):
    AccountNumber: str
    AccountHolder: str
    BankName: str
    IFSCCode: str
    Branch: str

class Employee(BaseModel):
    Id: str = None
    Name: str
    Gender: str = Field(regex='^(M|F|O)$')
    Phone: str = Field(min_length=10)
    AltPhone: str = None
    Email: EmailStr
    DOB: str
    Type: str = Field(default=constants.EMPLOYEE)
    AdharCard: str
    BankDetails: BankDetail
    Permission: str
    Branch: str
    Password: str
    isActive: bool = False