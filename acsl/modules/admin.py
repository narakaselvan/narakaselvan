import streamlit as st
from acsl.modules.user_file_validation import user_file_validation
from acsl.modules.upload_bulk_user import create_users
from acsl.users.add_users import add_user
from acsl.users.edit_users import edit_user
from acsl.assignments.download_ass import download_assignments
from acsl.assignments.upload_ass import upload_assignments

def show_admin():
    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 30px;'>
        🛡️ System Management
    </h1>
    """,
    unsafe_allow_html=True
    )

    sub_tabs = st.tabs(["Assignments", "Users", "Interviews"])

    with sub_tabs[0]:
        assign_sub_tabs = st.tabs(["Download Assignments", "Upload Assignments"])

        with assign_sub_tabs[0]:
            download_assignments()

        with assign_sub_tabs[1]:
            upload_assignments()
        
    with sub_tabs[1]:
        user_sub_tabs= st.tabs(["Single User", "Bulk User"])
        
        with user_sub_tabs[0]:
            single_user_sub_tabs = st.tabs(["➕ Add", "✏️ Edit"])

            with single_user_sub_tabs[0]:
                add_user()

            with single_user_sub_tabs[1]:
                edit_user()

        with user_sub_tabs[1]:
            bulk_user_sub_tabs = st.tabs (["Validate_File", "Upload_file"])

            with bulk_user_sub_tabs[0]:
                user_file_validation()

            with bulk_user_sub_tabs[1]:
                create_users()