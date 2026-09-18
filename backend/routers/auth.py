"""Auth router — static bearer token from AUTH_TOKEN env var."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
def get_token(body: TokenRequest) -> TokenResponse:
    """
    Exchange the static secret token for a bearer token.
    In production this would be a real auth flow; for local deployment
    this is a simple secret-matching gate.
    """
    if body.token != settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
    return TokenResponse(access_token=settings.AUTH_TOKEN)
