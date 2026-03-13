import streamlit as st

def make_connection():
    # -------------------------------
    # DATABASE CONNECTION
    # -------------------------------
    DB_HOST = st.secrets["DB_HOST"]
    DB_NAME = st.secrets["DB_NAME"]
    DB_USER = st.secrets["DB_USER"]
    DB_PASS = st.secrets["DB_PASSWORD"]
    DB_PORT = st.secrets.get("DB_PORT", 5432)
