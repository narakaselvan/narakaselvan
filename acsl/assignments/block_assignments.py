import pandas as pd
import streamlit as st
import requests
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection


# ------------------------------------------------
# FETCH INTERVIEWERS
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
# FETCH BLOCKS FOR CURRENT USER
# ------------------------------------------------
def fetch_grouped_blocks_for_responsible(userid):

    with get_connection() as conn:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                (preload_a0::text || preload_a01::text) AS block,
                array_agg(meta_id) AS assignmentids
            FROM assignments
            WHERE meta_responsiblename=%s
            GROUP BY block
            ORDER BY block
        """, (userid,))

        return cur.fetchall()


# ------------------------------------------------
# SURVEY SOLUTIONS API
# ------------------------------------------------
def get_assignment_status(aid):

    url = f"{st.secrets['SURVEY_URL'].rstrip('/')}/api/v1/assignments/{aid}"

    try:
        resp = requests.get(
            url,
            auth=(st.secrets["API_USER"], st.secrets["API_PASSWORD"]),
            timeout=20
        )
    except Exception as e:
        return None, str(e)

    if resp.status_code == 200:

        j = resp.json()

        return {
            "responsible": j.get("Responsible"),
            "status": j.get("Status"),
            "updated": j.get("UpdatedAtUtc"),
        }, ""

    else:
        return None, resp.text


# ------------------------------------------------
# UPDATE SURVEY SOLUTIONS
# ------------------------------------------------
def sync_assignment_to_survey(aid, new_resp):

    url = f"{st.secrets['SURVEY_URL'].rstrip('/')}/api/v1/assignments/{aid}/assign"

    try:

        resp = requests.patch(
            url,
            json={"responsible": new_resp},
            auth=(st.secrets["API_USER"], st.secrets["API_PASSWORD"])
        )

        return resp.status_code in (200, 204), resp.text

    except Exception as e:

        return False, str(e)


# ------------------------------------------------
# QUEUE INSERT
# ------------------------------------------------
def queue_assignments(assign_ids, new_userid, old_userid):

    me=st.session_state.get("login")

    with get_connection() as conn:

        cur = conn.cursor()

        for aid in assign_ids:

            cur.execute("""
                INSERT INTO sync_queue
                (assignmentid, new_responsible, old_responsible, status, created_at,created_by)
                VALUES (%s,%s,%s,'pending',now(),%s)
            """, (aid, new_userid, old_userid,me))

        conn.commit()


# ------------------------------------------------
# PROCESS ONE QUEUE JOB
# ------------------------------------------------
def process_queue_once():

    conn = get_connection()

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM sync_queue
        WHERE status='pending'
        ORDER BY id
        LIMIT 1
    """)

    job = cur.fetchone()

    if not job:
        conn.close()
        return None, "No pending jobs"

    aid = job["assignmentid"]
    new_resp = job["new_responsible"]
    old_resp = job["old_responsible"]

    ok, msg = sync_assignment_to_survey(aid, new_resp)

    if ok:

        cur.execute("""
            UPDATE sync_queue
            SET status='done',
                updated_at=now()
            WHERE id=%s
        """, (job["id"],))

    else:

        # REVERT LOCAL DATABASE
        cur.execute("""
            UPDATE assignments
            SET meta_responsiblename=%s
            WHERE meta_id=%s
        """, (old_resp, aid))

        cur.execute("""
            UPDATE sync_queue
            SET status='failed',
                updated_at=now()
            WHERE id=%s
        """, (job["id"],))

    conn.commit()

    conn.close()

    return job, msg


# ------------------------------------------------
# PROCESS MULTIPLE JOBS
# ------------------------------------------------
def process_queue_batch(limit=10):

    results = []

    for i in range(limit):

        job, msg = process_queue_once()

        if not job:
            break

        results.append((job["assignmentid"], msg))

    return results


# ------------------------------------------------
# BLOCK ASSIGN UI
# ------------------------------------------------
def block_assign(me):

    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        Block Assign
    </h1>
    """,
    unsafe_allow_html=True
    )

    blocks = fetch_grouped_blocks_for_responsible(me)

    interviewers = fetch_interviewers_for_supervisor(me)

    if not interviewers:
        st.warning("No interviewers found")
        return

    target = st.selectbox("Select interviewer", interviewers)

    blk_map = {r["block"]: r["assignmentids"] for r in blocks}

    selected_blocks = st.multiselect(
        "Select blocks",
        list(blk_map.keys())
    )

    if st.button("Assign Blocks"):

        if not selected_blocks:
            st.warning("Please select blocks")
            return

        ids = sum([blk_map[b] for b in selected_blocks], [])

        # --------------------------------------
        # UPDATE LOCAL DB IMMEDIATELY
        # --------------------------------------
        with get_connection() as conn:

            cur = conn.cursor()

            cur.execute("""
                UPDATE assignments
                SET meta_responsiblename=%s
                WHERE meta_id = ANY(%s)
            """, (target, ids))

            conn.commit()

        # --------------------------------------
        # ADD TO SYNC QUEUE
        # --------------------------------------
        queue_assignments(ids, target, me)

        st.success(f"{len(ids)} assignments updated locally and queued for HQ sync")


# ------------------------------------------------
# SYNC WORKER PAGE
# ------------------------------------------------
def sync_worker_page():

    st.header("Assignment Sync Worker")

    if st.button("Process 10 Queue Jobs"):

        results = process_queue_batch(10)

        if not results:

            st.info("No pending jobs")

        else:

            for r in results:

                st.write(r)