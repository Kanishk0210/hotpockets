# This file is responsible for signing , encoding , decoding and returning JWTS
import time
from typing import Dict

import jwt


JWT_SECRET = '4b925c51afbef8811ade4ab8e669a7e9'
JWT_ALGORITHM = "HS256"


def token_response(token: str, br_cd: str, perms):
    return {
        "access_token": token,
        "branch": br_cd,
        "permissions": perms
    }

# function used for signing the JWT string
def signJWT(user_id: str, br_cd: str, perms) -> Dict[str, str]:
    payload = {
        "user_id": user_id,
        "expires": time.time() + 32400,
        "branch": br_cd,
        "permissions": perms
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token_response(token, br_cd, perms)


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        print(decoded_token)
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except:
        return {}

def signJWT_branch(token:str, br_cd: str):
    decoded_token = decodeJWT(token)
    decoded_token["branch"] = br_cd
    token = jwt.encode(decoded_token, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token_response(token, br_cd, decoded_token["permissions"])