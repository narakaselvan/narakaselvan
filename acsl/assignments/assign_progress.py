import streamlit as st
import pandas as pd
from acsl.db import run_query

def assign_progress():
    # -----------------------------------------
    # GET CURRENT USER (FROM SESSION)
    # -----------------------------------------
    current_user = st.session_state.get("login")
    if not current_user:
        st.error("No user logged in")
        st.stop()

    # -----------------------------------------
    # CHECK ROLE
    # -----------------------------------------
    role_query = "SELECT role FROM susouser WHERE login = %s"
    role_df = pd.DataFrame(run_query(role_query, (current_user,)))
    if role_df.empty:
        st.error("User not found")
        st.stop()

    user_role = role_df.iloc[0]["role"]
    if user_role.lower() != "supervisor":
        st.error("You don't have permission to view this activity")
        st.stop()

    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 30px;'>
        📊 Assignment Management Progress
    </h1>
    """,
    unsafe_allow_html=True
    )

    # -----------------------------------------
    # FETCH ALL ASSIGNMENTS
    # -----------------------------------------
    query_all = """
    SELECT
        a.meta_responsiblename AS interviewer,
        CONCAT(a.preload_a0, a.preload_a01) AS block_id,
        a.meta_id AS assignment_id,
        a.meta_receivedbytabletatutc IS NOT NULL AS downloaded,
        a.meta_interviewscount <> 0 AS sent
    FROM assignments a
    JOIN susouser u
        ON a.meta_responsiblename = u.login
    WHERE u.supervisor = %s
    ORDER BY interviewer, block_id
    """
    df_all = pd.DataFrame(run_query(query_all, (current_user,)))
    if df_all.empty:
        st.info("No assignments found")
        return

    # -----------------------------------------
    # AGGREGATE DATA PER INTERVIEWER + BLOCK
    # -----------------------------------------
    def join_list(series):
        return ", ".join(series.astype(str))

    aggregated_df = df_all.groupby(["interviewer", "block_id"]).apply(
        lambda g: pd.Series({
            "all_assignment_ids": join_list(g["assignment_id"]),
            "received_by_interviewer": join_list(g.loc[g["downloaded"], "assignment_id"]),
            "interviews_sent": join_list(g.loc[g["sent"], "assignment_id"]),
        })
    ).reset_index()

    # -----------------------------------------
    # DISPLAY TABLE
    # -----------------------------------------
    st.dataframe(aggregated_df, use_container_width=True)