import streamlit as st


def set_theme(title):
    st.set_page_config(
        page_title=title,
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Light, clean styling
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.3rem; padding-bottom: 3rem; }
        .stApp { background: #0b1020; }
        h1, h2, h3, p, li, label, div { color: #e9ecf1; }
        .card {
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.10);
          border-radius: 18px;
          padding: 16px 16px;
        }
        .muted { color: rgba(233,236,241,0.70); }
        .good { color: #69f0ae; font-weight: 700; }
        .bad { color: #ff6b6b; font-weight: 700; }
        .pill {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.12);
          background: rgba(255,255,255,0.06);
          font-size: 12px;
          color: rgba(233,236,241,0.85);
          margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(title, body_md):
    st.markdown(
        '<div class="card"><div style="font-size:16px;font-weight:700;margin-bottom:6px;">'
        + title
        + '</div><div class="muted">'
        + body_md
        + "</div></div>",
        unsafe_allow_html=True,
    )


def status_pill(ok, label_ok="OK", label_bad="Down"):
    if ok:
        st.markdown('<span class="pill good">✅ ' + label_ok + "</span>", unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill bad">⛔ ' + label_bad + "</span>", unsafe_allow_html=True)