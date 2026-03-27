import streamlit as st
from acsl.analyze.statistics_data import show_variable_distribution
from acsl.analyze.outliers_data import show_outliers
from acsl.analyze.interview_time import show_interview_time_analysis

def show_analysis():
    sub_tabs=st.tabs(["Stitistics_info","Outliers", "Interview_Time"])

    with sub_tabs[0]:
        show_variable_distribution()

    with sub_tabs[1]:
        show_outliers()

    with sub_tabs[2]:
        show_interview_time_analysis()
