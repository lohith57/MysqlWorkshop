import streamlit as st
import pandas as pd

# ------------------------------------------------
# BACKEND IMPORTS
# ------------------------------------------------
from db_metadata import (
    USER_DB_MAPPING,
    get_accessible_databases,
    get_accessible_tables
)

from NLSQL_V2 import (
    rewrite_question,
    run_nl_sql,
    generate_conversational_answer,
    generate_session_id,
    insert_chat_history,
    get_chat_sessions,          # 👈 NEW
    get_chat_by_session         # 👈 NEW
)

# ------------------------------------------------
# 1. PAGE SETUP
# ------------------------------------------------
st.set_page_config(
    page_title="HeatWave Intelligence Hub",
    page_icon="🔥",
    layout="wide"
)

st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# 2. SESSION STATE
# ------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "session_id" not in st.session_state or st.session_state.session_id is None:
    st.session_state.session_id = generate_session_id()

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None


# ------------------------------------------------
# 3. REGION: USER AUTH & GLOBAL CONFIG
# ------------------------------------------------
st.title("🔥 HeatWave Intelligence Hub")
st.markdown("### Region 1: Identity & Access Control")

with st.container():
    col1, col2 = st.columns(2)

    with col1:
        app_user = st.selectbox(
            "👤 Select User Profile:",
            list(USER_DB_MAPPING.keys())
        )
        st.session_state.app_user = app_user  # 👈 save for sidebar

    try:
        databases = get_accessible_databases(app_user)
    except Exception as e:
        st.error(f"RBAC Error: {e}")
        st.stop()

    with col2:
        selected_db = st.selectbox(
            "📂 Target Database:",
            databases if databases else ["Access Denied"]
        )

st.divider()

# ------------------------------------------------
# 4. SIDEBAR – CHATGPT STYLE HISTORY
# ------------------------------------------------
with st.sidebar:
    st.markdown("## 💬 Conversations")

    app_user_for_sidebar = st.session_state.get("app_user")

    if app_user_for_sidebar:
        sessions = get_chat_sessions(app_user)

        if not sessions:
            st.caption("No previous chats")
        else:
            for s in sessions:
                label = f"🗂️ {s['question'][:60]}"
                if s["message_count"] > 1:
                    label += f" ({s['message_count']})"

                if st.button(label, key=f"session_{s['session_id']}"):
                    st.session_state.active_session_id = s["session_id"]
                    st.session_state.session_id = s["session_id"]

                    # Load DB history into UI memory
                    rows = get_chat_by_session(s["session_id"])
                    st.session_state.chat_history = [
                        {"question": r["user_question"], "answer": r["answer"]}
                        for r in rows
                    ]
                    st.rerun()

    st.divider()

    if st.button("➕ New Chat"):
        st.session_state.chat_history = []
        st.session_state.session_id = generate_session_id()
        st.session_state.active_session_id = None
        st.rerun()
# ------------------------------------------------
# 5. REGION: DB OBJECT EXPLORER
# ------------------------------------------------
st.markdown("### Region 2: Database Object Explorer")

with st.expander("🔍 View Accessible Tables", expanded=True):
    try:
        tables = get_accessible_tables(app_user)
        if tables:
            grid = st.columns(4)
            for i, t in enumerate(tables):
                grid[i % 4].code(t)
        else:
            st.info("No tables visible.")
    except Exception as e:
        st.error(e)

st.divider()

# ------------------------------------------------
# 6. REGION: CHAT ASSISTANT
# ------------------------------------------------
st.markdown("### Region 3: Natural Language Assistant")

question = st.text_input(
    "Ask a data-related question:",
    placeholder="e.g. Which department is in CHICAGO?"
)

btn_col1, btn_col2, _ = st.columns([1, 1, 4])

with btn_col1:
    run_query = st.button("🚀 Run Query", type="primary")

with btn_col2:
    if st.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.session_state.session_id = None
        st.session_state.active_session_id = None
        st.rerun()

# ------------------------------------------------
# 7. QUERY EXECUTION
# ------------------------------------------------
if run_query and question.strip():
    try:
        with st.spinner("🧠 Resolving context..."):
            rewritten_text = rewrite_question(
                question,
                st.session_state.chat_history,
                app_user
            )

        with st.spinner("⚙️ HeatWave generating SQL..."):
            sql_query, df = run_nl_sql(rewritten_text, app_user, selected_db)

        with st.spinner("✍️ Summarizing results..."):
            answer = generate_conversational_answer(
                rewritten_text,
                df,
                app_user
            )

        with st.expander("🛠️ Query Execution Details"):
            st.write(f"**Interpreted as:** {rewritten_text}")
            if sql_query:
                st.code(sql_query, language="sql")

        if isinstance(df, pd.DataFrame) and not df.empty:
            st.dataframe(df, width="stretch")
        else:
            st.info("No rows returned.")

        st.success(answer)

        # Store in memory
        st.session_state.chat_history.append({
            "question": question,
            "answer": answer
        })

        # Store in DB
        insert_chat_history(
            session_id=st.session_state.session_id,
            user_question=question,
            generated_sql=sql_query,
            answer=answer,
            app_user=app_user
        )

    except Exception as e:
        st.error(f"Application Error: {e}")

# ------------------------------------------------
# 8. CHAT RENDER (ChatGPT style bubbles)
# ------------------------------------------------
if st.session_state.chat_history:
    st.divider()
    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.write(turn["answer"])
