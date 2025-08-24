# foxmask/auth/routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from foxmask.auth.dependencies import get_current_active_user
from foxmask.auth.schemas import User, Token
from foxmask.core.config import get_settings
from foxmask.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # This endpoint would typically validate against Casdoor
    # For simplicity, we're using a basic implementation
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user