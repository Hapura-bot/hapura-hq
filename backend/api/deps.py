import os
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Header, HTTPException
from config import get_settings

_app = None


def get_firebase_app():
    global _app
    if _app is None:
        settings = get_settings()
        cred_path = os.path.join(
            os.path.dirname(__file__), "..", settings.firebase_credentials_path
        )
        cred = credentials.Certificate(os.path.abspath(cred_path))
        _app = firebase_admin.initialize_app(cred)
    return _app


ALLOWED_EMAILS = {
    'unithree3@gmail.com',
    'dogiatrunghieu123@gmail.com',
    'hapuragroup@gmail.com',
}


async def get_current_user(authorization: str = Header(None)) -> str:
    settings = get_settings()
    if settings.app_env == "development" and not authorization:
        return "dev"
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    get_firebase_app()
    try:
        token = authorization.removeprefix("Bearer ")
        decoded = auth.verify_id_token(token)
        email = decoded.get('email', '')
        if email not in ALLOWED_EMAILS:
            raise HTTPException(status_code=403, detail="Access denied")
        return decoded["uid"]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
