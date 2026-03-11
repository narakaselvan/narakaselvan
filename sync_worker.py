import time
import requests
from psycopg2.extras import RealDictCursor
from acsl.db import get_connection
import streamlit as st


SURVEY_URL = st.secrets["SURVEY_URL"].rstrip("/")
API_USER = st.secrets["API_USER"]
API_PASSWORD = st.secrets["API_PASSWORD"]


def sync_assignment(aid, new_resp):

    url = f"{SURVEY_URL}/api/v1/assignments/{aid}/assign"

    try:

        r = requests.patch(
            url,
            json={"responsible": new_resp},
            auth=(API_USER, API_PASSWORD),
            timeout=20
        )

        return r.status_code in (200, 204), r.text

    except Exception as e:

        return False, str(e)


def process_queue():

    with get_connection() as conn:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM sync_queue
            WHERE status='pending'
            ORDER BY id
            LIMIT 20
        """)

        jobs = cur.fetchall()

        if not jobs:
            return

        for job in jobs:

            aid = job["assignmentid"]
            new_resp = job["new_responsible"]
            old_resp = job["old_responsible"]

            ok, msg = sync_assignment(aid, new_resp)

            if ok:

                cur.execute("""
                    UPDATE sync_queue
                    SET status='done',
                        updated_at=now(),
                        message=%s
                    WHERE id=%s
                """, (msg, job["id"]))

            else:

                if job["retry_count"] >= 3:

                    # revert local DB
                    cur.execute("""
                        UPDATE assignments
                        SET meta_responsiblename=%s
                        WHERE meta_id=%s
                    """, (old_resp, aid))

                    cur.execute("""
                        UPDATE sync_queue
                        SET status='failed',
                            updated_at=now(),
                            message=%s
                        WHERE id=%s
                    """, (msg, job["id"]))

                else:

                    cur.execute("""
                        UPDATE sync_queue
                        SET retry_count = retry_count + 1,
                            updated_at=now(),
                            message=%s
                        WHERE id=%s
                    """, (msg, job["id"]))

        conn.commit()


while True:

    process_queue()

    time.sleep(5)