"""
Shared QBO API helpers — GET, POST, QBOQL query, formatting.

All helpers call ensure_fresh_token(), build URLs, handle 401 → refresh → retry.
"""

import logging
import requests

from .config import QBO_API_BASE, MINOR_VERSION
from .auth import ensure_fresh_token

logger = logging.getLogger("qboAgent.helpers")


def _build_url(realm_id: str, endpoint: str) -> str:
    return f"{QBO_API_BASE}/{realm_id}/{endpoint}"


def _auth_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


def _qbo_get(tool_context, endpoint: str, params: dict | None = None) -> dict:
    """GET with auth, 401 retry."""
    access_token, realm_id = ensure_fresh_token(tool_context)
    url = _build_url(realm_id, endpoint)
    p = {"minorversion": MINOR_VERSION}
    if params:
        p.update(params)

    resp = requests.get(url, headers=_auth_headers(access_token), params=p, timeout=30)

    if resp.status_code == 401:
        # Invalidate cached token and retry
        tool_context.state["qbo_access_token"] = None
        access_token, realm_id = ensure_fresh_token(tool_context)
        resp = requests.get(url, headers=_auth_headers(access_token), params=p, timeout=30)

    resp.raise_for_status()
    return resp.json()


def _qbo_post(tool_context, endpoint: str, payload: dict) -> dict:
    """POST JSON with auth, 401 retry."""
    access_token, realm_id = ensure_fresh_token(tool_context)
    url = _build_url(realm_id, endpoint)
    params = {"minorversion": MINOR_VERSION}
    headers = _auth_headers(access_token)
    headers["Content-Type"] = "application/json"

    resp = requests.post(url, headers=headers, params=params, json=payload, timeout=30)

    if resp.status_code == 401:
        tool_context.state["qbo_access_token"] = None
        access_token, realm_id = ensure_fresh_token(tool_context)
        headers = _auth_headers(access_token)
        headers["Content-Type"] = "application/json"
        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=30)

    resp.raise_for_status()
    return resp.json()


def _qbo_query(tool_context, sql: str) -> list:
    """Execute a QBOQL query via POST, return the entity list."""
    access_token, realm_id = ensure_fresh_token(tool_context)
    url = _build_url(realm_id, "query")
    params = {"minorversion": MINOR_VERSION}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/text",
    }

    resp = requests.post(url, headers=headers, params=params, data=sql, timeout=30)

    if resp.status_code == 401:
        tool_context.state["qbo_access_token"] = None
        access_token, realm_id = ensure_fresh_token(tool_context)
        headers["Authorization"] = f"Bearer {access_token}"
        resp = requests.post(url, headers=headers, params=params, data=sql, timeout=30)

    resp.raise_for_status()
    data = resp.json()

    qr = data.get("QueryResponse", {})
    # The entity list key varies — find the first list value
    for v in qr.values():
        if isinstance(v, list):
            return v
    return []


def format_currency(amount) -> str:
    """Format a number as $1,234.56."""
    try:
        return f"${float(amount):,.2f}"
    except (TypeError, ValueError):
        return str(amount)


def format_error(e: Exception) -> dict:
    """Standard error dict for tool returns."""
    return {"status": "error", "message": str(e)}
