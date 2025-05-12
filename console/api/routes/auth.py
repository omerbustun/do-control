from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import BaseModel
from console.auth import create_access_token
from console.config import settings

router = APIRouter()

# Simple hardcoded user for demo
DEMO_USER = {
    "username": "admin",
    "password": "admin"
}

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Get access token"""
    if form_data.username != DEMO_USER["username"] or form_data.password != DEMO_USER["password"]:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}