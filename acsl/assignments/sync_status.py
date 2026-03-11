import streamlit as st
from psycopg2.extras import RealDictCursor

from acsl.db import get_connection

def sync_result():

    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        Synchronization Results
    </h1>
    """,
    unsafe_allow_html=True
    )

    conn = get_connection()

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT * FROM sync_queue
        ORDER BY id DESC
        LIMIT 500
    """)

    rows = cur.fetchall()

    conn.close()

    st.dataframe(rows, use_container_width=True)

# --------------------------------------------------
# Run Dashboard
# --------------------------------------------------
if __name__ == "__main__":
    sync_result()