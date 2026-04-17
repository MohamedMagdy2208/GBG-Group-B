import streamlit as st
from src.config import MAX_QUESTION_LENGTH
from src.database import get_table_names, get_table_columns
from src.chains import generate_sql, run_sql_with_retry, generate_response
from src.utils import validate_question

st.set_page_config(page_title="Chinook SQL Chatbot", page_icon=":musical_note:", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.header("Chinook SQL Chatbot")
    st.markdown("Ask natural language questions about the Chinook music database.")

    # Schema viewer
    st.subheader("Database Schema")
    try:
        tables = get_table_names()
        for table in sorted(tables):
            with st.expander(f"Table: {table}"):
                try:
                    columns = get_table_columns(table)
                    for col in columns:
                        st.text(f"  - {col}")
                except Exception:
                    st.text("  (could not load columns)")
    except Exception:
        st.info("Connect to database to view schema.")

    st.divider()

    # Example questions
    st.subheader("Example Questions")
    example_questions = [
        "How many customers are in the USA?",
        "Find the top 5 customers by total spending",
        "Which country generated the highest revenue?",
        "Count how many tracks exist in each genre",
        "Get monthly revenue for 2012",
        "Rank customers by spending within each country",
    ]
    for eq in example_questions:
        if st.button(eq, key=eq, use_container_width=True):
            st.session_state["prefill_question"] = eq

    st.divider()

    # Clear chat
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- Main Chat Area ---
st.title("Chinook SQL Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and "sql" in msg:
            with st.expander("Generated SQL", expanded=False):
                st.code(msg["sql"], language="sql")
        st.markdown(msg["content"])

# Handle prefilled question from sidebar
prefill = st.session_state.pop("prefill_question", None)
question = st.chat_input("Ask a question about the database...")
if prefill and not question:
    question = prefill

if question:
    # Validate input
    is_valid, error_msg = validate_question(question, MAX_QUESTION_LENGTH)
    if not is_valid:
        st.error(error_msg)
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            try:
                with st.status("Processing your question...", expanded=True) as status:
                    st.write("Generating SQL query...")
                    sql_query = generate_sql(question)

                    st.write("Executing query...")
                    result, sql_query = run_sql_with_retry(question, sql_query)

                    st.write("Generating answer...")
                    answer = generate_response(question, result)

                    status.update(label="Done!", state="complete", expanded=False)

                with st.expander("Generated SQL", expanded=False):
                    st.code(sql_query, language="sql")

                st.markdown(answer)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sql": sql_query,
                })

            except ValueError as e:
                st.error(str(e))
                st.session_state.messages.append({"role": "assistant", "content": f"Warning: {e}"})

            except Exception as e:
                error_text = (
                    "Sorry, I couldn't process that query. "
                    "Try rephrasing your question or ask something simpler."
                )
                st.error(f"{error_text}\n\nDetails: {e}")
                st.session_state.messages.append({"role": "assistant", "content": error_text})
