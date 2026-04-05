import streamlit as st
import pandas as pd
import numpy as np
from acsl.db import get_connection

try:
    import plotly.express as px
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

# ==========================================
# 1. NUMERIC VARIABLE DICTIONARY
# Strictly limits analysis to continuous variables.
# ==========================================
NUMERICAL_VARS = {
    "Q1_5": "Eligibility of Holding", 
    "Q2_1_5": "Age of the Holder", 
    "Q2_1_10b": "Amount of other source of income",
    "Q2_2_1a": "Males aged below 5", 
    "Q2_2_1b": "Females aged below 5", 
    "Q2_2_2a": "Males aged 5 to 14",
    "Q2_2_2b": "Females aged 5 to 14", 
    "Q2_2_3a": "Males aged more than 15", 
    "Q2_2_3b": "Females aged more than 15",
    "Q2_2_4a": "Total Males in Household", 
    "Q2_2_4b": "Total Females in Household", 
    "Q2_2_5": "Total adults aged 15+",
    "Q2_3_3b": "Age of the household member", 
    "Q2_3_6": "Months worked in cultivation year",
    "Q2_3_7": "Weeks worked per month", 
    "Q2_3_8": "Hours worked per week", 
    "Q2_5_2d": "Age of the Manager",
    "Q2_6_2a": "Male Employees", 
    "Q2_6_2b": "Female Employees", 
    "Q2_6_2c": "Total Employees",
    "Q2_6_3a": "Days worked by Males", 
    "Q2_6_3b": "Days worked by Females", 
    "Q2_6_3c": "Days worked by All",
    "Q2_7c": "Age of the selected person", 
    "Q3_1": "No. of Land Parcels", 
    "Q3_7_dec": "Parcel area in decimal acres",
    "Q3_12": "Area owned and operated", 
    "Q3_16": "Total holding area", 
    "Q4_2d": "Greenhouse area (sq. ft)",
    "MAHA": "Total area Maha season", 
    "YALA": "Total area Yala season", 
    "Q9_6": "Machinery owned count",
    "Q10_2_1a": "Total number of permanent employees (Male)", 
    "Q10_2_1b": "Total number of female permanent employees"
}

