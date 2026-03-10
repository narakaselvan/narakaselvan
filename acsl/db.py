import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
    )

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
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        if fetch:
            result = cur.fetchall()

        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
    return result