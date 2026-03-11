import streamlit as st
import requests

from psycopg2.extras import RealDictCursor


from acsl.db import get_connection

# ------------------------------------------------
# QUEUE LOGIC (Your Idea)
# ------------------------------------------------
def queue_assignments(assign_ids, new_userid):
    conn = get_connection()
    cur = conn.cursor()
    for aid in assign_ids:
        cur.execute("""
            INSERT INTO sync_queue (assignmentid, new_responsible)
            VALUES (%s, %s)
        """, (aid, new_userid))
    conn.commit()
    conn.close()

# ------------------------------------------------
# ASSIGNMENT STATUS API
# ------------------------------------------------
def get_assignment_status(aid):
    url = f"{st.secrets['SURVEY_URL'].rstrip('/')}/api/v1/assignments/{aid}"
    try:
        resp = requests.get(url, auth=(st.secrets["API_USER"], st.secrets["API_PASSWORD"]), timeout=20)
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
# HQ UPDATE RESPONSIBLE
# ------------------------------------------------
def sync_assignment_to_survey(aid, new_resp):
    current, _ = get_assignment_status(aid)
    if current and current["responsible"] == new_resp:
        return True, "Already same in HQ"

    url = f"{st.secrets['SURVEY_URL'].rstrip('/')}/api/v1/assignments/{aid}/assign"
    try:
        resp = requests.patch(url, json={"responsible": new_resp},
                              auth=(st.secrets["API_USER"], st.secrets["API_PASSWORD"]))
        return resp.status_code in (200, 204), resp.text
    except Exception as e:
        return False, str(e)

def process_queue_once():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM sync_queue WHERE status='pending' ORDER BY id LIMIT 1")
    job = cur.fetchone()

    if not job:
        conn.close()
        return None, "No pending jobs"

    ok, msg = sync_assignment_to_survey(job["assignmentid"], job["new_responsible"])
    new_status = "done" if ok else "failed"

    cur.execute("UPDATE sync_queue SET status=%s, updated_at=now() WHERE id=%s",
                (new_status, job["id"]))
    conn.commit()
    conn.close()
    return job, msg


def synchronize():

    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        Synchronize with Survey Solutions HQ
    </h1>
    """,
    unsafe_allow_html=True
    )

    if st.button("Process 1 Job"):

        job, msg = process_queue_once()

        if not job:
            st.info("Queue empty")

        else:
            st.success(
                f"{job['assignmentid']} → {job['new_responsible']} : {msg}"
            )

    if st.button("Process All Pending"):

        processed = 0

        while True:

            job, msg = process_queue_once()

            if not job:
                break

            processed += 1

        st.success(f"Processed {processed} queued sync jobs.")