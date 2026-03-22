# file: interview_uploader.py

import streamlit as st
import pandas as pd
import os
import glob
from pathlib import Path
from psycopg2.extras import execute_values

from acsl.db import get_connection

# ---------------------------------------------------
# FIND LATEST INTERVIEW FOLDER
# ---------------------------------------------------

def get_latest_folder(base_path="./interviews"):

    folders = [f for f in Path(base_path).iterdir() if f.is_dir()]

    latest_folder = max(folders, key=os.path.getctime)

    return latest_folder


# ---------------------------------------------------
# LOAD TAB FILES
# ---------------------------------------------------

def load_tab_files(folder):

    files = glob.glob(os.path.join(folder, "*.tab"))

    data = {}

    for file in files:

        name = os.path.basename(file).replace(".tab", "")

        df = pd.read_csv(file, sep="\t")

        data[name] = df

    return data


# ---------------------------------------------------
# CREATE TABLE
# ---------------------------------------------------

def create_table_if_not_exists(conn, table_name, df):

    columns = []

    for col in df.columns:
        columns.append(f'"{col}" TEXT')

    column_sql = ",".join(columns)

    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {column_sql}
    );
    """

    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()


# ---------------------------------------------------
# UPSERT DATA
# ---------------------------------------------------

def upsert_dataframe(conn, table_name, df):

    cols = list(df.columns)

    columns = ",".join([f'"{c}"' for c in cols])

    values = [tuple(x) for x in df.to_numpy()]

    insert_sql = f"""
        INSERT INTO {table_name} ({columns})
        VALUES %s
    """

    cur = conn.cursor()

    execute_values(cur, insert_sql, values)

    conn.commit()

    cur.close()


# ---------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------

def show_upload_interviews_to_local_DB():

    st.title("📂 Interview TAB File Loader")

    # ------------------------------------------------

    latest_folder = get_latest_folder()

    st.success(f"Latest Interview Folder: {latest_folder}")

    data = load_tab_files(latest_folder)

    if len(data) == 0:
        st.warning("No TAB files found")
        return

    # ------------------------------------------------
    # SHOW FILES IN TABS
    # ------------------------------------------------

    tab_names = list(data.keys())

    tabs = st.tabs(tab_names)

    for i, name in enumerate(tab_names):

        with tabs[i]:

            st.subheader(name)

            st.dataframe(data[name], use_container_width=True)

            st.write(f"Rows: {len(data[name])}")

    # ------------------------------------------------
    # UPLOAD BUTTON
    # ------------------------------------------------

    if st.button("⬆ Upload to Local DB"):

        conn = get_connection()

        progress = st.progress(0)

        total = len(data)

        for i, (table_name, df) in enumerate(data.items()):

            st.write(f"Processing {table_name}")

            create_table_if_not_exists(conn, table_name, df)

            upsert_dataframe(conn, table_name, df)

            progress.progress((i + 1) / total)

        conn.close()

        st.success("Upload Completed")


# ---------------------------------------------------

if __name__ == "__main__":
    show_upload_interviews_to_local_DB()