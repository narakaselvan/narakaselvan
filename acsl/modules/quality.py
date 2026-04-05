import streamlit as st

from acsl.qc.qctrl import show_qctrl_progress
from acsl.qc.qc_errors_in_qest import show_bulk_reject_dashboard
from acsl.qc.qc_unanswered_question import show_bulk_reject_unanswered_dashboard
from acsl.qc.qc_bulk_approve import show_bulk_approval
from acsl.qc.qc_questionnaire_random_check import show_generalized_verification_dashboard

def show_quality():
    qctab=st.tabs(["Progress", "Recommended_for_Approval","Suggestion_for_Reject","Randam_Check"])

    with qctab[0]:
        show_qctrl_progress()

    with qctab[1]:
        show_bulk_approval()

    with qctab[2]:
        subtab_reject=st.tabs(["Errors_in_Questionnaire", "Incomplete_Questionnaire","Inconsistency","Clerical Mistakes","Numerical Errors"])
        
        with subtab_reject[0]:
            show_bulk_reject_dashboard()

        with subtab_reject[1]:
            show_bulk_reject_unanswered_dashboard()

    with qctab[3]:
        show_generalized_verification_dashboard()