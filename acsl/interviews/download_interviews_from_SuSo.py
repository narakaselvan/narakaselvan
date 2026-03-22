# File: download_interviews_streamlit.py
import streamlit as st
import os
import time
import zipfile
from acsl.db import survey_solution_auth

def show_download_interviews_from_SuSo():
    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        📥 Survey Solutions Interview Downloader (HQ)
    </h1>
    """,
    unsafe_allow_html=True
    )

    # Inputs
    questionnaire_variable = "SriLanka_AgCensus2025"
    download_dir = "./interviews"

    if st.button("▶ Start Download"):
        os.makedirs(download_dir, exist_ok=True)

        # Authenticate
        try:
            session, server, workspace = survey_solution_auth()
            st.success("✅ Logged in successfully")
        except Exception as e:
            st.error(str(e))
            st.stop()

        # ---------------------------------------------------------
        # Step 1: Find the internal GUID & Version for your Questionnaire
        # ---------------------------------------------------------
        st.info("🔍 Locating questionnaire on server...")
        try:
            url_q = f"{server}/{workspace}/api/v1/questionnaires?qnVariables={questionnaire_variable}"
            r_q = session.get(url_q)
            r_q.raise_for_status()
            
            q_data = r_q.json()
            items = q_data.get("Questionnaires", q_data) if isinstance(q_data, dict) else q_data
            
            if not items:
                st.error(f"❌ Questionnaire with variable '{questionnaire_variable}' not found.")
                st.stop()
            
            # Extract both the GUID and the Version
            q_guid = items[0]["QuestionnaireId"]
            q_version = items[0]["Version"]
            
            # Combine them using the $ symbol as required by the Export API
            full_q_id = f"{q_guid}${q_version}"
            st.success(f"✅ Found Questionnaire: {full_q_id}")
            
        except Exception as e:
            st.error(f"Error fetching questionnaire: {str(e)}")
            st.stop()

        # ---------------------------------------------------------
        # Step 2: Ask the server to generate the Tabular Export ZIP
        # ---------------------------------------------------------
        st.info("⏳ Starting data export job on the server...")
        try:
            export_payload = {
                "ExportType": "Tabular", 
                "QuestionnaireId": full_q_id, 
                "InterviewStatus": "All" # You can change this to "ApprovedByHQ" etc.
            }
            
            url_export = f"{server}/{workspace}/api/v2/export"
            r_export = session.post(url_export, json=export_payload)
            
            # If we get a 400 Bad Request, let's print the actual server message!
            if r_export.status_code == 400:
                st.error(f"❌ Server rejected the request. Reason: {r_export.text}")
                st.stop()
                
            r_export.raise_for_status()
            job_id = r_export.json()["JobId"]
            
        except Exception as e:
            st.error(f"Error starting export: {str(e)}")
            st.stop()

        # ---------------------------------------------------------
        # Step 3: Wait for the server to finish preparing the ZIP
        # ---------------------------------------------------------
        st.info("🔄 Waiting for server to compile the data...")
        status_bar = st.progress(0)
        status_text = st.empty()
        
        job_url = f"{server}/{workspace}/api/v2/export/{job_id}"
        
        while True:
            r_job = session.get(job_url)
            r_job.raise_for_status()
            job_status = r_job.json()
            
            status = job_status.get("ExportStatus")
            progress = job_status.get("Progress", 0)
            
            status_bar.progress(int(progress))
            status_text.text(f"Status: {status} ({progress}%)")
            
            if status == "Completed":
                status_bar.progress(100)
                status_text.text("Status: Completed (100%)")
                break
            elif status in ["Failed", "Canceled", "FatalError"]:
                st.error(f"❌ Export failed on server with status: {status}")
                st.stop()
                
            time.sleep(3) # Wait 3 seconds before checking again

        # ---------------------------------------------------------
        # Step 4: Download the finalized ZIP file
        # ---------------------------------------------------------
        st.info("⬇️ Downloading the finalized ZIP file...")
        try:
            download_url = f"{server}/{workspace}/api/v2/export/{job_id}/file"
            r_file = session.get(download_url, stream=True)
            r_file.raise_for_status()
            
            zip_filename = f"{questionnaire_variable}_export.zip"
            zip_path = os.path.join(download_dir, zip_filename)
            
            with open(zip_path, "wb") as f:
                for chunk in r_file.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            st.success(f"✅ ZIP file downloaded to: {zip_path}")
            
            # ---------------------------------------------------------
            # Step 5: Automatically Unzip the Files
            # ---------------------------------------------------------
            st.info("📂 Extracting files...")
            
            # Create a specific folder for these extracted files
            extract_path = os.path.join(download_dir, f"{questionnaire_variable}_extracted_data")
            os.makedirs(extract_path, exist_ok=True)
            
            # Unzip everything into that folder
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
            st.success(f"✅ Files successfully unzipped to: {extract_path}")
            
            # Display the names of the files we just extracted!
            extracted_files = os.listdir(extract_path)
            st.write("**📄 Extracted Data Files:**")
            for file in extracted_files:
                st.text(file)
                
            # Keep the Streamlit download button so the user can still grab the ZIP from the browser if they want
            st.download_button(
                label="⬇ Download Final ZIP to Browser",
                data=open(zip_path, "rb").read(),
                file_name=zip_filename,
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"Error downloading or extracting file: {str(e)}")
            st.stop()