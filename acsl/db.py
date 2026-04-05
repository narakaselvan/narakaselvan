import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor
import requests
from requests.auth import HTTPBasicAuth

def get_connection():
    conn = psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
    )
    
    # 🚀 THIS IS THE FIX!
    # It forces psycopg2 to instantly read/write real-time data 
    # instead of holding onto a stale "Snapshot" of the database.
    conn.autocommit = True 
    
    return conn

@st.cache_data(ttl=300)
def run_query(query, params=None):
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        return cur.fetchall()
    
def load_df(query, params=None):
    conn = get_connection()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def user_query(query, params=None, fetch=False):
    """
    Executes a SQL query safely using psycopg2
    :param query: SQL query string
    :param params: tuple of parameters for the query
    :param fetch: True if SELECT query and results need to be returned
    :return: list of dicts if fetch=True, else None
    """
    conn = None
    result = None
    try:
        conn = get_connection()
        # Using the imported RealDictCursor directly
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        if fetch:
            result = cur.fetchall()

        # With autocommit=True, explicit commits are handled automatically,
        # but leaving conn.commit() here is perfectly safe and backwards compatible.
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
    return result

def survey_solution_auth():
    """
    Authenticate to Survey Solutions server using API User credentials stored in st.secrets.
    Returns:
        session: requests.Session() authenticated with Basic Auth
        server: base server URL (cleaned of trailing slashes)
    """
    # 1. Load secrets and clean up slashes
    server = st.secrets["SURVEY_URL"].rstrip('/')
    workspace = st.secrets["API_Workspace"].strip('/')
    user = st.secrets["API_USER"]
    password = st.secrets["API_PASSWORD"]

    # 2. Create the session
    session = requests.Session()
    
    # 3. SET BASIC AUTHENTICATION (This is the correct way for SuSo API)
    session.auth = HTTPBasicAuth(user, password)

    # 4. Test the connection to ensure credentials and workspace are valid
    try:
        # We test by making a simple GET request to the questionnaires endpoint
        test_url = f"{server}/api/v1/questionnaires"
        headers = {"Workspace": workspace}
        
        r = session.get(test_url, headers=headers)
        
        # Raise an error if the request failed
        r.raise_for_status()
        
    except requests.exceptions.HTTPError as e:
        # Provide specific, helpful error messages based on the status code
        if e.response.status_code == 401:
            raise Exception("❌ Authentication failed: 401 Unauthorized. Please check your API_USER and API_PASSWORD.")
        elif e.response.status_code == 404:
            raise Exception(f"❌ Workspace not found: 404 Error. Please check if the workspace '{workspace}' is correct.")
        elif e.response.status_code == 403:
             raise Exception("❌ 403 Forbidden: Your API user does not have permission to access this workspace.")
        else:
            raise Exception(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
            
    except Exception as e:
        raise Exception(f"❌ Connection failed: {str(e)}")

    # Return the authenticated session, server URL, and workspace
    return session, server, workspace