"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.auth.dependencies import CurrentUser, DbSession
from app.auth.service import AuthService
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SessionRead,
    TokenPair,
)
from app.schemas.common import Message
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


@router.get("/registration-open", summary="Whether bootstrap registration is allowed")
async def registration_open(session: DbSession) -> dict[str, bool]:
    return {"open": await AuthService(session).registration_open()}


@router.post("/register", response_model=AuthResponse, status_code=201, summary="Bootstrap owner")
async def register(payload: RegisterRequest, request: Request, session: DbSession) -> AuthResponse:
    service = AuthService(session)
    ip, user_agent = _client_meta(request)
    user = await service.register(payload.email, payload.password, payload.full_name)
    _, access_token, refresh_token = await service.login(
        payload.email,
        payload.password,
        device_name=payload.full_name,
        ip_address=ip,
        user_agent=user_agent,
    )
    return AuthResponse(
        user=UserRead.model_validate(user),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=0),
    )


@router.post("/login", response_model=AuthResponse, summary="Login")
async def login(payload: LoginRequest, request: Request, session: DbSession) -> AuthResponse:
    ip, user_agent = _client_meta(request)
    user, access_token, refresh_token = await AuthService(session).login(
        payload.email,
        payload.password,
        device_name=payload.device_name,
        ip_address=ip,
        user_agent=user_agent,
    )
    return AuthResponse(
        user=UserRead.model_validate(user),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=0),
    )


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
async def refresh(payload: RefreshRequest, request: Request, session: DbSession) -> TokenPair:
    ip, user_agent = _client_meta(request)
    _, access_token, refresh_token = await AuthService(session).refresh(
        payload.refresh_token, ip_address=ip, user_agent=user_agent
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=0)


@router.post("/logout", response_model=Message, summary="Revoke a session")
async def logout(payload: LogoutRequest, session: DbSession) -> Message:
    await AuthService(session).logout(payload.refresh_token)
    return Message(detail="Logged out")


@router.get("/me", response_model=UserRead, summary="Current user")
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.get("/sessions", response_model=list[SessionRead], summary="Active sessions/devices")
async def sessions(user: CurrentUser, session: DbSession) -> list[SessionRead]:
    records = await AuthService(session).list_sessions(user.id)
    return [SessionRead.model_validate(record) for record in records]
