import streamlit as st
import pandas as pd
from acsl.db import get_connection

try:
    import plotly.express as px
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

# ==========================================
# 1. HARDCODED DICTIONARIES (From Questionnaire)
# ==========================================
LAND_USE_MAP = {
    "1": "Paddy", "01": "Paddy",
    "2": "Seasonal crops (other than paddy)", "02": "Seasonal crops (other than paddy)",
    "3": "Permanent or semipermanent crops", "03": "Permanent or semipermanent crops",
    "4": "Forests and other wooded lands", "04": "Forests and other wooded lands",
    "5": "Aquaculture", "05": "Aquaculture",
    "6": "Exclusively for livestock", "06": "Exclusively for livestock",
    "7": "Temporary fallow lands", "07": "Temporary fallow lands",
    "8": "Meadows and pastureland", "08": "Meadows and pastureland",
    "9": "Farm buildings, farmyards", "09": "Farm buildings, farmyards",
    "10": "Other land uses"
}

LIVESTOCK_MAP = {
    "11": "Cattle", "12": "Buffaloes", "13": "Sheep", "14": "Goats", 
    "15": "Swine/pigs", "16": "Chickens", "17": "Turkeys", "18": "Geese", 
    "19": "Ducks", "20": "Guinea fowls", "21": "Quail", "22": "Rabbits and hares", 
    "23": "Horses", "24": "Asses", "25": "Bees", "26": "Silkworms", "99": "Other animals"
}

AQUACULTURE_MAP = {
    "1": "Fish", "01": "Fish",
    "2": "Prawns", "02": "Prawns",
    "3": "Ornamental fish", "03": "Ornamental fish",
    "4": "Sea/ Water plants", "04": "Sea/ Water plants",
    "5": "Crab/ Sea urchin/ Shell fish", "05": "Crab/ Sea urchin/ Shell fish",
    "6": "No aquaculture", "06": "No aquaculture"
}



# ==========================================
# 2. DATABASE & DATA FETCHING HELPERS
# ==========================================
@st.cache_data(show_spinner=False, ttl=300)
def fetch_lookup_tables():
    """Fetches crops and machinery names from database lookup tables."""
    conn = get_connection()
    try:
        # Try correct spelling first, then fall back to the spelling from the data dictionary
        try:
            m_df = pd.read_sql("SELECT code::VARCHAR, name FROM machinery", conn)
            machinery_map = dict(zip(m_df['code'], m_df['name']))
        except:
            try:
                m_df = pd.read_sql("SELECT code::VARCHAR, name FROM machinary", conn)
                machinery_map = dict(zip(m_df['code'], m_df['name']))
            except: 
                machinery_map = {}

        try:
            sc_df = pd.read_sql("SELECT code::VARCHAR, name FROM seasonal_crops", conn)
            seasonal_map = dict(zip(sc_df['code'], sc_df['name']))
        except: 
            seasonal_map = {}

        try:
            c_df = pd.read_sql("SELECT code::VARCHAR, name FROM crops", conn)
            crops_map = dict(zip(c_df['code'], c_df['name']))
        except: 
            crops_map = {}

        return machinery_map, seasonal_map, crops_map
    finally:
        conn.close()

def unpack_multiselect(val):
    """Safely converts Postgres array strings '{1,3}' into a list of strings ['1', '3']."""
    if pd.isna(val) or val == "" or str(val).strip() == "{}":
        return []
    cleaned = str(val).replace("{", "").replace("}", "").replace('"', '').strip()
    return [v.strip() for v in cleaned.split(",")] if cleaned else []

