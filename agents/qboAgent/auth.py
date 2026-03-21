"""
Token management for QBO API tools.

Adapted from daily-qbo-api/qbo.py. Reads tokens from Postgres qbo_connection
table, refreshes via Intuit OAuth when needed, caches in session state.
"""

import base64
import logging
from datetime import datetime, timezone, timedelta

import requests
import psycopg2
import psycopg2.extras

from .config import QB_CLIENT_ID, QB_CLIENT_SECRET, TOKEN_URL, DATABASE_URL

logger = logging.getLogger("qboAgent.auth")


def _db():
    return psycopg2.connect(DATABASE_URL)


def _to_aware_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        s = dt.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _basic_auth_header() -> str:
    raw = f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _refresh_access_token(refresh_token: str) -> dict:
    """Call Intuit token endpoint to refresh. Returns {access_token, refresh_token, expires_in}."""
    headers = {
        "Authorization": _basic_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {resp.status_code} {resp.text}")
    return resp.json()


def ensure_fresh_token(tool_context) -> tuple:
    """
    Return (access_token, realm_id).

    Reads realm_id from tool_context.state. Checks session-cached token first,
    then falls back to Postgres qbo_connection table. Refreshes if expired or
    expiring within 2 minutes.
    """
    state = tool_context.state
    realm_id = state.get("realm_id")
    if not realm_id:
        raise RuntimeError("No realm_id in session state. QBO is not connected.")

    # Check session-cached token
    cached_token = state.get("qbo_access_token")
    cached_expires = state.get("qbo_token_expires_at")
    now = datetime.now(timezone.utc)

    if cached_token and cached_expires:
        expires_at = _to_aware_utc(cached_expires)
        if expires_at and (expires_at - now) > timedelta(minutes=2):
            return (cached_token, realm_id)

    # Fall back to Postgres
    if not DATABASE_URL:
        # No DB configured — use whatever is in state (env-var mode)
        if cached_token:
            return (cached_token, realm_id)
        raise RuntimeError("No DATABASE_URL configured and no cached token available.")

    with _db() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT access_token, refresh_token, token_expires_at FROM qbo_connection WHERE realm_id = %s LIMIT 1",
            (realm_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"No qbo_connection found for realm {realm_id}")

        access_token = row["access_token"]
        refresh_token = row.get("refresh_token")
        expires_at = _to_aware_utc(row.get("token_expires_at"))

        needs_refresh = (
            not access_token
            or expires_at is None
            or (expires_at - now) <= timedelta(minutes=2)
        )

        if needs_refresh:
            if not refresh_token:
                logger.warning("Token expired and no refresh_token for realm %s", realm_id)
                if access_token:
                    return (access_token, realm_id)
                raise RuntimeError("Token expired and no refresh token available.")

            new_tok = _refresh_access_token(refresh_token)
            access_token = new_tok["access_token"]
            new_refresh = new_tok.get("refresh_token", refresh_token)
            expires_in = int(new_tok.get("expires_in", 3600))
            new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            cur.execute(
                """UPDATE qbo_connection
                   SET access_token = %s, refresh_token = %s, token_expires_at = %s
                   WHERE realm_id = %s""",
                (access_token, new_refresh, new_expires_at, realm_id),
            )
            conn.commit()
            expires_at = new_expires_at

        # Cache in session state
        state["qbo_access_token"] = access_token
        state["qbo_token_expires_at"] = expires_at.isoformat() if expires_at else None

        return (access_token, realm_id)
