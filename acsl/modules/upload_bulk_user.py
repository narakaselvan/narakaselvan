import streamlit as st
import pandas as pd
import bcrypt 
from acsl.db import get_connection

def create_users():
    # -------------------------------
    # CREATE TABLE
    # -------------------------------
    def create_table():
        conn = get_connection()
        cur = conn.cursor()

        create_query = """
        CREATE TABLE IF NOT EXISTS susouser (
            login VARCHAR(100) PRIMARY KEY,
            password TEXT NOT NULL,
            role VARCHAR(100),
            supervisor VARCHAR(100),
            fullname VARCHAR(200),
            email VARCHAR(200),
            phonenumber VARCHAR(50),
            workspace VARCHAR(100),
            workingarea VARCHAR(100),
            is_active BOOLEAN
        );
        """

        cur.execute(create_query)
        conn.commit()
        cur.close()
        conn.close()

    # -------------------------------
    # HASH PASSWORD
    # -------------------------------
    def hash_password(password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    # -------------------------------
    # INSERT USERS
    # -------------------------------
    def insert_users(df):
        conn = get_connection()
        cur = conn.cursor()

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            try:
                hashed_pw = hash_password(str(row["password"]))

                insert_query = """
                INSERT INTO susouser 
                (login, password, role, supervisor, fullname, email, phonenumber, workspace, workingarea, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (login) DO NOTHING;
                """

                cur.execute(insert_query, (
                    row["login"],
                    hashed_pw,
                    row["role"],
                    row["supervisor"],
                    row["fullname"],
                    row["email"],
                    row["phonenumber"],
                    row["workspace"],
                    row["workingarea"],
                    row["is_active"]
                ))

                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1

            except Exception as e:
                st.error(f"Error inserting {row['login']}: {e}")

        conn.commit()
        cur.close()
        conn.close()

        return inserted, skipped

    # -------------------------------
    # STREAMLIT UI
    # -------------------------------
   
    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        User Upload to susouser Table
    </h1>
    """,
    unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Upload Excel / CSV / TSV file",
        type=["xlsx", "csv", "tsv"]
    )

    if uploaded_file:

        try:
            if uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, dtype={"is_active": bool})
            elif uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, dtype={"is_active": bool})
            else:
                df = pd.read_csv(uploaded_file, sep="\t", dtype={"is_active": bool})

            # Remove thousand separators if any
            #df["workingarea"] = df["workingarea"].astype(str).str.replace(",", "", regex=False)
            # Clean workingarea column safely
            if "workingarea" in df.columns:
                df["workingarea"] = (
                    df["workingarea"]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                    .replace("nan", "")
                )
            
            st.write("Preview:")
            st.dataframe(df.head())

            required_columns = [
                "login", "password", "role", "supervisor",
                "fullname", "email", "phonenumber", "workspace", "workingarea", "is_active"
            ]

            if not all(col in df.columns for col in required_columns):
                st.error("File does not contain required columns.")
            else:
                if st.button("Create Table & Upload Users"):
                    create_table()
                    inserted, skipped = insert_users(df)
                    st.success(f"Inserted: {inserted} users")
                    st.warning(f"Skipped (already exists): {skipped} users")

        except Exception as e:
            st.error(f"File processing error: {e}")