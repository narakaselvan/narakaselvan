
import streamlit as st
import requests
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
import math

def show_download_interviews_from_SuSo():
    # --------------------------
    # Streamlit UI
    # --------------------------
    st.title("📥 Survey Solutions: Download All Interviews")

    server = st.secrets["SURVEY_URL"]
    workspace = st.secrets["API_Workspace"]
    user = st.secrets["API_USER"]
    password = st.secrets["API_PASSWORD"]
    questionnaire_variable = st.secrets["questionniare_variable"]
    download_dir = st.text_input("Download Directory", "D:/Nonagri/Download")
    if st.button("▶ Start Download"):

        os.makedirs(download_dir, exist_ok=True)
        session = requests.Session()

        # --------------------------
        # Authenticate
        # --------------------------
        try:
            auth_payload = {"UserName": user, "Password": password, "Tenant": workspace}
            r = session.post(f"{server}/api/v1/login", json=auth_payload)
            r.raise_for_status()
            st.success("✅ Logged in successfully")
        except requests.exceptions.HTTPError as e:
            st.error(f"HTTP Error {e.response.status_code} - {e.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            st.stop()

        # --------------------------
        # Fetch questionnaires
        # --------------------------
        r = session.get(f"{server}/api/v1/questionnaires")
        r.raise_for_status()
        data = r.json()
        questionnaires = [q for q in data.get("Questionnaires", []) if questionnaire_variable.lower() in q.get("Variable", "").lower()]

        if not questionnaires:
            st.warning("No questionnaire found with this variable")
            st.stop()

        qnr = questionnaires[0]
        qnr_id = qnr["QuestionnaireId"]
        st.write(f"Selected questionnaire: {qnr['Title']} (v{qnr['Version']})")

        # --------------------------
        # Fetch all interview IDs in batches
        # --------------------------
        st.info("Fetching interview IDs...")

        all_interview_ids = []
        skip = 0
        take = 100  # batch size
        while True:
            url = f"{server}/api/v1/interviews?questionnaireVariable={questionnaire_variable}&skip={skip}&take={take}"
            r = session.get(url)
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            for i in batch:
                all_interview_ids.append(i["Id"])
            skip += len(batch)

        total_interviews = len(all_interview_ids)
        if total_interviews == 0:
            st.warning("No interviews found")
            st.stop()
        st.success(f"✅ Found {total_interviews} interviews")

        # --------------------------
        # Download full interviews in parallel
        # --------------------------
        st.info("Downloading full interview data...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []

        def download_full(iid):
            try:
                r = session.get(f"{server}/api/v1/interviews/{iid}?format=json")
                r.raise_for_status()
                return r.json()
            except Exception as e:
                return {"error": str(e), "id": iid}

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(download_full, iid): iid for iid in all_interview_ids}
            for count, future in enumerate(as_completed(futures), 1):
                res = future.result()
                results.append(res)
                progress_bar.progress(int(count / total_interviews * 100))
                status_text.text(f"Downloading interviews: {count}/{total_interviews}")

        st.success("✅ All interviews downloaded")

        # --------------------------
        # Extract main + roster tables
        # --------------------------
        st.info("Extracting main + roster tables...")

        main_rows = []
        roster_rows = {}

        for interview in results:
            if "error" in interview:
                st.warning(f"Skipping failed interview {interview.get('id')}: {interview['error']}")
                continue

            main_row = {"InterviewId": interview.get("Id"), "Status": interview.get("Status")}
            answers = interview.get("Answers", {})
            for k, v in answers.items():
                if isinstance(v, list):
                    if k not in roster_rows:
                        roster_rows[k] = []
                    for item in v:
                        row = {"InterviewId": interview.get("Id")}
                        if isinstance(item, dict):
                            for kk, vv in item.items():
                                row[kk] = vv
                        else:
                            row["Value"] = item
                        roster_rows[k].append(row)
                else:
                    main_row[k] = v
            main_rows.append(main_row)

        # --------------------------
        # Save CSVs and ZIP
        # --------------------------
        zip_path = os.path.join(download_dir, f"{questionnaire_variable}_interviews.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            if main_rows:
                df_main = pd.DataFrame(main_rows)
                main_csv = os.path.join(download_dir, f"{questionnaire_variable}_main.csv")
                df_main.to_csv(main_csv, index=False)
                zipf.write(main_csv, arcname=f"{questionnaire_variable}_main.csv")
            for roster_name, rows in roster_rows.items():
                if rows:
                    df_roster = pd.DataFrame(rows)
                    roster_csv = os.path.join(download_dir, f"{questionnaire_variable}_roster_{roster_name}.csv")
                    df_roster.to_csv(roster_csv, index=False)
                    zipf.write(roster_csv, arcname=f"{questionnaire_variable}_roster_{roster_name}.csv")

        st.success(f"✅ Completed! All CSVs saved and zipped at {zip_path}")

        st.download_button(
            label="⬇ Download ZIP",
            data=open(zip_path, "rb").read(),
            file_name=os.path.basename(zip_path),
            mime="application/zip"
        )