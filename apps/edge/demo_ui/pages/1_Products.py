import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json, post_json
from infra.ui import set_theme, card
from infra.auth import require_login, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_login(s)
sidebar_identity_box()

st.title("📦 Products")

edge = s["EDGE_URL"]

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Create / Update Product")
    with st.form("product_upsert", clear_on_submit=False):
        barcode = st.text_input("Barcode", value="123456")
        name = st.text_input("Name", value="Tea")
        price_cents = st.number_input("Price (cents)", min_value=0, value=250, step=1)
        currency = st.text_input("Currency (3 letters)", value="PKR")
        is_active = st.checkbox("Active", value=True)
        submitted = st.form_submit_button("Save")

    if submitted:
        payload = {
            "barcode": barcode.strip(),
            "name": name.strip(),
            "price_cents": int(price_cents),
            "currency": currency.strip(),
            "is_active": bool(is_active),
        }
        ok, code, data = post_json(edge, "/products", payload)
        if ok:
            st.success("Saved.")
            st.json(data)
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

with col_right:
    st.subheader("Search by Barcode")
    search_barcode = st.text_input("Barcode to search", value="123456", key="search_barcode")

    if st.button("Search"):
        ok, code, data = get_json(edge, "/products/" + search_barcode.strip())
        if ok:
            card("Product found", "<span class='pill'>barcode</span> <b>" + str(data.get("barcode", "")) + "</b>")
            st.json(data)
        else:
            st.warning("Not found / error (" + str(code) + ")")
            st.json(data)

st.divider()
st.caption("Tip: create a product here, then go to Cart → add by barcode.")