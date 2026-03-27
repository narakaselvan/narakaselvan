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

def get_area_level(wa):
    wa = normalize_working_area(wa)
    if wa == "0000000": return "island"
    elif wa[1:] == "000000": return "province"
    elif wa[2:] == "00000": return "district"
    elif wa[4:] == "000": return "division"
    else: return "gn"

def get_next_level_length(level):
    mapping = {"island": 1, "province": 2, "district": 4, "division": 7}
    return mapping.get(level, 7)

# -------------------------------------------------
# FETCH DATA EFFICIENTLY (SINGLE DATABASE HIT)
# -------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60)
def fetch_dashboard_data(prefix):
    conn = get_connection()
    try:
        # 1. Fetch Users
        sql_users = """
        SELECT login, LOWER(role) AS role, workingarea 
        FROM susouser 
        WHERE workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = ''
        """
        df_users = pd.read_sql(sql_users, conn, params={'prefix': prefix})

        # 2. Fetch Assignments (STRICTLY FROM assignments TABLE)
        sql_assign = """
        WITH LatestAssign AS (
            -- Get the absolute latest status and owner of the assignment
            SELECT assignment__id, responsible__name, action,
                   ROW_NUMBER() OVER(PARTITION BY assignment__id ORDER BY "date" DESC, "time" DESC) as rn
            FROM assignment__actions
            WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
        ),
        ReassignedStats AS (
            -- Check if it was ever reassigned by a supervisor (Action 7)
            SELECT DISTINCT aa.assignment__id 
            FROM assignment__actions aa
            JOIN susouser su ON aa.originator = su.login
            WHERE aa.action = '7' AND LOWER(su.role) = 'supervisor'
        )
        SELECT 
            a.meta_id AS assignment_id, 
            LOWER(su.role) AS current_role,
            la.action AS latest_action,
            su.workingarea,
            CASE WHEN rs.assignment__id IS NOT NULL THEN 1 ELSE 0 END AS is_reassigned
        FROM assignments a
        -- INNER JOIN ensures we ONLY count assignments that physically exist in the assignments table
        JOIN LatestAssign la ON a.meta_id::VARCHAR = la.assignment__id::VARCHAR AND la.rn = 1
        JOIN susouser su ON la.responsible__name = su.login
        LEFT JOIN ReassignedStats rs ON a.meta_id::VARCHAR = rs.assignment__id::VARCHAR
        WHERE su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = ''
        """
        df_assign = pd.read_sql(sql_assign, conn, params={'prefix': prefix})
        
        # 3. Fetch Area Names based on the required tables
        names_dict = {
            1: pd.read_sql("SELECT code::VARCHAR, name FROM province", conn),
            2: pd.read_sql("SELECT code::VARCHAR, name FROM district", conn),
            4: pd.read_sql("SELECT code::VARCHAR, name FROM division", conn),
            7: pd.read_sql("SELECT code::VARCHAR, name FROM gndivision", conn)
        }
        
        return df_users, df_assign, names_dict
    finally:
        conn.close()


