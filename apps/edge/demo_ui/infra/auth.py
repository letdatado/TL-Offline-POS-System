import streamlit as st


def _ensure_state():
    if st.session_state.get("auth") is None:
        st.session_state["auth"] = {
            "is_authenticated": False,
            "username": "",
            "role": "",  # "admin" or "viewer"
        }


def logout():
    _ensure_state()
    st.session_state["auth"] = {
        "is_authenticated": False,
        "username": "",
        "role": "",
    }


def login_form(settings):
    """
    Renders a login form and updates session state on success.
    Returns True if authenticated.
    """
    _ensure_state()

    if settings.get("UI_AUTH_ENABLED") is False:
        # auth disabled
        st.session_state["auth"]["is_authenticated"] = True
        st.session_state["auth"]["username"] = "guest"
        st.session_state["auth"]["role"] = "admin"
        return True

    auth = st.session_state["auth"]
    if auth.get("is_authenticated") is True:
        return True

    st.title("🔐 Login")
    st.write("Enter your credentials to access the POS demo UI.")

    with st.form("login_form"):
        username = st.text_input("Username", value="", placeholder="admin or viewer")
        password = st.text_input("Password", value="", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        admin_u = settings.get("UI_ADMIN_USERNAME", "admin")
        admin_p = settings.get("UI_ADMIN_PASSWORD", "")
        viewer_u = settings.get("UI_VIEWER_USERNAME", "viewer")
        viewer_p = settings.get("UI_VIEWER_PASSWORD", "")

        u = username.strip()
        p = password.strip()

        if u == admin_u and p == admin_p and p != "":
            st.session_state["auth"] = {
                "is_authenticated": True,
                "username": u,
                "role": "admin",
            }
            st.success("Signed in as admin.")
            st.rerun()

        elif u == viewer_u and p == viewer_p and p != "":
            st.session_state["auth"] = {
                "is_authenticated": True,
                "username": u,
                "role": "viewer",
            }
            st.success("Signed in as viewer.")
            st.rerun()

        else:
            st.error("Invalid username/password.")

    return False


def require_login(settings):
    """
    Enforce authentication before rendering the page.
    If not authenticated, renders login and stops the page.
    """
    ok = login_form(settings)
    if not ok:
        st.stop()


def require_admin(settings):
    """
    Enforce admin role on a page.
    """
    require_login(settings)
    _ensure_state()

    role = st.session_state["auth"].get("role", "")
    if role != "admin":
        st.error("Admin access required.")
        st.info("Please sign in with an admin account to use this page.")
        st.stop()


def sidebar_identity_box():
    _ensure_state()
    auth = st.session_state["auth"]

    if auth.get("is_authenticated") is True:
        st.sidebar.markdown("### 👤 Session")
        st.sidebar.write("User: **" + str(auth.get("username", "")) + "**")
        st.sidebar.write("Role: **" + str(auth.get("role", "")) + "**")
        if st.sidebar.button("Log out"):
            logout()
            st.rerun()