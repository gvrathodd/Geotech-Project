"""Optional sign-in (Google, via Streamlit's st.login) and per-user project storage (Firestore).

Guest mode is always available: without an [auth] section in secrets.toml the app simply
hides saving.  Firestore layout: users/{email}/projects/{project_id}.
"""
from __future__ import annotations

import datetime as _dt
import json
import re

import streamlit as st


def auth_configured() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:  # no secrets.toml at all
        return False


def user_email() -> str | None:
    try:
        return st.user.email if st.user.is_logged_in else None
    except Exception:
        return None


@st.cache_resource
def _db():
    from google.cloud import firestore  # imported lazily: only needed when signed in
    return firestore.Client()


def _projects(email: str):
    return _db().collection("users").document(email).collection("projects")


def _pid(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "untitled"


def list_projects(email: str) -> list[dict]:
    rows = []
    for d in _projects(email).stream():
        v = d.to_dict()
        rows.append({"id": d.id, "name": v.get("name", d.id), "updated": v.get("updated", "")})
    return sorted(rows, key=lambda r: r["updated"], reverse=True)


def save_project(email: str, name: str, data: dict) -> str:
    pid = _pid(name)
    _projects(email).document(pid).set({
        "name": name,
        "updated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "data": json.dumps(data),  # stored as text: nested lists of layers/SPT records
    })
    return pid


def load_project(email: str, pid: str) -> dict | None:
    snap = _projects(email).document(pid).get()
    return json.loads(snap.to_dict()["data"]) if snap.exists else None


def delete_project(email: str, pid: str) -> None:
    _projects(email).document(pid).delete()
