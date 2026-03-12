import secrets
import streamlit as st

from infra.settings import get_settings
from infra.http_client import (
    post_json_with_headers,
    post_no_body_with_headers,
)
from infra.ui import set_theme, card
from infra.auth import require_admin, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_admin(s)
sidebar_identity_box()

st.title("🔐 Admin (Cloud) — Devices")

cloud = s["CLOUD_URL"]
admin_key = s.get("CLOUD_ADMIN_API_KEY", "")

if admin_key.strip() == "":
    st.warning("CLOUD_ADMIN_API_KEY is not set in apps/demo_ui/.env. Admin actions will fail with 401.")

headers = {"X-Admin-Key": admin_key}

st.caption("Manage per-device keys, rotation, and revocation on the Cloud server.")

tabs = st.tabs(["Upsert device", "Rotate key", "Promote key", "Revoke/Enable", "Help"])

# ------------------ Upsert ------------------
with tabs[0]:
    st.subheader("Create / Update Device")

    with st.form("upsert_device"):
        device_id = st.text_input("Device ID", value="edge-001")
        api_key_current = st.text_input("Current API key", value="", type="password")
        is_active = st.checkbox("Active", value=True)

        gen = st.form_submit_button("Generate random key")
        if gen:
            st.session_state["generated_key"] = secrets.token_urlsafe(32)

        if st.session_state.get("generated_key") is not None and st.session_state["generated_key"] != "":
            st.code(st.session_state["generated_key"])
            st.info("Paste this into Current API key and save. Also update Edge .env POS_CLOUD_API_KEY.")

        save = st.form_submit_button("Upsert device")

    if save:
        payload = {
            "device_id": device_id.strip(),
            "api_key_current": api_key_current.strip(),
            "is_active": bool(is_active),
        }
        ok, code, data = post_json_with_headers(cloud, "/admin/devices/upsert", payload, headers)
        if ok:
            st.success("Device upserted.")
            st.json(data)
            card("Next", "Go to <b>Rotate key</b> to start rotation, or <b>Revoke/Enable</b> to disable a device.")
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

# ------------------ Rotate ------------------
with tabs[1]:
    st.subheader("Rotate Device Key (zero downtime)")

    with st.form("rotate_device"):
        device_id_r = st.text_input("Device ID", value="edge-001", key="device_id_r")
        api_key_next = st.text_input("Next API key", value="", type="password", key="api_key_next")

        col1, col2 = st.columns(2)
        with col1:
            next_valid_in_minutes = st.number_input("Next key valid in (minutes)", min_value=0, max_value=1440, value=0, step=1)
        with col2:
            expire_current_in_minutes = st.number_input("Expire current key in (minutes, optional)", min_value=0, max_value=1440, value=60, step=1)

        gen2 = st.form_submit_button("Generate random next key")
        if gen2:
            st.session_state["generated_next"] = secrets.token_urlsafe(32)

        if st.session_state.get("generated_next") is not None and st.session_state["generated_next"] != "":
            st.code(st.session_state["generated_next"])
            st.info("Paste this into Next API key and rotate. Then update Edge to use it before promoting.")

        rotate = st.form_submit_button("Rotate now")

    if rotate:
        payload = {
            "api_key_next": api_key_next.strip(),
            "next_valid_in_minutes": int(next_valid_in_minutes),
            "expire_current_in_minutes": int(expire_current_in_minutes),
        }
        path = "/admin/devices/" + device_id_r.strip() + "/rotate"
        ok, code, data = post_json_with_headers(cloud, path, payload, headers)
        if ok:
            st.success("Rotation scheduled.")
            st.json(data)
            card(
                "Recommended flow",
                "1) Set next key<br/>2) Update Edge to next key<br/>3) Verify sync works<br/>4) Promote next → current",
            )
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

# ------------------ Promote ------------------
with tabs[2]:
    st.subheader("Promote next key → current")

    device_id_p = st.text_input("Device ID", value="edge-001", key="device_id_p")

    if st.button("Promote now", type="primary"):
        path = "/admin/devices/" + device_id_p.strip() + "/promote"
        ok, code, data = post_no_body_with_headers(cloud, path, headers)
        if ok:
            st.success("Promoted.")
            st.json(data)
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

# ------------------ Revoke/Enable ------------------
with tabs[3]:
    st.subheader("Revoke (disable) or enable a device")

    with st.form("revoke_enable"):
        device_id_e = st.text_input("Device ID", value="edge-001", key="device_id_e")
        new_key = st.text_input("API key (required for upsert)", value="", type="password", key="new_key_e")

        c1, c2 = st.columns(2)
        with c1:
            disable = st.form_submit_button("Disable device")
        with c2:
            enable = st.form_submit_button("Enable device")

    if disable or enable:
        payload = {
            "device_id": device_id_e.strip(),
            "api_key_current": new_key.strip(),
            "is_active": False if disable else True,
        }
        ok, code, data = post_json_with_headers(cloud, "/admin/devices/upsert", payload, headers)
        if ok:
            st.success("Updated.")
            st.json(data)
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

# ------------------ Help ------------------
with tabs[4]:
    st.subheader("How to use this safely")
    st.write(
        "- **Upsert device**: create device and set its current key.\n"
        "- **Rotate key**: set next key and allow overlap for smooth transition.\n"
        "- **Promote**: once Edge is using next key and sync works, promote it.\n"
        "- **Revoke**: disable a device if stolen or compromised.\n"
    )
    st.write("Where Edge config lives:")
    st.code("pos/apps/edge/app/.env\nPOS_DEVICE_ID=\nPOS_CLOUD_API_KEY=")