from fastapi import FastAPI, APIRouter, Body, Depends, Request

from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from auth.auth_bearer import JWTBearer
from auth.auth_handler import signJWT, decodeJWT

from models.UserLoginSchema import UserLoginSchema
from database import firebase_conn as fs_db
from util import util, constants

import uvicorn

app = FastAPI()

# authb = auth_bearer()

origins = [
    "http://localhost:3000",
    "https://hot-pocket-47985.web.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_methods = ["GET","POST","PUT","DELETE"],
    allow_headers = ["*"]
)

def check_user(data: UserLoginSchema):
    users = fs_db.get_all(constants.EMPLOYEE)
    br_cd = ""
    for usr in users:
        user = usr.to_dict()
        user_dec_pass = util.decode_pass(user["Password"])
        if user["Email"] == data.email and user_dec_pass == data.password:
            br_cd = user["Branch"]
            return True, br_cd
    return False

@app.get("/", dependencies= [Depends(JWTBearer())] ,tags=["root"])
async def root(request: Request):
    print(decodeJWT(request.headers["authorization"]))
    return {"message": "Hot Pockets"}, "a", "b"

if __name__ == "__main__":
#     # listener = ngrok.forward(8000, authtoken = '2jcb2Za6XtLuFkJ0GoenNZ1cNNo_3GRT9swyPEPZrC1v6wX5A')
#     # print(listener.url())
#     # uvicorn.run("main:app", host=listener.url(), reload= True)
    uvicorn.run("test:app", port=8000, reload= True)