import streamlit as st

from acsl.db import get_connection

def retry_failed_jobs():

    st.markdown(
    """
    <h1 style='text-align: left ; color: red; font-size: 20px;'>
        🛡️ Retry Failed Sync Jobs
    </h1>
    """,
    unsafe_allow_html=True
    )

    if st.button("Retry Failed"):

        with get_connection() as conn:

            cur = conn.cursor()

            cur.execute("""
                UPDATE sync_queue
                SET status='pending',
                    retry_count=0
                WHERE status='failed'
            """)

            conn.commit()

        st.success("Failed jobs requeued")