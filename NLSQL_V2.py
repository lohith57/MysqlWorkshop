import pandas as pd
import mysql.connector
import json
from typing import List, Dict

# ------------------------------------------------
# DB CONNECTION BASE
# ------------------------------------------------
DB_BASE = {
    "host": "10.0.1.110",
    "port": 3306
}

# ------------------------------------------------
# APP USER → DB USER MAPPING
# ------------------------------------------------
USER_DB_MAPPING = {
    "ora_userA": {
        "user": "userA",
        "password": "App#Pass123!"
    },
    "ora_userB": {
        "user": "userC",
        "password": "App#Pass123!"
    }
}

def get_db_config(app_username: str):
    if app_username not in USER_DB_MAPPING:
        raise ValueError("Unauthorized user")

    return {
        **DB_BASE,
        "user": USER_DB_MAPPING[app_username]["user"],
        "password": USER_DB_MAPPING[app_username]["password"]
    }

# ============================================================
# 1️⃣ CONTEXTUAL QUESTION REWRITER (UPDATED)
# ============================================================
def rewrite_question(question: str, history: List[dict], app_username: str) -> str:
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**get_db_config(app_username))
        cursor = conn.cursor()

        history_text = ""
        for turn in history[-3:]:
            history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n"

        # REFINED PROMPT: Focus on preserving "How many" vs "What"
        prompt = f"""
You are a CONTEXTUAL QUESTION REWRITER for a Natural Language → SQL system.

Conversation history (for context only):
{history_text}

Current user question:
"{question}"

Your task:
Rewrite the current user question into a SINGLE, standalone, clear NATURAL-LANGUAGE question that can be understood without the conversation history.

STRICT RULES (VIOLATION = WRONG ANSWER):
1. OUTPUT MUST BE PLAIN ENGLISH ONLY.
2. DO NOT OUTPUT SQL.
3. DO NOT use or mention table names, column names, schemas, or database objects.
4. DO NOT use SQL keywords such as SELECT, FROM, WHERE, JOIN, GROUP BY, HAVING, ORDER BY, COUNT, SUM, etc.
5. DO NOT format the output as code or markdown.
6. Output exactly ONE sentence.

INTENT PRESERVATION RULES:
7. If the user asks “How many”, “Number of”, or “Count”, the rewritten question MUST ask for a count or total.
8. If the user asks “Which”, “What”, or “List”, the rewritten question MUST ask for specific items or details.
9. Preserve all filters such as locations, names, time ranges, and durations exactly as stated.
10. Resolve references like “here”, “there”, “them”, “those”, or “delayed” using the conversation history.

CONTEXT RULES:
11. Use conversation history ONLY to resolve ambiguity — do NOT introduce new assumptions.
12. Do NOT infer database schema or guess column meanings.
13. If the current question is already standalone and clear, return it unchanged.

FAIL-SAFE:
14. If you are unsure or lack enough context, rewrite the question conservatively without adding details.

FINAL OUTPUT:
- Return ONLY the rewritten natural-language question.
- No explanations.
- No preamble.
- No extra text.
"""

        query = "SELECT sys.ML_GENERATE(%s, JSON_OBJECT('task','generation','model_id','llama3.1-8b-instruct-v1'));"
        cursor.execute(query, (prompt,))
        result = cursor.fetchone()
        
        if not result or not result[0]: return question
        try:
            parsed = json.loads(result[0])
            return parsed.get("text", question).strip()
        except:
            return result[0].strip()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ============================================================
# 2️⃣ NL_SQL EXECUTION
# ============================================================
def run_nl_sql(
    rewritten_question: str,
    app_username: str,
    selected_db: str
):
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**get_db_config(app_username))
        cursor = conn.cursor()

        # sys.NL_SQL handles the translation to HeatWave SQL
        call_stmt = """
            CALL sys.NL_SQL(
                %s,
                @output,
                JSON_OBJECT(
                    'schemas', JSON_ARRAY(%s),
                    'model_id', 'llama3.1-8b-instruct-v1'
                )
            );
        """

        cursor.execute(call_stmt, (rewritten_question, selected_db))

        generated_sql = None
        answer_df = None
        idx = 1

        # sys.NL_SQL returns multiple result sets
        while True:
            try:
                rows = cursor.fetchall()
                if rows:
                    if idx == 1:
                        generated_sql = rows[0][0]
                    elif idx == 2:
                        cols = [d[0] for d in cursor.description]
                        answer_df = pd.DataFrame(rows, columns=cols)
                idx += 1
            except mysql.connector.errors.InterfaceError:
                pass

            if not cursor.nextset():
                break

        return generated_sql, answer_df

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ============================================================
# 3️⃣ CONVERSATIONAL ANSWER GENERATOR
# ============================================================
def generate_conversational_answer(
    question: str,
    df: pd.DataFrame,
    app_username: str
):
    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**get_db_config(app_username))
        cursor = conn.cursor()

        data_json = (
            df.to_json(orient="records")
            if isinstance(df, pd.DataFrame) and not df.empty
            else "[]"
        )

        prompt = f"""
You are a factual data reporter. 
The user asked: "{question}"

The database returned this result:
{data_json}

Rules:
1. If the data contains a list of IDs or names, acknowledge them as the answer to the question.
2. If the user asked "How many" and you see a list, count the items and provide the total.
3. If the data is empty, state clearly that no records match those criteria.
4. NEVER say "I don't have data" if there is data listed above.
5. Be direct. Do not explain your thought process.
"""

        query = """
            SELECT sys.ML_GENERATE(
                %s,
                JSON_OBJECT(
                    'task','generation',
                    'model_id','llama3.1-8b-instruct-v1'
                )
            );
        """

        cursor.execute(query, (prompt,))
        result = cursor.fetchone()

        if not result or not result[0]:
            return "No response generated."

        try:
            parsed = json.loads(result[0])
            return parsed.get("text", result[0])
        except Exception:
            return result[0]

    finally:
        if cursor: cursor.close()
        if conn: conn.close()