# foxmask/domains/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from jose import JWTError, jwt
from foxmask.core.config import get_settings
from foxmask.core.exceptions import AuthenticationError
from foxmask.auth.schemas import User

security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
settings = get_settings()

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = AuthenticationError(
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.CASDOOR_CERT or settings.SECRET_KEY,
            algorithms=["RS256" if settings.CASDOOR_CERT else "HS256"],
            options={"verify_aud": False}
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # Extract user information from token
        username = payload.get("preferred_username", "")
        email = payload.get("email", "")
        
        return User(id=user_id, username=username, email=email)
    except JWTError:
        raise credentials_exception

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    # Add any additional user status checks here
    return current_user