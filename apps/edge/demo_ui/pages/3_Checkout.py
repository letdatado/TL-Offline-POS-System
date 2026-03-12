import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json, post_no_body
from infra.ui import set_theme, card
from infra.auth import require_login, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_login(s)
sidebar_identity_box()

st.title("✅ Checkout")

edge = s["EDGE_URL"]

active_cart = st.session_state.get("active_cart_id", "").strip()

st.subheader("Selected cart")
st.code(active_cart if active_cart != "" else "(none)")

manual_cart = st.text_input("Cart ID (optional override)", value=active_cart)
use_cart = manual_cart.strip()

if use_cart == "":
    st.info("Go to Cart page to create/select a cart.")
else:
    ok, code, data = get_json(edge, "/carts/" + use_cart)
    if ok:
        st.write("Cart preview:")
        st.json(data.get("totals", {}))
    else:
        st.warning("Could not load cart (" + str(code) + ").")
        st.json(data)

    st.divider()

    if st.button("Checkout cart", type="primary"):
        ok2, code2, data2 = post_no_body(edge, "/carts/" + use_cart + "/checkout")
        if ok2:
            st.success("Checkout complete.")
            order = data2.get("order", {})
            outbox = data2.get("outbox", {})
            st.subheader("Order")
            st.json(order)

            st.subheader("Outbox event (created atomically)")
            st.json(outbox)

            st.subheader("Lines")
            st.json(data2.get("lines", []))

            card("Next steps", "Go to <b>Local Events</b> to dispatch modules, then <b>Sync</b> to push to Cloud.")
        else:
            st.error("Checkout failed (" + str(code2) + ")")
            st.json(data2)