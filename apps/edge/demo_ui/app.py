import streamlit as st

from infra.settings import get_settings
from infra.http_client import get_json
from infra.ui import set_theme, card, status_pill
from infra.auth import require_login, sidebar_identity_box


def _check_service(name, base_url):
    ok1, code1, j1 = get_json(base_url, "/health")
    ok2, code2, j2 = get_json(base_url, "/health/db")

    return {
        "name": name,
        "base_url": base_url,
        "ok_api": ok1,
        "ok_db": ok2,
        "code_api": code1,
        "code_db": code2,
        "json_api": j1,
        "json_db": j2,
    }


def main():
    s = get_settings()
    set_theme(s["APP_TITLE"])
    require_login(s)
    sidebar_identity_box()

    st.title("🧾 " + s["APP_TITLE"])
    st.write("Explore the full offline-first POS flow: Products → Cart → Checkout → Local Events → Sync → Cloud Reports.")

    col1, col2 = st.columns(2)

    with col1:
        edge = _check_service("Edge", s["EDGE_URL"])
        st.subheader("Edge Service")
        status_pill(edge["ok_api"], "API OK", "API Down")
        status_pill(edge["ok_db"], "DB OK", "DB Down")
        card(
            "Edge URL",
            "<div><code>" + edge["base_url"] + "</code></div>",
        )
        with st.expander("Edge details"):
            st.write(edge)

    with col2:
        cloud = _check_service("Cloud", s["CLOUD_URL"])
        st.subheader("Cloud Service")
        status_pill(cloud["ok_api"], "API OK", "API Down")
        status_pill(cloud["ok_db"], "DB OK", "DB Down")
        card(
            "Cloud URL",
            "<div><code>" + cloud["base_url"] + "</code></div>",
        )
        with st.expander("Cloud details"):
            st.write(cloud)

    st.divider()
    st.subheader("Flow Quickstart")
    st.write(
        "- Go to **Products** → create a product\n"
        "- Go to **Cart** → create cart, add items\n"
        "- Go to **Checkout** → checkout cart\n"
        "- Go to **Local Events** → dispatch local events (inventory)\n"
        "- Go to **Sync** → push to cloud\n"
        "- Go to **Cloud Reports** → view orders and sales\n"
    )


if __name__ == "__main__":
    main()