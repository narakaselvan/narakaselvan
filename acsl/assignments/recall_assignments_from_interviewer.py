import streamlit as st
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection


# ------------------------------------------------
# Fetch interviewers under supervisor
# ------------------------------------------------
def fetch_interviewers_for_supervisor(supervisor):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT login
            FROM susouser
            WHERE supervisor=%s
            ORDER BY login
        """, (supervisor,))
        return [r["login"] for r in cur.fetchall()]


# ------------------------------------------------
# Fetch recallable blocks for an interviewer
# ------------------------------------------------
def fetch_recallable_blocks(interviewer):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT DISTINCT
                (preload_a0 || preload_a01) AS block
            FROM assignments
            WHERE meta_responsiblename=%s
              AND COALESCE(meta_interviewscount,0) = 0
            ORDER BY block
        """, (interviewer,))
        return [r["block"] for r in cur.fetchall()]


# ------------------------------------------------
# Fetch all assignments in a block for recall
# ------------------------------------------------
def fetch_assignments_in_block(block, interviewer):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT meta_id
            FROM assignments
            WHERE (preload_a0 || preload_a01)=%s
              AND meta_responsiblename=%s
              AND COALESCE(meta_interviewscount,0) = 0
        """, (block, interviewer))
        return [r[0] for r in cur.fetchall()]


# ------------------------------------------------
# Update responsible user
# ------------------------------------------------
def update_responsibles(assign_ids, supervisor):
    if not assign_ids:
        return 0
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE assignments
            SET meta_responsiblename=%s
            WHERE meta_id = ANY(%s)
        """, (supervisor, assign_ids))
        conn.commit()
        return cur.rowcount


# ------------------------------------------------
# Insert into sync queue
# ------------------------------------------------
def queue_assignments(assign_ids, new_userid, created_by):
    if not assign_ids:
        return
    conn = get_connection()
    cur = conn.cursor()
    for aid in assign_ids:
        cur.execute("""
            INSERT INTO sync_queue
                (assignmentid, new_responsible, status, created_at, created_by)
            VALUES (%s,%s,'pending',now(),%s)
        """, (aid, new_userid, created_by))
    conn.commit()
    conn.close()


# ------------------------------------------------
# Recall blocks UI
# ------------------------------------------------
def recall_blocks(me):

    st.markdown(
    """
    <h1 style='text-align: center ; color: darkgreen; font-size: 20px;'>
        Recall Blocks From Interviewer
    </h1>
    """,
    unsafe_allow_html=True
    )

    # 1. List interviewers under supervisor
    interviewers = fetch_interviewers_for_supervisor(me)
    if not interviewers:
        st.warning("No interviewers found under this supervisor")
        return

    interviewer = st.selectbox(
        "Select Interviewer",
        interviewers,
        key="recall_interviewer"
    )

    # 2. Show recallable blocks
    blocks = fetch_recallable_blocks(interviewer)
    if not blocks:
        st.info("No recallable blocks found for this interviewer")
        return

    selected_blocks = st.multiselect(
        "Select Blocks to Recall",
        blocks,
        key="recall_blocks"
    )

    # 3. Recall button
    if st.button("Recall Selected Blocks", key="recall_button"):
        all_ids = []

        for block in selected_blocks:
            ids = fetch_assignments_in_block(block, interviewer)
            all_ids.extend(ids)

        if not all_ids:
            st.warning("No assignments found to recall in selected blocks")
            return

        updated = update_responsibles(all_ids, me)
        queue_assignments(all_ids, me, me)

        st.success(f"{updated} assignments recalled from {interviewer} and queued for HQ sync")


# ------------------------------------------------
# Supervisor Panel
# ------------------------------------------------
def supervisor_panel(me):
    st.title("Supervisor Assignment Control Panel")

    menu = st.radio(
        "Select Action",
        ["Recall Blocks"],
        key="supervisor_menu"
    )

    if menu == "Recall Blocks":
        recall_blocks(me)


# ------------------------------------------------
# Main
# ------------------------------------------------
if __name__ == "__main__":
    me = st.session_state.get("login")
    if me:
        supervisor_panel(me)
    else:
        st.error("User not logged in")