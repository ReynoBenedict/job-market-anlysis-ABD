from __future__ import annotations

import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from talentscope.api.errors import ApiError
from talentscope.config import Settings, get_settings
from talentscope.db import get_session_factory


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def require_admin(
    settings: SettingsDep, authorization: Annotated[str | None, Header()] = None
) -> str:
    """Bearer-token check for admin routes. Returns the actor name for the audit log.

    The admin API is off entirely unless ADMIN_API_TOKEN is configured.
    """
    if settings.admin_api_token is None:
        raise ApiError(503, "admin_disabled", "Admin API is disabled on this deployment.")
    scheme, _, token = (authorization or "").partition(" ")
    expected = settings.admin_api_token.get_secret_value()
    if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), expected.encode()):
        raise ApiError(401, "unauthorized", "A valid admin bearer token is required.")
    return "admin"


AdminDep = Annotated[str, Depends(require_admin)]
