import streamlit as st
import pandas as pd
import bcrypt 
import io
import sys
import os

# -------------------------------------------------
# PATH FIX (Must be before 'from acsl...' imports)
# -------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from acsl.db import get_connection

# Attempt to import msoffcrypto for password-protected Excel files
try:
    import msoffcrypto
except ImportError:
    st.error("⚠️ The `msoffcrypto-tool` library is not installed. Please run `pip install msoffcrypto-tool` in your terminal.")
    st.stop()

def create_users():
    # -------------------------------
    # 1. CREATE TABLE FUNCTION
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
    # 🌟 RUN TABLE CREATION IMMEDIATELY 🌟
    # -------------------------------
    try:
        create_table()
    except Exception as e:
        st.error(f"Critical Database Error: Could not verify or create 'susouser' table. Details: {e}")
        st.stop()

    # -------------------------------
    # 2. HASH PASSWORD FUNCTION
    # -------------------------------
    def hash_password(password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    # -------------------------------
    # 3. INSERT USERS FUNCTION
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
                conn.rollback() 
                st.error(f"Error inserting {row['login']}: {e}")

        conn.commit()
        cur.close()
        conn.close()

        return inserted, skipped

    # -------------------------------
    # 4. STREAMLIT UI
    # -------------------------------
   
    st.markdown(
        """
        <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
            User Upload to susouser Table
        </h1>
        <p style='text-align: center; color: gray; font-size: 14px;'>
            <i>Note: The admin user is handled separately.</i>
        </p>
        """,
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Upload Excel / CSV / TSV file",
        type=["xlsx", "csv", "tsv"]
    )

    if uploaded_file:
        
        # Determine file extension
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        # If Excel, show password prompt
        file_password = None
        if file_ext == "xlsx":
            file_password = st.text_input("🔒 Excel File Password (leave blank if not protected):", type="password")

        # Process the file
        df = None
        try:
            if file_ext == "xlsx":
                file_to_read = uploaded_file
                
                # If a password was provided, decrypt the file into memory first
                if file_password:
                    decrypted_workbook = io.BytesIO()
                    office_file = msoffcrypto.OfficeFile(uploaded_file)
                    office_file.load_key(password=file_password)
                    office_file.decrypt(decrypted_workbook)
                    
                    # Reset the file pointer for Pandas
                    decrypted_workbook.seek(0)
                    file_to_read = decrypted_workbook
                
                # Load the decrypted (or standard) Excel file
                df = pd.read_excel(file_to_read, dtype={"is_active": bool})
                
            elif file_ext == "csv":
                df = pd.read_csv(uploaded_file, dtype={"is_active": bool})
            else:
                df = pd.read_csv(uploaded_file, sep="\t", dtype={"is_active": bool})

        except msoffcrypto.exceptions.InvalidKeyError:
            st.error("❌ Incorrect password provided for the Excel file.")
            return
        except Exception as e:
            if "encrypted" in str(e).lower() or "compdoc" in str(e).lower() or "supported" in str(e).lower():
                st.warning("🔒 This Excel file appears to be password-protected. Please enter the password in the box above.")
            else:
                st.error(f"File reading error: {e}")
            return

        # --- DATA VALIDATION & CLEANING ---
        if df is not None:
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
                st.error(f"File does not contain all required columns. Missing: {list(set(required_columns) - set(df.columns))}")
            else:
                # Changed button text since the table is already created automatically!
                if st.button("Upload Users to Database", type="primary"):
                    with st.spinner("Processing users..."):
                        inserted, skipped = insert_users(df)
                        st.success(f"✅ Inserted: {inserted} users")
                        if skipped > 0:
                            st.warning(f"⚠️ Skipped (already exists): {skipped} users")

if __name__ == "__main__":
    create_users()
    