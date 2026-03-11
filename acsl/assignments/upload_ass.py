import streamlit as st
import pandas as pd
import math
from psycopg2.extras import execute_batch
from acsl.db import get_connection

def upload_assignments():

    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        📥 Bulk Assignments Uploader
    </h1>
    """,
    unsafe_allow_html=True
    )

    # -------------------------------
    # REQUIRED COLUMNS
    # -------------------------------
    REQUIRED_COLUMNS = [
        "meta_Archived","meta_CreatedAtUtc","meta_Email","meta_Id",
        "meta_InterviewsCount","meta_IsAudioRecordingEnabled",
        "meta_Password","meta_Quantity","meta_QuestionnaireId",
        "meta_ReceivedByTabletAtUtc","meta_ResponsibleId",
        "meta_ResponsibleName","meta_TargetArea","meta_UpdatedAtUtc",
        "meta_WebMode","preload_A0","preload_A01","preload_A10",
        "preload_A11a","preload_A11b","preload_A12a","preload_A12b",
        "preload_A13","preload_A14a","preload_A15","preload_A1a",
        "preload_A1b","preload_A2a","preload_A2b","preload_A3a",
        "preload_A3b","preload_B7","preload_B8"
    ]

    NUMERIC_COLUMNS = [
        "meta_Id",
        "meta_InterviewsCount",
        "meta_Quantity",
        "preload_A15",
        "preload_A1b",
        "preload_A2b",
        "preload_A3b"
    ]

    DATETIME_COLUMNS = [
        "meta_CreatedAtUtc",
        "meta_ReceivedByTabletAtUtc",
        "meta_UpdatedAtUtc"
    ]

    # -------------------------------
    # SAFE VALUE CLEANER
    # -------------------------------
    def clean_value(value):
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    # -------------------------------
    # CREATE TABLE
    # -------------------------------
    def create_table(conn):
        query = """
        CREATE TABLE IF NOT EXISTS assignments (
            meta_Archived TEXT,
            meta_CreatedAtUtc TIMESTAMP,
            meta_Email TEXT,
            meta_Id BIGINT PRIMARY KEY,
            meta_InterviewsCount BIGINT,
            meta_IsAudioRecordingEnabled BOOLEAN,
            meta_Password TEXT,
            meta_Quantity BIGINT,
            meta_QuestionnaireId TEXT,
            meta_ReceivedByTabletAtUtc TIMESTAMP,
            meta_ResponsibleId TEXT,
            meta_ResponsibleName TEXT,
            meta_TargetArea TEXT,
            meta_UpdatedAtUtc TIMESTAMP,
            meta_WebMode BOOLEAN,
            preload_A0 TEXT,
            preload_A01 TEXT,
            preload_A10 TEXT,
            preload_A11a TEXT,
            preload_A11b TEXT,
            preload_A12a TEXT,
            preload_A12b TEXT,
            preload_A13 TEXT,
            preload_A14a TEXT,
            preload_A15 BIGINT,
            preload_A1a TEXT,
            preload_A1b BIGINT,
            preload_A2a TEXT,
            preload_A2b BIGINT,
            preload_A3a TEXT,
            preload_A3b BIGINT,
            preload_B7 TEXT,
            preload_B8 TEXT
        );
        """
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        cur.close()

    # -------------------------------
    # FILE UPLOAD
    # -------------------------------
    uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])

    if uploaded_file:

        try:
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            st.success(f"Excel Loaded Successfully! Total Rows: {len(df)}")

            # Keep required columns only
            df = df[[c for c in REQUIRED_COLUMNS if c in df.columns]]

            if "meta_Id" not in df.columns:
                st.error("meta_Id column is required.")
                st.stop()

            # Remove duplicates inside Excel
            duplicate_excel = df[df.duplicated(subset=["meta_Id"], keep="first")]
            df = df.drop_duplicates(subset=["meta_Id"], keep="first")

            if not duplicate_excel.empty:
                st.warning(f"{len(duplicate_excel)} duplicate rows ignored from Excel.")
                st.dataframe(duplicate_excel)

            # Convert numeric
            for col in NUMERIC_COLUMNS:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Convert datetime
            for col in DATETIME_COLUMNS:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            # -------------------------------
            # INSERT INTO DATABASE
            # -------------------------------
            conn = get_connection()
            conn.autocommit = False
            create_table(conn)

            cur = conn.cursor()

            columns = list(df.columns)

            insert_query = f"""
            INSERT INTO assignments ({", ".join(columns)})
            VALUES ({", ".join(["%s"] * len(columns))})
            ON CONFLICT (meta_Id) DO NOTHING;
            """

            # Clean data row by row (THIS FIXES NaT 100%)
            data = []
            for _, row in df.iterrows():
                cleaned_row = tuple(clean_value(v) for v in row)
                data.append(cleaned_row)

            execute_batch(cur, insert_query, data, page_size=1000)

            conn.commit()

            st.success(f"✅ Upload complete! {len(df)} unique rows processed.")

            cur.close()
            conn.close()

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            st.error(f"❌ Error: {e}")