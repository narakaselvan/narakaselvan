import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from acsl.db import get_connection

# ==========================================
# ⚙️ SURVEY SOLUTIONS API CONFIGURATION
# ==========================================
SUSO_URL = "https://your-server-name.mysurvey.solutions" 
WORKSPACE = "primary" 
API_USER = "your_api_username"
API_PASS = "your_api_password"

def initialize_database():
    """Creates the local audit log table if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS bulk_approvals_log (
            id SERIAL PRIMARY KEY,
            interview__key VARCHAR(50),
            interview__id VARCHAR(50),
            action_by VARCHAR(100),
            role VARCHAR(50),
            action_type VARCHAR(50),
            api_status VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_sql)
        conn.commit()
    except Exception as e:
        st.error(f"Failed to initialize log table: {e}")
    finally:
        cursor.close()
        conn.close()

def fetch_eligible_interviews(role, prefix):
    """
    Fetches interviews eligible for approval.
    STRICT QUALITY GATES APPLIED: Must have 0 errors and 0 unanswered questions.
    """
    conn = get_connection()
    
    if role in ['supervisor', '2']:
        target_status = 100 # Completed 
    elif role in ['hq', 'admin', '1']:
        target_status = 120 # Approved by Supervisor
    else:
        return pd.DataFrame() 
        
    try:
        sql = """
        WITH OriginalInterviewer AS (
            SELECT interview__key::VARCHAR AS int_key, responsible__name,
                   ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
            FROM interview__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        MainData AS (
            SELECT interview__key::VARCHAR AS int_key, MAX(assignment__id::VARCHAR) AS assignment_id
            FROM srilanka_agcensus2025
            GROUP BY interview__key
        ),
        ErrorCounts AS (
            SELECT interview__key::VARCHAR AS int_key, COUNT(*) as err_count
            FROM interview__errors
            GROUP BY interview__key
        )
        SELECT DISTINCT
            CAST(0 AS BOOLEAN) AS "Select",
            d.interview__key::VARCHAR AS "Interview Key",
            d.interview__id::VARCHAR AS "Interview GUID",
            COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
            oi.responsible__name AS "Interviewer",
            COALESCE(ec.err_count, 0) AS "Errors",
            COALESCE(d.n_questions_unanswered::INT, 0) AS "Unanswered",
            d.interview__status::FLOAT AS "Status Code"
        FROM interview__diagnostics d
        JOIN OriginalInterviewer oi ON d.interview__key::VARCHAR = oi.int_key AND oi.rn = 1
        JOIN susouser su ON oi.responsible__name = su.login
        LEFT JOIN MainData m ON d.interview__key::VARCHAR = m.int_key
        LEFT JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
        LEFT JOIN ErrorCounts ec ON d.interview__key::VARCHAR = ec.int_key
        WHERE d.interview__status::FLOAT = %(status)s
          AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
          
          -- STRICT QUALITY GATES
          AND COALESCE(ec.err_count, 0) = 0
          AND COALESCE(d.n_questions_unanswered::INT, 0) = 0
          
        ORDER BY "Interview Key";
        """
        df = pd.read_sql(sql, conn, params={'status': target_status, 'prefix': prefix})
        
        if not df.empty:
            status_map = {100: "Completed (Pending Sup.)", 120: "Sup. Approved (Pending HQ)"}
            df["Current Status"] = df["Status Code"].map(status_map)
            df = df.drop(columns=["Status Code"])
            
        return df
    finally:
        conn.close()

def log_approval_action(interview_key, interview_id, action_by, role, action_type, api_status):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO bulk_approvals_log (interview__key, interview__id, action_by, role, action_type, api_status)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(sql, (interview_key, interview_id, action_by, role, action_type, api_status))
        conn.commit()
    except Exception as e:
        pass 
    finally:
        cursor.close()
        conn.close()

def show_bulk_approval():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            ✅ Bulk Interview Approval
        </h1>
        <p style='color: gray; font-size: 14px;'>Review and bulk-approve pending interviews. Actions are synced directly to the server.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    initialize_database()

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    def get_user_info(login):
        sql = "SELECT role, workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn, params={'login': login})
            if not df.empty:
                return str(df.iloc[0]['role']).lower().strip(), str(df.iloc[0]['workingarea']).strip()
            return None, None
        finally:
            conn.close()

    user_role, user_wa = get_user_info(current_login_user)
    
    if user_role not in ['supervisor', '2', 'headquarters', 'admin', '1']:
        st.error("🚫 Access Denied: You do not have permission to approve interviews.")
        return # FIXED: Changed from st.stop() to return

    prefix = "" 
    if user_wa:
        if user_wa == '0000000': prefix = ''
        elif user_wa.endswith('000000'): prefix = user_wa[:1]
        elif user_wa.endswith('00000'): prefix = user_wa[:2]
        elif user_wa.endswith('000'): prefix = user_wa[:4]
        else: prefix = user_wa

    is_hq = user_role in ['hq', 'admin', '1']
    action_name = "HQ Approve" if is_hq else "Supervisor Approve"
    api_endpoint_suffix = "hqapprove" if is_hq else "approve"

    # UI Warning for Quality Gates
    st.info("🛡️ **Strict Quality Gates Active:** Interviews will ONLY appear here if they have **0 Errors** and **0 Unanswered Questions**. Any interview failing these checks must be rejected or fixed by the interviewer first.")

    with st.spinner("Fetching eligible interviews for approval..."):
        df_eligible = fetch_eligible_interviews(user_role, prefix)

    if df_eligible.empty:
        st.success(f"🎉 No perfectly clean interviews are currently pending {action_name} in your area.")
        return # FIXED: Changed from st.stop() to return

    st.markdown(f"### 📋 Pending {action_name} ({len(df_eligible)} available)")
    
    edited_df = st.data_editor(
        df_eligible,
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "Errors": st.column_config.NumberColumn("Errors", format="%d", disabled=True),
            "Unanswered": st.column_config.NumberColumn("Unanswered", format="%d", disabled=True)
        },
        disabled=["Interview Key", "Interview GUID", "Block", "Interviewer", "Current Status", "Errors", "Unanswered"],
        use_container_width=True
    )

    selected_rows = edited_df[edited_df["Select"] == True]
    
    if len(selected_rows) > 0:
        st.write(f"**{len(selected_rows)}** clean interviews selected for approval.")
        
        comment = st.text_input("Approval Comment (Optional):", value="Bulk approved via dashboard (Zero Errors Verified)")
        
        if st.button(f"🚀 Execute {action_name}"):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            error_count = 0

            for idx, row in selected_rows.reset_index(drop=True).iterrows():
                int_key = row["Interview Key"]
                int_guid = row["Interview GUID"]
                
                status_text.text(f"Processing Interview: {int_key}...")
                
                api_url = f"{SUSO_URL}/api/v1/interviews/{int_guid}/{api_endpoint_suffix}"
                headers = {"Workspace": WORKSPACE}
                payload = {"comment": comment}
                
                try:
                    response = requests.patch(
                        api_url, 
                        auth=HTTPBasicAuth(API_USER, API_PASS), 
                        headers=headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        api_status = "Success (200)"
                        success_count += 1
                    else:
                        api_status = f"Failed ({response.status_code}): {response.text}"
                        error_count += 1
                        
                except Exception as e:
                    api_status = f"API Connection Error: {str(e)}"
                    error_count += 1

                log_approval_action(int_key, int_guid, current_login_user, user_role, action_name, api_status)
                progress_bar.progress((idx + 1) / len(selected_rows))

            status_text.text("Bulk Approval Complete!")
            if error_count == 0:
                st.success(f"✅ Successfully approved {success_count} interviews! They are now synced with Headquarters.")
            else:
                st.warning(f"⚠️ Process finished. {success_count} succeeded, {error_count} failed. Check the local DB log for details.")
                
            if st.button("Refresh List"):
                st.rerun()

if __name__ == "__main__":
    show_bulk_approval()