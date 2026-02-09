import streamlit as st
import pandas as pd

# Import from your existing backend files
from db_metadata import (
    USER_DB_MAPPING,
    get_accessible_databases,
    get_accessible_tables
)

from NLSQL_V2 import (
    rewrite_question,
    run_nl_sql,
    generate_conversational_answer
)

# ------------------------------------------------
# 1. PAGE SETUP
# ------------------------------------------------
st.set_page_config(
    page_title="HeatWave Intelligence Hub",
    page_icon="🔥",
    layout="wide"
)

# Custom styling for a modern look
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .stAlert { border-radius: 8px; }
    .region-box { 
        padding: 20px; 
        border-radius: 10px; 
        background-color: #f0f2f6; 
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------
# 2. SESSION STATE
# ------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ------------------------------------------------
# 3. REGION: USER AUTHENTICATION & GLOBAL CONFIG
# ------------------------------------------------
st.title("🔥 HeatWave Intelligence Hub")
st.markdown("### Region 1: Identity & Access Control")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        app_user = st.selectbox(
            "👤 Select User Profile:",
            list(USER_DB_MAPPING.keys()),
            help="Simulates RBAC based on app user identity."
        )
    
    # Fetch databases based on user
    try:
        databases = get_accessible_databases(app_user)
    except Exception as e:
        st.error(f"RBAC Error: {e}")
        st.stop()

    with col2:
        selected_db = st.selectbox(
            "📂 Target Database:",
            databases if databases else ["Access Denied"],
            index=0
        )

st.divider()

# ------------------------------------------------
# 4. REGION: RBAC EXPLORER
# ------------------------------------------------
st.markdown("### Region 2: Database Object Explorer")

with st.expander("🔍 View Accessible Tables", expanded=True):
    if not databases:
        st.warning("No database access found for this user profile.")
    else:
        try:
            # Note: Assuming get_accessible_tables uses app_user context
            tables = get_accessible_tables(app_user)
            if tables:
                st.write(f"The following tables in **{selected_db}** are available to **{app_user}**:")
                # Display tables in a clean 4-column grid
                grid = st.columns(4)
                for idx, table in enumerate(tables):
                    grid[idx % 4].code(f"📋 {table}", language="text")
            else:
                st.info("No tables visible in this database.")
        except Exception as e:
            st.error(f"Explorer Error: {e}")

st.divider()

# ------------------------------------------------
# 5. REGION: NL-SQL CHAT ASSISTANT (WITH CONTEXT)
# ------------------------------------------------
st.markdown("### Region 3: Natural Language Assistant")

# Chat Container
chat_container = st.container()

with chat_container:
    # Input field
    question = st.text_input(
        "Ask a data-related question:",
        placeholder="e.g. Which department is in CHICAGO?",
        key="main_input"
    )

    btn_col1, btn_col2, _ = st.columns([1, 1, 4])
    with btn_col1:
        run_query = st.button("🚀 Run Query", type="primary")
    with btn_col2:
        if st.button("🧹 Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

    if run_query:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                # A. REWRITE: This is where we fix "how many work here?"
                with st.spinner("🧠 Resolving context..."):
                    rewritten_text = rewrite_question(
                        question=question,
                        history=st.session_state.chat_history,
                        app_username=app_user
                    )
                
                # B. EXECUTE: NL to SQL
                with st.spinner("⚙️ HeatWave generating SQL..."):
                    sql_query, df = run_nl_sql(rewritten_text, app_user, selected_db)

                # C. CONVERSE: Summary
                with st.spinner("✍️ Summarizing results..."):
                    answer = generate_conversational_answer(rewritten_text, df, app_user)

                # --- DISPLAY RESULTS ---
                
                # 1. The rewritten logic (Technical Detail)
                with st.expander("🛠️ Query Execution Details"):
                    st.write(f"**Interpreted as:** {rewritten_text}")
                    if sql_query:
                        st.code(sql_query, language="sql")

                # 2. The Result Table
                if isinstance(df, pd.DataFrame) and not df.empty:
                    st.markdown("#### 📊 Result Set")
                    st.dataframe(df, width="stretch")
                else:
                    st.info("No rows returned from the database.")

                # 3. The Friendly Answer
                st.markdown("#### 🗣️ Assistant Response")
                st.success(answer)

                # D. STORE HISTORY
                st.session_state.chat_history.append({
                    "question": question,
                    "canonical_question": rewritten_text,
                    "answer": answer
                })
                # Maintain memory limit
                if len(st.session_state.chat_history) > 5:
                    st.session_state.chat_history.pop(0)

            except Exception as e:
                st.error(f"Application Error: {str(e)}")

# ------------------------------------------------
# 6. REGION: HISTORY LOG
# ------------------------------------------------
if st.session_state.chat_history:
    st.divider()
    st.markdown("### 📜 Recent Conversation History")
    for i, turn in enumerate(reversed(st.session_state.chat_history)):
        with st.chat_message("user"):
            st.write(turn['question'])
        with st.chat_message("assistant"):
            st.write(turn['answer'])