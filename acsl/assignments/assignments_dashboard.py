import streamlit as st
import sys
import os
import pandas as pd

# -------------------------------------------------
# PATH FIX
# -------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from acsl.db import get_connection

# -------------------------------------------------
# WORKING AREA FUNCTIONS
# -------------------------------------------------
def normalize_working_area(wa):
    if str(wa) == "0":
        return "0000000"
    return str(wa).zfill(7)

def build_area_filter(current_wa):
    current_wa = normalize_working_area(current_wa)
    if current_wa == "0000000":
        return "1=1", []
    prefix = current_wa.rstrip("0")
    return "workingarea LIKE %s", [prefix + "%"]

# -------------------------------------------------
# AREA LEVEL DETECTION
# -------------------------------------------------
def get_area_level(wa):
    wa = normalize_working_area(wa)

    if wa == "0000000":
        return "island"
    elif wa[1:] == "000000":
        return "province"
    elif wa[2:] == "00000":
        return "district"
    elif wa[4:] == "000":
        return "division"
    else:
        return "gn"

def get_next_level_length(level):
    mapping = {
        "island": 1,
        "province": 2,
        "district": 4,
        "division": 7
    }
    return mapping.get(level, 7)

# -------------------------------------------------
# AREA-WISE PROGRESS
# -------------------------------------------------
def show_area_wise_progress(conn, current_wa):
    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        📊 Area-wise Progress
    </h1>
    """,
    unsafe_allow_html=True
    )

    level = get_area_level(current_wa)

    # --------------------------------------------
    # LEVEL SELECTION
    # --------------------------------------------
    if level == "island":
        view_option = st.selectbox(
            "Select Summary Level",
            ["Province Wise", "District Wise"]
        )
        prefix_len = 1 if view_option == "Province Wise" else 2
    else:
        prefix_len = get_next_level_length(level)

    # --------------------------------------------
    # USERS
    # --------------------------------------------
    area_condition, area_params = build_area_filter(current_wa)

    df_users = pd.read_sql(
        f"SELECT login, role, workingarea FROM susouser WHERE {area_condition}",
        conn, params=area_params
    )

    if df_users.empty:
        st.warning("No data available")
        return

    df_users["role_clean"] = df_users["role"].str.lower().str.strip()
    df_users["area_group"] = df_users["workingarea"].astype(str).str[:prefix_len]

    # --------------------------------------------
    # LOAD AREA NAMES
    # --------------------------------------------
    if prefix_len == 1:
        df_names = pd.read_sql("SELECT code, name FROM province", conn)
    elif prefix_len == 2:
        df_names = pd.read_sql("SELECT code, name FROM district", conn)
    elif prefix_len == 4:
        df_names = pd.read_sql("SELECT code, name FROM division", conn)
    elif prefix_len == 7:
        df_names = pd.read_sql("SELECT code, name FROM gndivision", conn)
    else:
        df_names = pd.DataFrame(columns=["code", "name"])

    df_names["code"] = df_names["code"].astype(str)

    # --------------------------------------------
    # USER SUMMARY
    # --------------------------------------------
    summary = df_users.groupby("area_group").agg(
        supervisors=("role_clean", lambda x: (x == "supervisor").sum()),
        interviewers=("role_clean", lambda x: (x == "interviewer").sum())
    ).reset_index()

    # Merge names
    summary = summary.merge(
        df_names,
        left_on="area_group",
        right_on="code",
        how="left"
    )

    summary.rename(columns={"name": "area_name"}, inplace=True)

    # ❌ REMOVE UNKNOWN AREAS
    summary = summary[summary["area_name"].notna()]

    if summary.empty:
        st.warning("No mapped areas found")
        return

    # --------------------------------------------
    # KPI FUNCTION
    # --------------------------------------------
    def get_counts(area_prefix):
        like_pattern = area_prefix + "%"

        supervisors = pd.read_sql(
            "SELECT login FROM susouser WHERE workingarea LIKE %s AND LOWER(role)='supervisor'",
            conn, params=[like_pattern]
        )["login"].tolist()

        interviewers = pd.read_sql(
            "SELECT login FROM susouser WHERE workingarea LIKE %s AND LOWER(role)='interviewer'",
            conn, params=[like_pattern]
        )["login"].tolist()

        sup_assignments = 0
        if supervisors:
            sup_assignments = pd.read_sql("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT ON (assignment__id) assignment__id
                    FROM assignment__actions
                    WHERE responsible__name = ANY(%s)
                    ORDER BY assignment__id,
                    (TO_DATE(date, 'YYYY-MM-DD') + time::time) DESC
                ) t
            """, conn, params=(supervisors,)).iloc[0,0]

        received = 0
        if interviewers:
            received = pd.read_sql("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT ON (assignment__id) assignment__id
                    FROM assignment__actions
                    WHERE action = '4'
                    AND responsible__name = ANY(%s)
                    ORDER BY assignment__id,
                    (TO_DATE(date, 'YYYY-MM-DD') + time::time) DESC
                ) t
            """, conn, params=(interviewers,)).iloc[0,0]

        reassigned = 0
        if supervisors:
            reassigned = pd.read_sql("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT ON (assignment__id) assignment__id
                    FROM assignment__actions
                    WHERE action = '7'
                    AND originator = ANY(%s)
                    ORDER BY assignment__id,
                    (TO_DATE(date, 'YYYY-MM-DD') + time::time) DESC
                ) t
            """, conn, params=(supervisors,)).iloc[0,0]

        return sup_assignments, received, reassigned

    # --------------------------------------------
    # BUILD RESULT
    # --------------------------------------------
    results = []
    for _, row in summary.iterrows():
        area = row["area_group"]
        area_name = row["area_name"]

        sup_assign, rec, reas = get_counts(area)

        results.append({
            "Area Code": area,
            "Area Name": area_name,
            "Supervisors": row["supervisors"],
            "Interviewers": row["interviewers"],
            "Assignments (Sup)": sup_assign,
            "Received (Int)": rec,
            "Reassigned": reas
        })

    df_result = pd.DataFrame(results)

    # --------------------------------------------
    # TOTAL ROW
    # --------------------------------------------
    total_values = df_result.select_dtypes(include='number').sum()
    total_row = pd.DataFrame([total_values])
    total_row["Area Code"] = ""
    total_row["Area Name"] = "TOTAL"

    df_result = pd.concat([df_result, total_row], ignore_index=True)

    # --------------------------------------------
    # DISPLAY
    # --------------------------------------------
    st.dataframe(df_result, use_container_width=True)

