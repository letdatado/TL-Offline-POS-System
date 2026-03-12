import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json, post_json, post_no_body
from infra.ui import set_theme, card
from infra.auth import require_login, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_login(s)
sidebar_identity_box()

st.title("🛒 Cart")

edge = s["EDGE_URL"]

if st.session_state.get("active_cart_id") is None:
    st.session_state["active_cart_id"] = ""

top_left, top_right = st.columns([1, 2])

with top_left:
    st.subheader("Active cart")
    st.write("Cart ID:")
    st.code(st.session_state["active_cart_id"] if st.session_state["active_cart_id"] != "" else "(none)")

    if st.button("Create new cart"):
        ok, code, data = post_no_body(edge, "/carts")
        if ok:
            st.session_state["active_cart_id"] = str(data.get("id", ""))
            st.success("Cart created.")
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

    manual_cart = st.text_input("Or paste existing Cart ID", value=st.session_state["active_cart_id"])
    if st.button("Set active cart"):
        st.session_state["active_cart_id"] = manual_cart.strip()

with top_right:
    st.subheader("Add / Remove items by barcode")

    cart_id = st.session_state["active_cart_id"].strip()
    if cart_id == "":
        st.info("Create or set an active cart first.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            with st.form("add_item"):
                add_barcode = st.text_input("Barcode", value="123456", key="add_barcode")
                add_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="add_qty")
                add_submit = st.form_submit_button("Add / Increase")

            if add_submit:
                payload = {"barcode": add_barcode.strip(), "qty": int(add_qty)}
                ok, code, data = post_json(edge, "/carts/" + cart_id + "/items", payload)
                if ok:
                    st.success("Added.")
                    st.json(data)
                else:
                    st.error("Failed (" + str(code) + ")")
                    st.json(data)

        with c2:
            with st.form("remove_item"):
                rem_barcode = st.text_input("Barcode", value="123456", key="rem_barcode")
                rem_qty = st.number_input("Qty", min_value=1, value=1, step=1, key="rem_qty")
                rem_submit = st.form_submit_button("Remove / Decrease")

            if rem_submit:
                payload = {"barcode": rem_barcode.strip(), "qty": int(rem_qty)}
                ok, code, data = post_json(edge, "/carts/" + cart_id + "/items/remove", payload)
                if ok:
                    st.success("Removed / updated.")
                    st.json(data)
                else:
                    st.error("Failed (" + str(code) + ")")
                    st.json(data)

st.divider()
st.subheader("Cart view (items + totals)")

cart_id = st.session_state["active_cart_id"].strip()
if cart_id == "":
    st.info("No active cart.")
else:
    ok, code, data = get_json(edge, "/carts/" + cart_id)
    if ok:
        totals = data.get("totals", {})
        items = data.get("items", [])

        a, b, c = st.columns(3)
        a.metric("Subtotal (cents)", int(totals.get("subtotal_cents", 0)))
        b.metric("Tax (cents)", int(totals.get("tax_cents", 0)))
        c.metric("Total (cents)", int(totals.get("total_cents", 0)))

        if items is None or len(items) == 0:
            card("Empty cart", "Add items using barcode above.")
        else:
            # Display a simple table
            rows = []
            i = 0
            while i < len(items):
                it = items[i]
                rows.append(
                    {
                        "barcode": it.get("barcode", ""),
                        "name": it.get("name", ""),
                        "qty": it.get("qty", 0),
                        "unit_price_cents": it.get("unit_price_cents", 0),
                        "line_total_cents": it.get("line_total_cents", 0),
                    }
                )
                i = i + 1
            st.dataframe(rows, use_container_width=True, hide_index=True)

    else:
        st.error("Failed (" + str(code) + ")")
        st.json(data)

st.caption("Tip: go to Checkout page once totals look right.")