# -------------------------------------------------
# MAIN DASHBOARD
# -------------------------------------------------
def show_assignment_dashboard():
    st.markdown(
        """
        <h1 style='text-align: center; color: darkgreen; font-size: 24px;'>
            📊 Assignment Monitoring Dashboard
        </h1>
        <hr>
        """,
        unsafe_allow_html=True
    )

    current_user = st.session_state.get("login") # Assuming session state holds 'login'
    if not current_user:
        st.warning("Please login first.")
        return

    # Fetch Logged-in User's Area
    conn = get_connection()
    try:
        df_user = pd.read_sql("SELECT workingarea, role FROM susouser WHERE login = %s", conn, params=[current_user])
    finally:
        conn.close()

    if df_user.empty:
        st.error("User not found in database.")
        return

    current_wa = normalize_working_area(df_user.iloc[0]["workingarea"])
    current_role = str(df_user.iloc[0]["role"]).lower().strip()

    # Determine Prefix
    if current_wa == "0000000":
        prefix = ""
    else:
        prefix = current_wa.rstrip("0")

    # Determine Level length for grouping
    level = get_area_level(current_wa)
    if level == "island":
        view_option = st.selectbox("🌍 Select Summary Level", ["Province Wise", "District Wise"])
        prefix_len = 1 if view_option == "Province Wise" else 2
    else:
        prefix_len = get_next_level_length(level)

    # --- FETCH DATA ---
    with st.spinner("Calculating assignment metrics..."):
        df_users, df_assign, names_dict = fetch_dashboard_data(prefix)

    # If no data exists, stop gracefully
    if df_assign.empty and df_users.empty:
        st.info("No users or assignments found for this working area.")
        return

    # --- PREPARE DATA GROUPING ---
    df_users["area_group"] = df_users["workingarea"].astype(str).str[:prefix_len]
    df_assign["area_group"] = df_assign["workingarea"].astype(str).str[:prefix_len]

    # Aggregate Users
    summary_users = df_users.groupby("area_group").agg(
        Supervisors=("role", lambda x: (x == "supervisor").sum()),
        Interviewers=("role", lambda x: (x == "interviewer").sum())
    ).reset_index()

    # Aggregate Assignments
    df_assign['Assign_Sup'] = (df_assign['current_role'] == 'supervisor').astype(int)
    df_assign['Assign_Int'] = (df_assign['current_role'] == 'interviewer').astype(int)
    df_assign['Received_Int'] = ((df_assign['current_role'] == 'interviewer') & (df_assign['latest_action'] == '4')).astype(int)
    
    summary_assign = df_assign.groupby("area_group").agg(
        Assignments_Sup=("Assign_Sup", "sum"),
        Assigned_to_Int=("Assign_Int", "sum"),
        Received_by_Int=("Received_Int", "sum"),
        Reassigned=("is_reassigned", "sum")
    ).reset_index()

    # Merge everything together
    df_result = pd.merge(summary_users, summary_assign, on="area_group", how="outer").fillna(0)

    # Attach the proper Area Names
    df_names = names_dict.get(prefix_len, pd.DataFrame(columns=["code", "name"]))
    df_result = df_result.merge(df_names, left_on="area_group", right_on="code", how="left")
    
    # Clean up table columns
    df_result.rename(columns={"name": "Area Name", "area_group": "Area Code"}, inplace=True)
    df_result = df_result.dropna(subset=["Area Name"]) # Remove unmapped areas
    
    # Force integers
    cols_to_int = ["Supervisors", "Interviewers", "Assignments_Sup", "Assigned_to_Int", "Received_by_Int", "Reassigned"]
    df_result[cols_to_int] = df_result[cols_to_int].astype(int)

    # Rename final columns for display
    df_result.rename(columns={
        "Assignments_Sup": "Assignments (Sup)",
        "Assigned_to_Int": "Assigned (Int)",
        "Received_by_Int": "Received (Int)"
    }, inplace=True)
    
    df_result = df_result[["Area Code", "Area Name", "Supervisors", "Interviewers", "Assignments (Sup)", "Assigned (Int)", "Received (Int)", "Reassigned"]]

    # --- CALCULATE TOP LEVEL KPIs ---
    tot_sup = int(df_result["Supervisors"].sum())
    tot_int = int(df_result["Interviewers"].sum())
    tot_a_sup = int(df_result["Assignments (Sup)"].sum())
    tot_a_int = int(df_result["Assigned (Int)"].sum())
    tot_r_int = int(df_result["Received (Int)"].sum())
    tot_reass = int(df_result["Reassigned"].sum())

    # Adjust supervisor count if the logged-in user is a supervisor (matching original logic)
    display_sup_count = 1 if current_role == "supervisor" else tot_sup

    # --- RENDER KPI METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("👨‍💼 Supervisors", display_sup_count)
    col2.metric("🧑‍💻 Interviewers", tot_int)
    col3.metric("📦 Assignments w/ Supervisors", tot_a_sup)

    col4, col5, col6 = st.columns(3)
    col4.metric("📤 Assigned to Interviewers", tot_a_int)
    col5.metric("📥 Received by Interviewers", tot_r_int)
    col6.metric("🔁 Reassigned Assignments", tot_reass)

    st.markdown("---")

    # --- RENDER DATAFRAME ---
    st.markdown(
        """
        <h3 style='text-align: left; color: #2c3e50; font-size: 18px;'>
            📍 Area-Wise Breakdown
        </h3>
        """,
        unsafe_allow_html=True
    )

    # Append Total Row
    total_row = pd.DataFrame([{
        "Area Code": "",
        "Area Name": "TOTAL",
        "Supervisors": tot_sup,
        "Interviewers": tot_int,
        "Assignments (Sup)": tot_a_sup,
        "Assigned (Int)": tot_a_int,
        "Received (Int)": tot_r_int,
        "Reassigned": tot_reass
    }])
    df_display = pd.concat([df_result, total_row], ignore_index=True)

    # Highlight the last row (Total)
    def highlight_total(s):
        if s.name == len(df_display) - 1:
            return ['font-weight: bold; background-color: #f8f9fa'] * len(s)
        return [''] * len(s)

    st.dataframe(df_display.style.apply(highlight_total, axis=1), use_container_width=True, hide_index=True)

# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":
    show_assignment_dashboard()