# -------------------------------------------------
# MAIN DASHBOARD
# -------------------------------------------------
def show_assignment_dashboard():
    st.markdown(
    """
    <h1 style='text-align: center; color: darkgreen; font-size: 20px;'>
        📊 Assignment Monitoring Dashboard
    </h1>
    """,
    unsafe_allow_html=True
    )

    conn = get_connection()
    current_user = st.session_state.get("user")

    df_user = pd.read_sql(
        "SELECT workingarea, role FROM susouser WHERE login = %s",
        conn, params=[current_user]
    )

    if df_user.empty:
        st.error("User not found")
        st.stop()

    current_wa = df_user.iloc[0]["workingarea"]
    current_role = df_user.iloc[0]["role"]

    #st.sidebar.success(f"👤 {current_user} ({current_role})")

    area_condition, area_params = build_area_filter(current_wa)

    df_users = pd.read_sql(
        f"SELECT login, role FROM susouser WHERE {area_condition}",
        conn, params=area_params
    )

    df_users["role_clean"] = df_users["role"].str.lower().str.strip()

    supervisors = df_users[df_users["role_clean"] == "supervisor"]["login"].tolist()
    interviewers = df_users[df_users["role_clean"] == "interviewer"]["login"].tolist()

    supervisor_count = 1 if current_role.lower() == "supervisor" else len(supervisors)
    interviewer_count = len(interviewers)

    sup_assignments = 0
    if supervisors:
        sup_assignments = pd.read_sql("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT ON (assignment__id) assignment__id
                FROM assignment__actions
                WHERE responsible__name = ANY(%s)
                ORDER BY assignment__id,
                (TO_DATE(date, 'YYYY-MM-DD') + time::time) DESC
            ) t
        """, conn, params=(supervisors,)).iloc[0,0]

    assigned_to_int = 0
    received_int = 0

    if interviewers:
        assigned_to_int = pd.read_sql("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT ON (assignment__id) assignment__id
                FROM assignment__actions
                WHERE action = '4'
                AND responsible__name = ANY(%s)
                ORDER BY assignment__id,
                (TO_DATE(date, 'YYYY-MM-DD') + time::time) DESC
            ) t
        """, conn, params=(interviewers,)).iloc[0,0]

        received_int = assigned_to_int

    reassigned = 0
    if supervisors:
        reassigned = pd.read_sql("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT ON (assignment__id) assignment__id
                FROM assignment__actions
                WHERE action = '7'
                AND originator = ANY(%s)
                ORDER BY assignment__id,
                (TO_DATE(date, 'YYYY-MM-DD') + time::time) DESC
            ) t
        """, conn, params=(supervisors,)).iloc[0,0]

    col1, col2, col3 = st.columns(3)
    col1.metric("👨‍💼 Supervisors", supervisor_count)
    col2.metric("🧑‍💻 Interviewers", interviewer_count)
    col3.metric("📦 Assignments with Supervisors", sup_assignments)

    col4, col5, col6 = st.columns(3)
    col4.metric("📤 Assigned to Interviewers", assigned_to_int)
    col5.metric("📥 Received by Interviewers", received_int)
    col6.metric("🔁 Reassigned Assignments", reassigned)

    # NEW FEATURE
    show_area_wise_progress(conn, current_wa)

# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":
    show_assignment_dashboard()