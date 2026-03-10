import streamlit as st
import pandas as pd
from acsl.db import run_query

# --------------------------------------------------
# Detect administrative level from working area
# --------------------------------------------------
def detect_area_level(workingarea):
    if workingarea == "0000000":
        return "island"
    if workingarea[1:] == "000000":
        return "province"
    if workingarea[2:] == "00000":
        return "district"
    if workingarea[4:] == "000":
        return "division"
    return "gndivision"

# --------------------------------------------------
# Get user working area
# --------------------------------------------------
def get_user_workingarea(login):
    result = run_query(
        "SELECT workingarea FROM susouser WHERE LOWER(login)=LOWER(%s)",
        (login,)
    )
    if not result:
        st.error("User not found")
        st.stop()
    workingarea = str(result[0]["workingarea"])
    if workingarea == "0":
        workingarea = "0000000"
    return workingarea

# --------------------------------------------------
# Safe DataFrame conversion
# --------------------------------------------------
def to_df(result):
    if not result:
        return pd.DataFrame()
    return pd.DataFrame(result)

# --------------------------------------------------
# Provincial Progress for working area 0000000
# --------------------------------------------------
def all_province_progress():
    query = """
    SELECT
        LEFT(a.preload_a1b::text,1) AS province_code,
        p.name AS province_name,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a
    JOIN province p
      ON p.code = LEFT(a.preload_a1b::text,1)
    JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor', 'interviewer')
    GROUP BY province_code, province_name
    ORDER BY province_code;
    """
    return to_df(run_query(query))

# --------------------------------------------------
# All District Progress for working area 0000000
# --------------------------------------------------
def All_Dsitrict_progress():
    query = """
    SELECT
        a.preload_a1b AS district_code,
        a.preload_a1a AS district_name,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a
    JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor', 'interviewer')
    GROUP BY district_code, district_name
    ORDER BY district_code;
    """
    return to_df(run_query(query))

# --------------------------------------------------
# particular province progress
# --------------------------------------------------
def province_progress(province_code):
    query = """
    SELECT
        LEFT(a.preload_a1b::text,1) AS province_code,
        p.name AS province_name,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a

    JOIN province p
      ON p.code = LEFT(a.preload_a1b::text,1)

    JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor', 'interviewer')
      AND LEFT(a.preload_a1b::text,1) = %s

    GROUP BY province_code, province_name
    ORDER BY province_code;
    """
    return to_df(run_query(query, (province_code,)))

# --------------------------------------------------
# All District within Province Progress
# --------------------------------------------------
def All_District_within_Province_progress(province_code):

    query = """
    SELECT
        a.preload_a1b AS district_code,
        a.preload_a1a AS district_name,
        
        COUNT(DISTINCT a.meta_id) AS total_assignments,
        
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN 1 END) AS total_interviews_done,
        
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN 1 END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN 1 END) AS assignments_with_supervisors,
        
        COUNT(CASE WHEN u.role='interviewer' THEN 1 END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a
    JOIN susouser u
        ON u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor','interviewer')
      AND LEFT(a.preload_a1b::text,1) = %s

    GROUP BY a.preload_a1b, a.preload_a1a
    ORDER BY a.preload_a1b;
    """

    return to_df(run_query(query, (province_code,)))

# --------------------------------------------------
# District Progress
# --------------------------------------------------
def district_progress(district_code):

    query = """
    SELECT
        a.preload_a1a AS district_name,
        a.preload_a1b AS district_code,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a
    JOIN susouser u
      ON LEFT(u.workingarea::text,2) = LEFT(a.preload_a1b::text,2)
      AND u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor','interviewer')
      AND LEFT(a.preload_a1b::text,2) = %s

    GROUP BY a.preload_a1a, a.preload_a1b
    ORDER BY a.preload_a1a;
    """

    return to_df(run_query(query, (district_code,)))

# --------------------------------------------------
# All DIvisions within District Progress
# --------------------------------------------------
def All_Division_within_District_progress(district_code):

    query = """
    SELECT
        a.preload_a2a AS division_name,
        a.preload_a2b::text AS division_code,
                
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a
    LEFT JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE LEFT(u.workingarea::text,2) = LEFT(a.preload_a2b::text,2)
      AND LEFT(a.preload_a2b::text,2) = %s::text

    GROUP BY division_code, division_name
    ORDER BY division_code;
    """
    return to_df(run_query(query, (district_code,)))
# --------------------------------------------------
# Division Progress
# --------------------------------------------------
def division_progress(division_code):
    query = """
    SELECT
        a.preload_a2a AS division_name,
        a.preload_a2b::text AS division_code,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a

    JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor', 'interviewer')
      AND LEFT(a.preload_a2b::text,4) = %s

    GROUP BY division_code, division_name
    ORDER BY division_code;
    """
    return to_df(run_query(query, (division_code,)))

# --------------------------------------------------
# GN Division Progress
# --------------------------------------------------
def All_gn_within_division_progress(gndivision_code):
    query = """
    SELECT
        a.preload_a3a AS gndivision_name,
        a.preload_a3b::text AS gndivision_code,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a

    JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE u.role IN ('supervisor', 'interviewer')
      AND LEFT(a.preload_a3b::text,4) = %s

    GROUP BY gndivision_code, gndivision_name
    ORDER BY gndivision_code;
    """
    return to_df(run_query(query, (gndivision_code,)))

# --------------------------------------------------
# Dashboard
# --------------------------------------------------
def assignments_dashboard():
    st.title("Agriculture Census Progress Dashboard")

    login = st.session_state.get("login")
    
    if not login:
        st.error("User not logged in")
        return
    
    workingarea = get_user_workingarea(login)
    level = detect_area_level(workingarea)

    df = pd.DataFrame()

    province = workingarea[0:2]

    if level == "island":

        view = st.radio("View Progress", ["Province", "District"])

        if view == "Province":
            df = all_province_progress()
        elif view == "District":
            df = All_Dsitrict_progress()

    elif level == "province":
        view = st.radio("View Progress", ["Province", "District"])

        if view == "Province":
            province=workingarea[:1]
            df = province_progress(province)
        elif view == "District":
            province=workingarea[:1]
            df = All_District_within_Province_progress(province)

    elif level == "district":
        view = st.radio("View Progress", ["District", "Division"])
        
        if view =="District":
            district = workingarea[:2]
            df = district_progress(district)
        elif view=="Division":
            division =workingarea[:2]
            st.write("district",division)
            df= All_Division_within_District_progress(division)

    elif level == "division":
        view = st.radio("View Progress", ["Division", "GN Division"])

        if view == "Division":
            division = workingarea[:4]
            df = division_progress(division)
        elif view == "GN Division":
            gndivision=workingarea[:4]
            df= All_gn_within_division_progress(gndivision)

    else:
        st.warning("GN level dashboard not available")

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No data available.")

# --------------------------------------------------
# Run Dashboard
# --------------------------------------------------
if __name__ == "__main__":
    assignments_dashboard()