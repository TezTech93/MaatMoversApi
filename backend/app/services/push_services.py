"""Expo push delivery via the public HTTP Push API.

Uses https://exp.host/--/api/v2/push/send — no SDK dependency required.
"""
from typing import Iterable, Optional

import requests


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push(
    tokens: Iterable[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> dict:
    """Send a push notification to each valid Expo push token. Never raises."""
    tokens = list(tokens or [])
    valid = [t for t in tokens if t and t.startswith("ExponentPushToken")]
    if not valid:
        print(f"[push] no valid tokens (input={len(tokens)})")
        return {"sent": 0, "reason": "no valid tokens"}

    messages = [
        {
            "to": t,
            "title": title,
            "body": body,
            "data": data or {},
            "sound": "default",
        }
        for t in valid
    ]

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        payload = resp.json() if resp.ok else {}
        data_arr = payload.get("data") or []
        errors = [d for d in data_arr if isinstance(d, dict) and d.get("status") == "error"]
        print(f"[push] sent={len(valid)} status={resp.status_code} errors={len(errors)}")
        for e in errors[:3]:
            print(f"[push] error detail: {e.get('message', e)}")
        return {"sent": len(valid), "status_code": resp.status_code, "errors": errors}
    except Exception as e:
        print(f"[push] error: {e}")
        return {"sent": 0, "reason": str(e)}