def show_regional_statistics():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            🗺️ Regional Statistics Report
        </h1>
        <p style='color: gray; font-size: 14px;'>Compare statistical factors across different administrative regions.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    # ==========================================
    # 2. FETCH LOGGED-IN USER INFO
    # ==========================================
    def get_user_info(login):
        sql = "SELECT role, workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn, params={'login': login})
            if not df.empty:
                return str(df.iloc[0]['role']).lower().strip(), str(df.iloc[0]['workingarea']).strip()
            return None, None
        finally:
            conn.close()

    user_role, user_wa = get_user_info(current_login_user)
    
    # Prefix Length for Locking logic
    prefix = "" 
    if user_wa:
        if user_wa == '0000000': prefix = ''
        elif user_wa.endswith('000000'): prefix = user_wa[:1]
        elif user_wa.endswith('00000'): prefix = user_wa[:2]
        elif user_wa.endswith('000'): prefix = user_wa[:4]
        else: prefix = user_wa
    else:
        st.error("Error: Could not determine working area for the current user.")
        return

    # ==========================================
    # 3. ANALYSIS SETTINGS (Variables & Factors)
    # ==========================================
    col_var, col_stat = st.columns(2)

    # 3A. Select Variable
    @st.cache_data(show_spinner=False, ttl=300)
    def get_table_columns():
        sql = "SELECT column_name FROM information_schema.columns WHERE table_name = 'srilanka_agcensus2025';"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn)
            return set(df['column_name'].tolist())
        except Exception: return set()
        finally: conn.close()

    db_columns = get_table_columns()
    available_vars = {k: v for k, v in NUMERICAL_VARS.items() if k in db_columns}
    var_options = ["-- Select Variable --"] + [f"{v} ({k})" for k, v in available_vars.items()]

    selected_label = col_var.selectbox("📊 1. Select a Variable:", var_options)
    
    # 3B. Select Statistical Factor
    stat_options = ["Mean (Average)", "Median (Middle)", "Mode (Most Frequent)", "Standard Deviation", "Minimum Value", "Maximum Value"]
    selected_stat = col_stat.selectbox("🧮 2. Select Statistical Factor:", stat_options)

    if selected_label == "-- Select Variable --":
        st.info("👆 Please select a variable to generate the regional comparison.")
        return

    selected_var = selected_label.split("(")[-1].replace(")", "")

    # ==========================================
    # 4. FETCH DATA FROM DATABASE
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_regional_data(area_prefix, var_name):
        conn = get_connection()
        try:
            sql = f"""
            WITH OriginalInterviewer AS (
                SELECT interview__key::VARCHAR AS int_key, responsible__name,
                       ROW_NUMBER() OVER(PARTITION BY interview__key ORDER BY "date" ASC, "time" ASC) as rn
                FROM interview__actions
                WHERE responsible__name IS NOT NULL AND TRIM(responsible__name) != ''
            )
            SELECT
                m.interview__key::VARCHAR AS "Interview Key",
                m."{var_name}",
                COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '') AS "Block",
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name
            FROM srilanka_agcensus2025 m
            LEFT JOIN OriginalInterviewer oi ON m.interview__key::VARCHAR = oi.int_key AND oi.rn = 1
            LEFT JOIN susouser su ON oi.responsible__name = su.login
            LEFT JOIN assignments a ON m.assignment__id::VARCHAR = a.meta_id::VARCHAR
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE m."{var_name}" IS NOT NULL
            AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
            """
            df = pd.read_sql(sql, conn, params={'prefix': area_prefix})
            return df
        finally:
            conn.close()

    with st.spinner("Fetching data for regions..."):
        df_raw = fetch_regional_data(prefix, selected_var)
        
    df_raw['Block'] = df_raw['Block'].replace('', 'Missing Block')
    df_raw['clean_val'] = pd.to_numeric(df_raw[selected_var], errors='coerce')
    df_clean = df_raw.dropna(subset=['clean_val']).copy()

    if df_clean.empty:
        st.warning(f"🚫 No valid data found for `{selected_label}` in your working area.")
        return

    # ==========================================
    # 5. CASCADING FILTERS & DRILL-DOWN LOGIC
    # ==========================================
    st.markdown("##### 🌍 3. Target Region (Drill-Down)")
    st.caption("The chart automatically compares the regions exactly *one level below* your deepest selection.")
    
    df_filt = df_clean.copy()
    group_col = 'province_name' # Default starting group
    chart_title_suffix = "Provinces"

    col1, col2, col3, col4, col5 = st.columns(5)

    # 1. Island
    col1.text_input("📍 Island", value="Sri Lanka", disabled=True)

    # 2. Province
    if len(prefix) >= 1:
        fixed_prov = df_filt['province_name'].iloc[0] if not df_filt.empty else "N/A"
        col2.text_input("📍 Province", value=fixed_prov, disabled=True)
        df_filt = df_filt[df_filt['province_name'] == fixed_prov]
        group_col = 'district_name'
        chart_title_suffix = f"Districts in {fixed_prov}"
    else:
        provs = sorted([x for x in set(df_filt['province_name']) if x != 'Unknown'])
        sel_prov = col2.selectbox("📍 Province", ["All"] + provs)
        if sel_prov != "All":
            df_filt = df_filt[df_filt['province_name'] == sel_prov]
            group_col = 'district_name'
            chart_title_suffix = f"Districts in {sel_prov}"

    # 3. District
    if len(prefix) >= 2:
        fixed_dist = df_filt['district_name'].iloc[0] if not df_filt.empty else "N/A"
        col3.text_input("📍 District", value=fixed_dist, disabled=True)
        df_filt = df_filt[df_filt['district_name'] == fixed_dist]
        group_col = 'division_name'
        chart_title_suffix = f"Divisions in {fixed_dist}"
    else:
        dists = sorted([x for x in set(df_filt['district_name']) if x != 'Unknown'])
        sel_dist = col3.selectbox("📍 District", ["All"] + dists)
        if sel_dist != "All":
            df_filt = df_filt[df_filt['district_name'] == sel_dist]
            group_col = 'division_name'
            chart_title_suffix = f"Divisions in {sel_dist}"

    # 4. Division
    if len(prefix) >= 4:
        fixed_div = df_filt['division_name'].iloc[0] if not df_filt.empty else "N/A"
        col4.text_input("📍 Division", value=fixed_div, disabled=True)
        df_filt = df_filt[df_filt['division_name'] == fixed_div]
        group_col = 'gndivision_name'
        chart_title_suffix = f"GN Divisions in {fixed_div}"
    else:
        divs = sorted([x for x in set(df_filt['division_name']) if x != 'Unknown'])
        sel_div = col4.selectbox("📍 Division", ["All"] + divs)
        if sel_div != "All":
            df_filt = df_filt[df_filt['division_name'] == sel_div]
            group_col = 'gndivision_name'
            chart_title_suffix = f"GN Divisions in {sel_div}"

    # 5. GN Division
    if len(prefix) >= 7:
        fixed_gn = df_filt['gndivision_name'].iloc[0] if not df_filt.empty else "N/A"
        col5.text_input("📍 GN Division", value=fixed_gn, disabled=True)
        df_filt = df_filt[df_filt['gndivision_name'] == fixed_gn]
        group_col = 'Block'
        chart_title_suffix = f"Blocks in {fixed_gn}"
    else:
        gns = sorted([x for x in set(df_filt['gndivision_name']) if x != 'Unknown'])
        sel_gn = col5.selectbox("📍 GN Division", ["All"] + gns)
        if sel_gn != "All":
            df_filt = df_filt[df_filt['gndivision_name'] == sel_gn]
            group_col = 'Block'
            chart_title_suffix = f"Blocks in {sel_gn}"

    if df_filt.empty:
        st.warning("No data matches the selected geographic filters.")
        return

    # ==========================================
    # 6. MATHEMATICAL CALCULATIONS
    # ==========================================
    # Remove 'Unknown' groups from final chart view for a cleaner look
    df_chart_data = df_filt[df_filt[group_col] != 'Unknown'].copy()

    if df_chart_data.empty:
        st.info("No named regions available to compare at this level.")
        return

    with st.spinner("Crunching statistical factors..."):
        if selected_stat == "Mean (Average)":
            df_grouped = df_chart_data.groupby(group_col)['clean_val'].mean().reset_index()
        elif selected_stat == "Median (Middle)":
            df_grouped = df_chart_data.groupby(group_col)['clean_val'].median().reset_index()
        elif selected_stat == "Mode (Most Frequent)":
            df_grouped = df_chart_data.groupby(group_col)['clean_val'].apply(lambda x: x.mode().iloc[0] if not x.mode().empty else np.nan).reset_index()
        elif selected_stat == "Standard Deviation":
            df_grouped = df_chart_data.groupby(group_col)['clean_val'].std().reset_index()
        elif selected_stat == "Minimum Value":
            df_grouped = df_chart_data.groupby(group_col)['clean_val'].min().reset_index()
        elif selected_stat == "Maximum Value":
            df_grouped = df_chart_data.groupby(group_col)['clean_val'].max().reset_index()

    # Clean up standard deviation NaNs (occurs if only 1 interview exists in a region)
    df_grouped['clean_val'] = df_grouped['clean_val'].fillna(0)
    
    # Sort values descending for better chart readability
    df_grouped = df_grouped.sort_values('clean_val', ascending=False)

    # ==========================================
    # 7. RENDER BAR CHART
    # ==========================================
    st.markdown("---")
    
    fig = px.bar(
        df_grouped, 
        x=group_col, 
        y='clean_val',
        text='clean_val',
        color='clean_val',
        color_continuous_scale=px.colors.sequential.Blues,
        labels={
            group_col: "Region",
            'clean_val': selected_stat
        }
    )
    
    # Format the numbers sitting on top of the bars
    fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')
    
    fig.update_layout(
        title=dict(
            text=f"<b>{selected_stat}</b> of {selected_label} <br><sup>Comparing {chart_title_suffix}</sup>",
            x=0.5, xanchor='center', font=dict(size=18)
        ),
        xaxis_title="Geographic Regions",
        yaxis_title=f"{selected_stat} Value",
        margin=dict(t=80, b=40, l=10, r=10),
        height=500,
        showlegend=False
    )
    
    # Make sure Plotly respects all category names on the X-axis (no skipping)
    fig.update_xaxes(type='category', tickmode='linear')

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    show_regional_statistics()