import streamlit as st
import pandas as pd
from acsl.db import get_connection

# -----------------------------
# CONFIG
# -----------------------------

def show_interview_progress():

    ACTION_LABELS = {
        0: "SupervisorAssigned",
        1: "InterviewerAssigned",
        3: "Completed",
        4: "Restarted",
        5: "ApprovedBySupervisor",
        6: "ApprovedByHeadquarter",
        7: "RejectedBySupervisor",
        8: "RejectedByHeadquarter",
        11: "UnapprovedByHeadquarter",
        12: "Created",
        13: "InterviewReceivedByTablet",
        16: "TranslationSwitched",
        17: "OpenedBySupervisor",
        18: "ClosedBySupervisor",
        21: "InterviewReceivedBySupervisor"
    }

    conn = get_connection()
    current_user = st.session_state.get("login")

    # -----------------------------
    # USER WORKING AREA
    # -----------------------------
    @st.cache_data
    def get_user_working_area(user):
        return pd.read_sql(
            "SELECT workingarea FROM susouser WHERE login = %s",
            conn,
            params=(user,)
        ).iloc[0]["workingarea"]

    working_area = get_user_working_area(current_user)

    # -----------------------------
    # AREA LOGIC
    # -----------------------------
    def get_area_code(area):
        if area == "0000000":
            return "ALL", None
        elif area[1:] == "000000":
            return "PROVINCE", area[0]
        elif area[2:] == "00000":
            return "DISTRICT", area[:2]
        elif area[4:] == "000":
            return "DIVISION", area[:4]
        else:
            return "GN", area

    area_type, area_code = get_area_code(working_area)

    # -----------------------------
    # AREA NAME (HEADER)
    # -----------------------------
    def get_area_name():
        if area_type == "PROVINCE":
            q = "SELECT name FROM province WHERE code = %s"
        elif area_type == "DISTRICT":
            q = "SELECT name FROM district WHERE code = %s"
        elif area_type == "DIVISION":
            q = "SELECT name FROM division WHERE code = %s"
        elif area_type == "GN":
            q = "SELECT name FROM gndivision WHERE code = %s"
        else:
            return "Sri Lanka"

        df = pd.read_sql(q, conn, params=(area_code,))
        return df.iloc[0]["name"] if not df.empty else "Unknown"

    area_name = get_area_name()

    st.markdown(
        f"""
        <h1 style='text-align: left; color: darkgreen; font-size: 20px;'>
            📊 Interview Progress Dashboard - {area_name}
        </h1>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    @st.cache_data
    def load_data():
        query = """
            WITH latest_actions AS (
                SELECT 
                    interview__key,
                    action,
                    responsible__name,
                    ROW_NUMBER() OVER (
                        PARTITION BY interview__key 
                        ORDER BY TO_DATE(date, 'YYYY-MM-DD') DESC, time::time DESC
                    ) AS rn
                FROM interview__actions
            )

            SELECT 
                la.interview__key,
                la.action,
                la.responsible__name,
                a.preload_a0,
                a.preload_a01,
                su.workingarea
            FROM latest_actions la

            LEFT JOIN srilanka_agcensus2025 ag
                ON la.interview__key = ag.interview__key

            LEFT JOIN assignments a
                ON ag.assignment__id::bigint = a.meta_id

            LEFT JOIN susouser su
                ON la.responsible__name = su.login

            WHERE la.rn = 1;
        """
        return pd.read_sql(query, conn)

    df = load_data()

    # -----------------------------
    # FILTER AREA
    # -----------------------------
    def filter_area(df):
        if area_type == "ALL":
            return df
        if area_type == "PROVINCE":
            return df[df["workingarea"].str[:1] == area_code]
        if area_type == "DISTRICT":
            return df[df["workingarea"].str[:2] == area_code]
        if area_type == "DIVISION":
            return df[df["workingarea"].str[:4] == area_code]
        return df[df["workingarea"] == area_code]

    df = filter_area(df)

    # -----------------------------
    # BLOCK DROPDOWN
    # -----------------------------
    df["block"] = df["preload_a0"].astype(str) + df["preload_a01"].fillna("").astype(str)

    block_list = sorted(df["block"].dropna().unique())
    selected_block = st.selectbox("Select Block", ["All"] + block_list)

    if selected_block != "All":
        df = df[df["block"] == selected_block]

    # -----------------------------
    # STATUS MAPPING
    # -----------------------------
    df["action"] = pd.to_numeric(df["action"], errors="coerce")
    df["status"] = df["action"].map(ACTION_LABELS)

    # -----------------------------
    # SUMMARY
    # -----------------------------
    summary = df["status"].value_counts().reindex(ACTION_LABELS.values(), fill_value=0)

    st.subheader("Overall Status Counts")

    cols = st.columns(5)
    for i, (status, count) in enumerate(summary.items()):
        cols[i % 5].metric(status, int(count))

    # -----------------------------
    # LOAD AREA NAMES
    # -----------------------------
    @st.cache_data
    def load_area_names(area_type):
        if area_type == "ALL":
            return pd.read_sql("SELECT code, name FROM province", conn)
        elif area_type == "PROVINCE":
            return pd.read_sql("SELECT code, name FROM district", conn)
        elif area_type == "DISTRICT":
            return pd.read_sql("SELECT code, name FROM division", conn)
        elif area_type == "DIVISION":
            return pd.read_sql("SELECT code, name FROM gndivision", conn)
        return None

    # -----------------------------
    # AREA BREAKDOWN WITH NAMES
    # -----------------------------
    st.subheader("Area-wise Breakdown")

    if area_type == "ALL":
        df["area_code"] = df["workingarea"].str[:1]
    elif area_type == "PROVINCE":
        df["area_code"] = df["workingarea"].str[:2]
    elif area_type == "DISTRICT":
        df["area_code"] = df["workingarea"].str[:4]
    else:
        df["area_code"] = df["workingarea"]

    area_names_df = load_area_names(area_type)

    if area_names_df is not None:
        area_names_df["code"] = area_names_df["code"].astype(str)
        df["area_code"] = df["area_code"].astype(str)

        area_map = dict(zip(area_names_df["code"], area_names_df["name"]))
        df["area"] = df["area_code"].map(area_map)
    else:
        df["area"] = df["area_code"]

    # -----------------------------
    # PIVOT TABLE
    # -----------------------------
    pivot = pd.pivot_table(
        df,
        index="area",
        columns="status",
        aggfunc="size",
        fill_value=0
    )

    st.dataframe(pivot, use_container_width=True)