import streamlit as st
import os, requests, time, json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_assignments():
    # -------------------------
    # CONFIGURATION
    # -------------------------
    SS_URL = st.secrets["SURVEY_URL"]
    AUTH = (st.secrets["API_USER"], st.secrets["API_PASSWORD"])
    API_WORKSPACE = "agriculture"

    PAGE_SIZE = 1000
    MAX_WORKERS = 6
    TIMEOUT = 60
    CHUNK_SIZE = 5000

    OUTPUT_DIR = "exports"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    EXCEL_FILE = f"{OUTPUT_DIR}/assignments_FULL_export.xlsx"

    # -------------------------
    # API FUNCTIONS
    # -------------------------

    def get_assignment_ids():
        ids = []
        offset = 0
        while True:
            r = requests.get(
            f"{SS_URL}/api/v1/assignments",
            auth=AUTH,
            params={
                "offset": offset,
                "limit": PAGE_SIZE,
                "workspace": API_WORKSPACE
            },
            timeout=TIMEOUT
            )
            r.raise_for_status()

            batch = r.json().get("Assignments", [])
            if not batch:
                break

            ids.extend(a["Id"] for a in batch)
            offset += PAGE_SIZE

        return ids


    def get_assignment_details(aid):
        r = requests.get(
            f"{SS_URL}/api/v1/assignments/{aid}",
            auth=AUTH,
            params={"workspace": API_WORKSPACE},
            timeout=TIMEOUT
            )
        r.raise_for_status()
        return r.json()

    # -------------------------
    # NORMALIZATION
    # -------------------------
    def normalize_value(v):
        if v is None:
            return ""
        if isinstance(v, (str, int, float, bool)):
            return v
        if isinstance(v, (list, dict)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)


    def extract_metadata(data):
        """
        Extract ALL top-level metadata fields dynamically
        """
        meta = {}
        for key, value in data.items():
            if key not in ["Answers", "IdentifyingData"]:
                meta[f"meta_{key}"] = normalize_value(value)
        return meta


    def extract_preloaded(data):
        """
        Extract all preloaded values (IdentifyingData)
        """
        preload = {}
        identifying = data.get("IdentifyingData", [])
        for item in identifying:
            var = item.get("Variable")
            val = normalize_value(item.get("Answer"))
            preload[f"preload_{var}"] = val
        return preload

    def extract_answers(data):
        """
        Extract all assignment variables
        """
        ans = {}
        for a in data.get("Answers", []):
            var = a.get("Variable")
            val = normalize_value(a.get("Answer"))
            ans[f"var_{var}"] = val
        return ans

    # -------------------------
    # STREAMLIT UI
    # -------------------------
    st.markdown(
    """
    <h1 style='text-align: center; color: maroon; font-size: 15px;'>
        Bulk Assignments Exportor
    </h1>
    """,
    unsafe_allow_html=True
    )

    st.warning("""
    ✔ Exports ALL assignment metadata  
    ✔ Exports ALL preloaded values  
    """)

    if st.button("Start Download"):
        status = st.empty()
        progress = st.progress(0.0)

        # STEP 1 – GET IDS
        status.info("Fetching assignment IDs...")
        assignment_ids = get_assignment_ids()
        total = len(assignment_ids)

        if total == 0:
            st.error("No assignments found.")
            st.stop()

        st.success(f"Total assignments: {total:,}")

        writer = pd.ExcelWriter(EXCEL_FILE, engine="openpyxl")
        current_chunk = []
        written_rows = 0
        completed = 0
        start_time = time.time()

        all_columns = set()

        # STEP 2 – PARALLEL DOWNLOAD
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(get_assignment_details, aid): aid for aid in assignment_ids}

            for future in as_completed(futures):
                try:
                    data = future.result()

                    row = {}
                    row.update(extract_metadata(data))
                    row.update(extract_preloaded(data))
                    row.update(extract_answers(data))

                    all_columns.update(row.keys())
                    current_chunk.append(row)

                    completed += 1

                    # WRITE IN CHUNKS
                    if len(current_chunk) >= CHUNK_SIZE:
                        df_chunk = pd.DataFrame(current_chunk)
                        df_chunk = df_chunk.reindex(columns=sorted(all_columns))
                        df_chunk.to_excel(
                            writer,
                            index=False,
                            startrow=written_rows,
                            header=(written_rows == 0)
                        )
                        written_rows += len(df_chunk)
                        current_chunk = []

                    if completed % 100 == 0:
                        progress.progress(completed / total)
                        status.info(f"{completed:,} / {total:,} processed")

                except Exception as e:
                    st.error(f"Error: {e}")

        # WRITE REMAINING
        if current_chunk:
            df_chunk = pd.DataFrame(current_chunk)
            df_chunk = df_chunk.reindex(columns=sorted(all_columns))
            df_chunk.to_excel(
                writer,
                index=False,
                startrow=written_rows,
                header=(written_rows == 0)
            )

        writer.close()

        duration = (time.time() - start_time) / 60
        progress.progress(1.0)
        status.success(f"✅ Completed in {duration:.1f} minutes")

        with open(EXCEL_FILE, "rb") as f:
            st.download_button(
            "Download FULL Excel File",
            f,
            file_name="assignments_FULL_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
