# acsl/modules/admin.py
import streamlit as st
from acsl.modules.user_file_validation import user_file_validation
from acsl.modules.upload_bulk_user import create_users
from acsl.assignments.download_ass import download_assignments
from acsl.assignments.upload_ass import upload_assignments
from acsl.assignments.Revert_assignments import retry_failed_jobs
from acsl.assignments.sync_status import sync_result
from acsl.assignments.supervisor_assignments_updated_summary import sync_dashboard
from acsl.assignments.prepare_assignments import prepare_assignments
from acsl.interviews.interviewes import show_interviews

def show_admin():
    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 30px;'>
        🛡️ System Management
    </h1>
    """,
    unsafe_allow_html=True
    )

    # Changed "Users" to "Bulk Users"
    sub_tabs = st.tabs(["Assignments", "Bulk Users", "Interviews", "Monitoring"])

    with sub_tabs[0]:
        assign_sub_tabs = st.tabs(["Prepare Assignments", "Upload to SuSo", "L-Form" ,"Download Assignments", "Upload to LocalDB", "Revert Assignments"])

        with assign_sub_tabs[0]:
            prepare_assignments()
        with assign_sub_tabs[1]:
            st.write("Upload to SuSo")
        with assign_sub_tabs[2]:
            st.write("L-Form")
        with assign_sub_tabs[3]:
            download_assignments()
        with assign_sub_tabs[4]:
            upload_assignments()
        with assign_sub_tabs[5]:
            retry_failed_jobs()
        
    with sub_tabs[1]:
        # Only Bulk User tools remain here for the Admin
        bulk_user_sub_tabs = st.tabs(["Validate_File", "Upload_file"])

        with bulk_user_sub_tabs[0]:
            user_file_validation()
        with bulk_user_sub_tabs[1]:
            create_users()

    with sub_tabs[2]:
       show_interviews()

    with sub_tabs[3]:
        monitoring_sub_tabs = st.tabs(["Sync Summary","Sync Details"])
        with monitoring_sub_tabs[0]:
            sync_dashboard()
        with monitoring_sub_tabs[1]:
            sync_result()