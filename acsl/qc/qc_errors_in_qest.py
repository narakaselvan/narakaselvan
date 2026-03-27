import streamlit as st
import pandas as pd
import requests
from acsl.db import get_connection

def get_suso_session():
    server = st.secrets["SURVEY_URL"].rstrip('/')
    workspace = st.secrets.get("API_Workspace", "primary").strip('/')
    user = st.secrets["API_USER"]
    password = st.secrets["API_PASSWORD"]
    session = requests.Session()
    session.auth = (user, password)
    return session, server, workspace

def show_bulk_reject_dashboard():
    st.markdown(
        """
        <h1 style='text-align: left; color: darkred; font-size: 22px;'>
            🛑 Bulk Rejection Dashboard (Validation Errors)
        </h1>
        <p style='color: gray; font-size: 14px;'>Review validation errors per interview, add comments, and reject the block.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return  # Replaced st.stop() with return to keep tabs alive

    # ==========================================
    # 1. SECURITY CHECK
    # ==========================================
    def check_user_role(login):
        sql = "SELECT role FROM susouser WHERE login = %(login)s LIMIT 1;"
        try:
            conn = get_connection()
            df = pd.read_sql(sql, conn, params={'login': login})
            if not df.empty:
                return str(df.iloc[0]['role']).lower().strip()
            return None
        finally:
            if 'conn' in locals() and hasattr(conn, 'close'):
                conn.close()

    user_role = check_user_role(current_login_user)
    
    if user_role not in ['headquarters', 'supervisor', '4', '2']:
        st.error(f"🚫 Access Denied: Your role ({user_role}) does not have permission to reject interviews.")
        return

    # ==========================================
    # 2. AUTO-CREATE DB TABLE
    # ==========================================
    def initialize_database():
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sync_reject_interviews (
            id SERIAL PRIMARY KEY,
            interview_id VARCHAR(50),
            interview_key VARCHAR(50),
            block_number VARCHAR(100),
            comment TEXT,
            rejected_by VARCHAR(50),
            status VARCHAR(20),  
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            st.error(f"Database Initialization Error: {e}")
            return False
        finally:
            conn.close()

    if not initialize_database():
        return

    # ==========================================
    # 3. FETCH INTERVIEWERS WITH ERRORS
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=60)
    def get_interviewers_with_errors(login_user, role):
        supervisor_filter = ""
        if role in ['supervisor', '2']:
            supervisor_filter = "AND su.supervisor = %(current_login)s"

        sql = f"""
        WITH OriginalInterviewer AS (
            SELECT interview__key::VARCHAR AS int_key, responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
            FROM interview__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        CurrentStatus AS (
            SELECT interview__key::VARCHAR AS int_key, MAX(interview__status::FLOAT) as current_status
            FROM interview__diagnostics
            GROUP BY interview__key
        )
        SELECT DISTINCT oi.responsible__name AS interviewer
        FROM interview__errors ie
        JOIN OriginalInterviewer oi ON ie.interview__key::VARCHAR = oi.int_key AND oi.rn = 1
        JOIN CurrentStatus cs ON ie.interview__key::VARCHAR = cs.int_key
        JOIN susouser su ON oi.responsible__name = su.login
        WHERE cs.current_status IN (100, 120) 
          AND (su.role::TEXT = '1' OR LOWER(su.role::TEXT) = 'interviewer')
          {supervisor_filter}
        ORDER BY oi.responsible__name;
        """
        conn = get_connection()
        try:
            return pd.read_sql(sql, conn, params={'current_login': login_user})['interviewer'].tolist()
        finally:
            conn.close()

    interviewers = get_interviewers_with_errors(current_login_user, user_role)
    
    if not interviewers:
        st.success("🎉 No pending interviews with validation errors found in your assigned team!")
        return

    col1, col2 = st.columns(2)
    selected_interviewer = col1.selectbox("👤 Select Interviewer:", ["-- Select --"] + interviewers, key="err_int_sel")

    if selected_interviewer == "-- Select --":
        return

    # ==========================================
    # 4. FETCH BLOCKS
    # ==========================================
    def get_blocks_for_interviewer(interviewer):
        sql = """
        WITH OriginalInterviewer AS (
            SELECT interview__key::VARCHAR AS int_key, responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
            FROM interview__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        CurrentStatus AS (
            SELECT interview__key::VARCHAR AS int_key, MAX(interview__status::FLOAT) as current_status
            FROM interview__diagnostics
            GROUP BY interview__key
        )
        SELECT DISTINCT COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS block_number
        FROM interview__errors ie
        JOIN OriginalInterviewer oi ON ie.interview__key::VARCHAR = oi.int_key AND oi.rn = 1
        JOIN CurrentStatus cs ON ie.interview__key::VARCHAR = cs.int_key
        JOIN srilanka_agcensus2025 s ON ie.interview__key::VARCHAR = s.interview__key::VARCHAR
        JOIN assignments a ON s.assignment__id::VARCHAR = a.meta_id::VARCHAR
        JOIN susouser su ON oi.responsible__name = su.login
        WHERE oi.responsible__name = %(interviewer)s
          AND (a.preload_a0 IS NOT NULL OR a.preload_a01 IS NOT NULL)
          AND cs.current_status IN (100, 120)
          AND (su.role::TEXT = '1' OR LOWER(su.role::TEXT) = 'interviewer')
        ORDER BY block_number;
        """
        conn = get_connection()
        try:
            return pd.read_sql(sql, conn, params={'interviewer': interviewer})['block_number'].tolist()
        finally:
            conn.close()

    blocks = get_blocks_for_interviewer(selected_interviewer)
    
    if not blocks:
        st.info(f"No block data found for errors associated with {selected_interviewer}.")
        return

    selected_block = col2.selectbox("🏢 Select Block Number:", ["-- Select --"] + blocks, key="err_blk_sel")

    if selected_block == "-- Select --":
        return

    # ==========================================
    # 5. FETCH & DISPLAY ERROR DETAILS
    # ==========================================
    def get_error_details(interviewer, block):
        sql = """
        WITH OriginalInterviewer AS (
            SELECT interview__key::VARCHAR AS int_key, responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
            FROM interview__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        CurrentStatus AS (
            SELECT interview__key::VARCHAR AS int_key, MAX(interview__status::FLOAT) as current_status
            FROM interview__diagnostics
            GROUP BY interview__key
        )
        SELECT DISTINCT
            ie.interview__id,
            ie.interview__key AS "Interview Key", 
            ie.variable AS "Variable", 
            ie.message AS "Error Message"
        FROM interview__errors ie
        JOIN OriginalInterviewer oi ON ie.interview__key::VARCHAR = oi.int_key AND oi.rn = 1
        JOIN CurrentStatus cs ON ie.interview__key::VARCHAR = cs.int_key
        JOIN srilanka_agcensus2025 s ON ie.interview__key::VARCHAR = s.interview__key::VARCHAR
        JOIN assignments a ON s.assignment__id::VARCHAR = a.meta_id::VARCHAR
        JOIN susouser su ON oi.responsible__name = su.login
        WHERE oi.responsible__name = %(interviewer)s
          AND (COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '')) = %(block)s
          AND cs.current_status IN (100, 120)
          AND (su.role::TEXT = '1' OR LOWER(su.role::TEXT) = 'interviewer')
        ORDER BY ie.interview__key;
        """
        conn = get_connection()
        try:
            return pd.read_sql(sql, conn, params={'interviewer': interviewer, 'block': block})
        finally:
            conn.close()

    df_errors = get_error_details(selected_interviewer, selected_block)

    st.markdown(f"### 📋 Interviews in Block: `{selected_block}`")
    
    unique_interviews = df_errors[['interview__id', 'Interview Key']].drop_duplicates()
    num_interviews = len(unique_interviews)
    
    for idx, row in unique_interviews.iterrows():
        i_id = row['interview__id']
        i_key = row['Interview Key']
        
        interview_specific_errors = df_errors[df_errors['interview__id'] == i_id][['Variable', 'Error Message']]
        error_count = len(interview_specific_errors)
        
        with st.expander(f"📄 Interview Key: {i_key}  (Contains {error_count} error(s))", expanded=True):
            st.dataframe(interview_specific_errors, use_container_width=True, hide_index=True)
            
            # UNIQUE KEY PREFIX FOR VALIDATION ERRORS
            st.text_area(
                f"📝 Add specific comment for Interview {i_key}:", 
                key=f"error_comment_{i_id}",  
                placeholder="Optional: Enter a specific reason for rejection. If left blank, a default message will be used."
            )

    # ==========================================
    # 6. BULK REJECTION ACTION
    # ==========================================
    st.markdown("---")
    st.warning(f"You are about to reject **{num_interviews}** unique interview(s) in Block **{selected_block}**.")
    
    if st.button("🚨 Reject All Interviews in Block", type="primary", key="err_reject_btn"):
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        conn = get_connection()
        cursor = conn.cursor()
        session, server, workspace = get_suso_session()
        
        success_count = 0
        already_rejected_count = 0
        fail_count = 0

        try:
            for i, (idx, row) in enumerate(unique_interviews.iterrows(), start=1):
                i_id = row['interview__id']
                i_key = row['Interview Key']
                
                # Fetch comment using the error-specific prefix
                indiv_comment = st.session_state.get(f"error_comment_{i_id}", "").strip()
                
                if not indiv_comment:
                    indiv_comment = "Rejected due to validation errors during bulk block review."
                
                insert_sql = """
                INSERT INTO sync_reject_interviews 
                (interview_id, interview_key, block_number, comment, rejected_by, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'Pending', NOW())
                RETURNING id;
                """
                cursor.execute(insert_sql, (i_id, i_key, selected_block, indiv_comment, current_login_user))
                local_record_id = cursor.fetchone()[0]
                conn.commit()
                
                api_url = f"{server}/{workspace}/api/v1/interviews/{i_id}/reject"
                
                try:
                    r = session.patch(api_url, params={"comment": indiv_comment})
                    r.raise_for_status()
                    
                    update_sql = "UPDATE sync_reject_interviews SET status = 'Synced' WHERE id = %s;"
                    cursor.execute(update_sql, (local_record_id,))
                    conn.commit()
                    success_count += 1
                    
                except requests.exceptions.HTTPError as api_err:
                    if api_err.response.status_code == 406:
                        st.toast(f"Skipped {i_key}: It is already rejected on the server.", icon="ℹ️")
                        update_sql = "UPDATE sync_reject_interviews SET status = 'Already Rejected' WHERE id = %s;"
                        cursor.execute(update_sql, (local_record_id,))
                        conn.commit()
                        already_rejected_count += 1
                    else:
                        fail_count += 1
                        st.error(f"API Error {i_key}: {api_err.response.status_code} - {api_err.response.text}")
                except Exception as e:
                    fail_count += 1
                    st.error(f"Network error for {i_key}: {str(e)}")

                progress = i / num_interviews
                progress_bar.progress(progress)
                status_text.text(f"Processing... {i}/{num_interviews}")

            if fail_count == 0:
                msg = f"✅ Process complete! {success_count} newly rejected."
                if already_rejected_count > 0:
                    msg += f" ({already_rejected_count} were already rejected previously)."
                st.success(msg)
            else:
                st.warning(f"⚠️ {success_count} rejected successfully. {fail_count} failed API sync and remain 'Pending' in your queue.")
                
            st.cache_data.clear()

        except Exception as e:
            conn.rollback()
            st.error(f"A critical database error occurred: {str(e)}")
        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    show_bulk_reject_dashboard