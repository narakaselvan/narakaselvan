import streamlit as st

from acsl.interviews.download_interviews_from_SuSo import show_download_interviews_from_SuSo
from acsl.interviews.upload_interviews_local_DB import show_upload_interviews_to_local_DB

def show_interviews():
     
    interview_sub_tabs=st.tabs(["Download_from_SuSo", "Upload_to_Local_DB"])

    with interview_sub_tabs[0]:
         show_download_interviews_from_SuSo()

    with interview_sub_tabs[1]:
         show_upload_interviews_to_local_DB()