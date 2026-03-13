import streamlit as st
from psycopg2.extras import RealDictCursor

from acsl.db import get_connection

# ------------------------------------------------
# DB HELPERS
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


def fetch_grouped_blocks_for_responsible(userid):

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                (preload_a0 || preload_a01) AS block,
                array_agg(meta_id) AS assignmentids
            FROM assignments
            WHERE meta_responsiblename=%s
            GROUP BY block
            ORDER BY block
        """, (userid,))

        return cur.fetchall()


def fetch_grouped_blocks_for_my_interviewers(supervisor):

    ints = fetch_interviewers_for_supervisor(supervisor)

    if not ints:
        return []

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                (preload_a0 || preload_a01) AS block,
                array_agg(meta_id) AS assignmentids,
                meta_responsiblename AS responsible
            FROM assignments
            WHERE meta_responsiblename = ANY(%s)
            GROUP BY block, responsible
            ORDER BY block
        """, (ints,))

        return cur.fetchall()

# ------------------------------------------------
# QUEUE INSERT
# ------------------------------------------------
def queue_assignments(assign_ids, new_userid, created_by):

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

def update_responsibles(assign_ids, new_userid):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE assignments SET meta_responsiblename=%s WHERE meta_id=ANY(%s)",
                    (new_userid, assign_ids))
        conn.commit()
        return cur.rowcount


def re_assign(me):

    st.markdown(
    """
    <h1 style='text-align: center ; color: darkgreen; font-size: 20px;'>
        Re-Assign Blocks
    </h1>
    """,
    unsafe_allow_html=True
    )

    ints = fetch_interviewers_for_supervisor(me)

    source = st.selectbox("Source Interviewer", ints)

    target = st.selectbox(
        "Target Interviewer",
        [i for i in ints if i != source]
    )

    src = fetch_grouped_blocks_for_responsible(source)

    src_map = {r["block"]: r["assignmentids"] for r in src}

    selected_blocks = st.multiselect("Move blocks", src_map.keys())

    if st.button("Reassign Blocks"):

        ids = sum([src_map[b] for b in selected_blocks], [])

        updated = update_responsibles(ids, target)

        queue_assignments(ids, target, me)

        st.success(f"{updated} assignments queued for HQ sync")