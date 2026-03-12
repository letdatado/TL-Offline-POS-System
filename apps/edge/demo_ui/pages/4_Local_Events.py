import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json, post_no_body
from infra.ui import set_theme
from infra.auth import require_login, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_login(s)
sidebar_identity_box()

st.title("⚙️ Local Events")

edge = s["EDGE_URL"]

st.subheader("Dispatch local outbox events")
limit = st.number_input("Dispatch limit", min_value=1, max_value=500, value=25, step=1)

if st.button("Dispatch now", type="primary"):
    ok, code, data = post_no_body(edge, "/outbox/dispatch?limit=" + str(int(limit)))
    if ok:
        st.success("Dispatched.")
        st.json(data)
    else:
        st.error("Dispatch failed (" + str(code) + ")")
        st.json(data)

st.divider()

st.subheader("Module events log")
limit2 = st.number_input("Show recent module events", min_value=1, max_value=500, value=50, step=1)

if st.button("Refresh module events"):
    ok2, code2, data2 = get_json(edge, "/module-events/recent?limit=" + str(int(limit2)))
    if ok2:
        st.json(data2)
    else:
        st.error("Failed (" + str(code2) + ")")
        st.json(data2)