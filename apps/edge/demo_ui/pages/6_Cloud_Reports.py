import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json
from infra.ui import set_theme
from infra.auth import require_login, sidebar_identity_box

s = get_settings()
set_theme(s["APP_TITLE"])

require_login(s)
sidebar_identity_box()

st.title("📈 Cloud Reports")

cloud = s["CLOUD_URL"]

tab1, tab2, tab3 = st.tabs(["Recent orders", "Daily sales", "Product sales"])

with tab1:
    st.subheader("Recent orders")
    limit = st.number_input("Limit", min_value=1, max_value=200, value=20, step=1, key="recent_limit")

    if st.button("Load recent orders"):
        ok, code, data = get_json(cloud, "/reports/orders/recent?limit=" + str(int(limit)))
        if ok:
            st.json(data)
        else:
            st.error("Failed (" + str(code) + ")")
            st.json(data)

with tab2:
    st.subheader("Daily sales totals")
    days = st.number_input("Days", min_value=1, max_value=365, value=7, step=1, key="days")

    if st.button("Load daily sales"):
        ok2, code2, data2 = get_json(cloud, "/reports/sales/daily?days=" + str(int(days)))
        if ok2:
            st.json(data2)

            # Optional small chart
            days_list = data2.get("days", [])
            if days_list is None:
                days_list = []

            chart_rows = []
            i = 0
            while i < len(days_list):
                row = days_list[i]
                chart_rows.append(
                    {
                        "day": row.get("day", ""),
                        "total_cents": int(row.get("total_cents", 0)),
                    }
                )
                i = i + 1

            if len(chart_rows) > 0:
                st.line_chart(chart_rows, x="day", y="total_cents")
        else:
            st.error("Failed (" + str(code2) + ")")
            st.json(data2)

with tab3:
    st.subheader("Top products")
    limit3 = st.number_input("Limit", min_value=1, max_value=200, value=10, step=1, key="prod_limit")

    if st.button("Load product sales"):
        ok3, code3, data3 = get_json(cloud, "/reports/sales/products?limit=" + str(int(limit3)))
        if ok3:
            st.json(data3)
        else:
            st.error("Failed (" + str(code3) + ")")
            st.json(data3)