# ==========================================
# 3. MAIN DASHBOARD FUNCTION
# ==========================================
def show_overview_agricultural_analytics():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            🌾 Agricultural Analytics Dashboard
        </h1>
        <p style='color: gray; font-size: 14px;'>Analyze core agricultural patterns from approved holdings in your area.</p>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    current_login_user = st.session_state.get("login")
    if not current_login_user:
        st.warning("Please login first.")
        return

    def get_user_info(login):
        sql = "SELECT role, workingarea FROM susouser WHERE login = %(login)s LIMIT 1;"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn, params={'login': login})
            return (str(df.iloc[0]['role']).lower().strip(), str(df.iloc[0]['workingarea']).strip()) if not df.empty else (None, None)
        finally:
            conn.close()

    user_role, user_wa = get_user_info(current_login_user)

    prefix = "" 
    if user_wa and user_wa != '0000000':
        prefix = user_wa[:1] if user_wa.endswith('000000') else user_wa[:2] if user_wa.endswith('00000') else user_wa[:4] if user_wa.endswith('000') else user_wa

    # --- FETCH MAIN DATA (WITH DYNAMIC COLUMN DISCOVERY) ---
    @st.cache_data(show_spinner=False, ttl=60)
    def fetch_analytical_data(area_prefix):
        conn = get_connection()
        try:
            # Safely get actual column names from DB to prevent case-sensitivity crashes
            cur = conn.cursor()
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'srilanka_agcensus2025'")
            db_columns = [row[0] for row in cur.fetchall()]
            cur.close()

            def get_col(name):
                # Returns the exact column name matched from the DB, or NULL if it doesn't exist
                for col in db_columns:
                    if col.lower() == name.lower():
                        return f'MAX("{col}"::VARCHAR)'
                return "NULL"

            # Dynamically assign columns safely
            q3_8_col = get_col('q3_8')
            q9_4_col = get_col('q9_4')
            q4_5_1_col = get_col('q4_5_1')
            q6_1_col = get_col('q6_1')
            q7_1_2_col = get_col('q7_1_2')
            q8_1b_col = get_col('q8_1b')

            sql = f"""
            WITH MainData AS (
                SELECT 
                    interview__key::VARCHAR AS int_key, 
                    MAX(assignment__id::VARCHAR) AS assignment_id,
                    {q3_8_col} AS q3_8,
                    {q9_4_col} AS q9_4,
                    {q4_5_1_col} AS q4_5_1,
                    {q6_1_col} AS q6_1,
                    {q7_1_2_col} AS q7_1_2,
                    {q8_1b_col} AS q8_1b
                FROM srilanka_agcensus2025
                GROUP BY interview__key
            )
            SELECT DISTINCT
                d.interview__key::VARCHAR AS "Interview Key",
                (COALESCE(a.preload_a0::VARCHAR, '') || COALESCE(a.preload_a01::VARCHAR, '')) AS "Block",
                COALESCE(p.name, 'Unknown') AS province_name,
                COALESCE(d_ist.name, 'Unknown') AS district_name,
                COALESCE(v.name, 'Unknown') AS division_name,
                COALESCE(g.name, 'Unknown') AS gndivision_name,
                m.q3_8, m.q9_4, m.q4_5_1, m.q6_1, m.q7_1_2, m.q8_1b
            FROM interview__diagnostics d
            JOIN MainData m ON d.interview__key::VARCHAR = m.int_key
            JOIN assignments a ON m.assignment_id = a.meta_id::VARCHAR
            LEFT JOIN susouser su ON a.meta_responsiblename = su.login
            LEFT JOIN province p ON SUBSTRING(su.workingarea, 1, 1) = p.code::VARCHAR
            LEFT JOIN district d_ist ON SUBSTRING(su.workingarea, 1, 2) = d_ist.code::VARCHAR
            LEFT JOIN division v ON SUBSTRING(su.workingarea, 1, 4) = v.code::VARCHAR
            LEFT JOIN gndivision g ON su.workingarea = g.code::VARCHAR
            WHERE d.interview__status::FLOAT = 130
              AND (su.workingarea LIKE %(prefix)s || '%%' OR %(prefix)s = '')
            """
            return pd.read_sql(sql, conn, params={'prefix': area_prefix})
        finally:
            conn.close()

    with st.spinner("Loading agricultural data..."):
        df_raw = fetch_analytical_data(prefix)
        machinery_map, seasonal_map, crops_map = fetch_lookup_tables()

    if df_raw.empty:
        st.info("No approved agricultural data found in your working area.")
        return

    # ==========================================
    # 4. CASCADING GEOGRAPHIC FILTERS
    # ==========================================
    st.markdown("<h1 style='text-align: left; color: #2c3e50; font-size: 15px;'>🔍 Filter Scope</h1>", unsafe_allow_html=True)
    df_filt = df_raw.copy()

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2 = st.columns(2)

    r1c1.text_input("📍 Island", value="Sri Lanka", disabled=True, key="ag_ov_isl")
    
    provs = sorted([x for x in set(df_filt['province_name']) if x != 'Unknown'])
    sel_prov = r1c2.selectbox("📍 Province", ["All"] + provs, key="ag_ov_prov_s") if len(prefix) < 1 else r1c2.text_input("📍 Province", df_filt['province_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True, key="ag_ov_prov_l")
    if sel_prov != "All" and len(prefix) < 1: df_filt = df_filt[df_filt['province_name'] == sel_prov]

    dists = sorted([x for x in set(df_filt['district_name']) if x != 'Unknown'])
    sel_dist = r1c3.selectbox("📍 District", ["All"] + dists, key="ag_ov_dist_s") if len(prefix) < 2 else r1c3.text_input("📍 District", df_filt['district_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True, key="ag_ov_dist_l")
    if sel_dist != "All" and len(prefix) < 2: df_filt = df_filt[df_filt['district_name'] == sel_dist]

    divs = sorted([x for x in set(df_filt['division_name']) if x != 'Unknown'])
    sel_div = r1c4.selectbox("📍 Division", ["All"] + divs, key="ag_ov_div_s") if len(prefix) < 4 else r1c4.text_input("📍 Division", df_filt['division_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True, key="ag_ov_div_l")
    if sel_div != "All" and len(prefix) < 4: df_filt = df_filt[df_filt['division_name'] == sel_div]

    gns = sorted([x for x in set(df_filt['gndivision_name']) if x != 'Unknown'])
    sel_gn = r2c1.selectbox("📍 GN Division", ["All"] + gns, key="ag_ov_gn_s") if len(prefix) < 7 else r2c1.text_input("📍 GN Division", df_filt['gndivision_name'].iloc[0] if not df_filt.empty else "N/A", disabled=True, key="ag_ov_gn_l")
    if sel_gn != "All" and len(prefix) < 7: df_filt = df_filt[df_filt['gndivision_name'] == sel_gn]

    blks = sorted(list(set(df_filt['Block'])))
    sel_blk = r2c2.selectbox("🏢 Block", ["All"] + blks, key="ag_ov_blk_s")
    if sel_blk != "All": df_filt = df_filt[df_filt['Block'] == sel_blk]

    if df_filt.empty:
        st.warning("No data matches the selected geographic filters.")
        return

    st.markdown("---")

    # ==========================================
    # 5. ANALYTICAL TABS (The 5 Headings)
    # ==========================================
    tabs = st.tabs([
        "🌍 LandUse Pattern", 
        "🚜 Owned Machinery", 
        "🌾 Crop Category", 
        "🐄 Livestock Category", 
        "🐟 Type of Aquaculture"
    ])

    def render_bar_chart(df, col_name, mapping_dict, title, color):
        """Helper function to explode arrays and render a Plotly bar chart."""
        
        # Guard clause if column didn't exist in DB and is missing/null entirely
        if col_name not in df.columns or df[col_name].isnull().all():
            st.info(f"No data recorded for {title} in the main table. (This data may not have been collected yet, or it is stored inside a Roster).")
            return
            
        df['unpacked'] = df[col_name].apply(unpack_multiselect)
        exploded = df.explode('unpacked')
        exploded = exploded[exploded['unpacked'].str.len() > 0]
        
        if exploded.empty:
            st.info(f"No data recorded for {title} in this area.")
            return

        exploded['Mapped Name'] = exploded['unpacked'].map(mapping_dict).fillna(exploded['unpacked'])
        counts = exploded['Mapped Name'].value_counts().reset_index()
        counts.columns = ['Category', 'Number of Holdings']
        
        fig = px.bar(counts, x='Category', y='Number of Holdings', text='Number of Holdings', title=f"<b>{title}</b>", color_discrete_sequence=[color])
        fig.update_layout(xaxis_title="", yaxis_title="Count", margin=dict(t=40, b=0, l=0, r=0))
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 1: LAND USE ---
    with tabs[0]:
        st.markdown("#### Patterns of Land Use on Holdings")
        render_bar_chart(df_filt.copy(), 'q3_8', LAND_USE_MAP, "Land Use Types Reported", "#28a745")

    # --- TAB 2: MACHINERY ---
    with tabs[1]:
        st.markdown("#### Machinery Used / Owned")
        if not machinery_map:
            st.warning("⚠️ Machinery lookup table not found in database. Displaying raw codes.")
        render_bar_chart(df_filt.copy(), 'q9_4', machinery_map, "Types of Machinery", "#ffc107")

    # --- TAB 3: CROPS ---
    with tabs[2]:
        st.markdown("#### Crop Categories Cultivated")
        col_s, col_p = st.columns(2)
        
        with col_s:
            if not seasonal_map: st.warning("⚠️ Seasonal lookup table missing.")
            render_bar_chart(df_filt.copy(), 'q4_5_1', seasonal_map, "Seasonal Crops", "#17a2b8")
            
        with col_p:
            if not crops_map: st.warning("⚠️ Permanent crops lookup table missing.")
            render_bar_chart(df_filt.copy(), 'q6_1', crops_map, "Permanent / Semi-Permanent Crops", "#20c997")

    # --- TAB 4: LIVESTOCK ---
    with tabs[3]:
        st.markdown("#### Livestock Tended")
        render_bar_chart(df_filt.copy(), 'q7_1_2', LIVESTOCK_MAP, "Livestock Categories", "#d9534f")

    # --- TAB 5: AQUACULTURE ---
    with tabs[4]:
        st.markdown("#### Aquaculture Activities")
        render_bar_chart(df_filt.copy(), 'q8_1b', AQUACULTURE_MAP, "Types of Aquaculture", "#007bff")

if __name__ == "__main__":
    show_overview_agricultural_analytics()