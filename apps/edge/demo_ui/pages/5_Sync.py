import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json, post_no_body
from infra.ui import set_theme, card
from infra.auth import require_login, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_login(s)
sidebar_identity_box()

st.title("🔁 Sync")

edge = s["EDGE_URL"]

st.subheader("Sync status")

if st.button("Refresh status"):
    ok, code, data = get_json(edge, "/sync/status")
    if ok:
        st.json(data)
    else:
        st.error("Failed (" + str(code) + ")")
        st.json(data)

st.divider()

st.subheader("Push to Cloud")
limit = st.number_input("Push limit", min_value=1, max_value=500, value=50, step=1)

if st.button("Push now", type="primary"):
    ok2, code2, data2 = post_no_body(edge, "/sync/push?limit=" + str(int(limit)))
    if ok2:
        st.success("Push complete.")
        st.json(data2)
        card("Tip", "Go to <b>Cloud Reports</b> to verify orders landed in Cloud.")
    else:
        st.error("Push failed (" + str(code2) + ")")
        st.json(data2)