import streamlit as st
import pandas as pd
import io
from acsl.db import get_connection
from faker import Faker

# Initialize Faker for generating fake names and addresses
fake = Faker()

# ==========================================
# 1. CONFIGURATION & MAPPINGS
# ==========================================
REQUIRED_COLUMNS = [
    "A_15SNO", "A0_MRCB_NUMBER", "A0.1_MRCB_LETTER", 
    "A1_DISTRICT_NAME", "A1_DISTRICT_CODE", "A2_DS_NAME", "A2_DS_CODE", 
    "A3_GN_NAME", "A3_GN_CODE", "A10_CENSUS_BLOCK_NUMBER", 
    "A11A_BUILDING_NUMBER", "A11B_BUILDING_NUMBER_LETTER", 
    "A12A_UNIT_NUMBER", "A12B_UNIT_NUMBER_LETTER", "A13_UNIT_TYPE", 
    "A16_HOUSEHOLD_NO", "HOUSEHOLD HEAD NAME/PERSON INCHARGE/OWNER", "ADDRESS"
]

RENAME_MAP = {
    "A_15SNO": "A15",
    "A0_MRCB_NUMBER": "A0",
    "A0.1_MRCB_LETTER": "A01",
    "A1_DISTRICT_NAME": "A1a",
    "A1_DISTRICT_CODE": "A1b",
    "A2_DS_NAME": "A2a",
    "A2_DS_CODE": "A2b",
    "A3_GN_NAME": "A3a",
    "A3_GN_CODE": "A3b",
    "A10_CENSUS_BLOCK_NUMBER": "A10",
    "A11A_BUILDING_NUMBER": "A11a",
    "A11B_BUILDING_NUMBER_LETTER": "A11b",
    "A12A_UNIT_NUMBER": "A12a",
    "A12B_UNIT_NUMBER_LETTER": "A12b",
    "A13_UNIT_TYPE": "A13",
    "A16_HOUSEHOLD_NO": "A14a"
}

FINAL_COLUMN_ORDER = [
    "A15", "A0", "A01", "A1a", "A1b", "A2a", "A2b", "A3a", "A3b", 
    "A10", "A11a", "A11b", "A12a", "A12b", "A13", "A14a", "B7", "B8", 
    "_responsible", "_quantity"
]

# ==========================================
# 2. DATABASE FETCH HELPERS
# ==========================================
@st.cache_data(show_spinner=False, ttl=300)
def fetch_geographic_tables():
    conn = get_connection()
    try:
        df_prov = pd.read_sql("SELECT code::VARCHAR, name FROM province", conn)
        df_dist = pd.read_sql("SELECT code::VARCHAR, name FROM district", conn)
        df_div = pd.read_sql("SELECT code::VARCHAR, name FROM division", conn)
        df_gn = pd.read_sql("SELECT code::VARCHAR, name FROM gndivision", conn)
        return df_prov, df_dist, df_div, df_gn
    except Exception as e:
        st.error(f"Error connecting to database hierarchy tables: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# 3. MAIN APP FUNCTION
# ==========================================
def show_preload_generator():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            ⚙️ Assignment Preload Generator
        </h1>
        <p style='color: gray; font-size: 14px;'>Upload raw Census files, filter sequentially by region, sample by block, and generate Survey Solutions compatible (.tab) preload files with Fake PII.</p>
        <hr style='margin-top: 0px; margin-bottom: 15px;'>
        """,
        unsafe_allow_html=True
    )

    # --- STEP 1: FILE UPLOAD & VALIDATION ---
    uploaded_files = st.file_uploader(
        "📂 Upload Raw Census Files (Excel, CSV, or Tab)", 
        type=["csv", "xlsx", "xls", "tab", "txt"], 
        accept_multiple_files=True
    )

    # NEW FEATURE: Radio button for validation choice
    validate_choice = st.radio(
        "Strictly validate required columns in uploaded files?", 
        ["Yes, validate columns", "No, skip validation"]
    )

    if st.button("📥 Process Uploaded Files"):
        if not uploaded_files:
            st.warning("Please upload at least one file.")
            return

        all_dataframes = []
        has_errors = False

        st.markdown("### 📊 File Processing Status")
        
        with st.spinner("Processing and compiling files..."):
            for file in uploaded_files:
                try:
                    if file.name.endswith('.csv'): df = pd.read_csv(file, dtype=str)
                    elif file.name.endswith(('.xls', '.xlsx')): df = pd.read_excel(file, dtype=str)
                    elif file.name.endswith(('.tab', '.txt')): df = pd.read_csv(file, sep='\t', dtype=str)
                    else: continue

                    if validate_choice == "Yes, validate columns":
                        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
                        if missing_cols:
                            st.error(f"❌ `{file.name}` - **FAILED** (Missing: {', '.join(missing_cols)})")
                            has_errors = True
                        else:
                            df = df[REQUIRED_COLUMNS]
                            all_dataframes.append(df)
                            st.success(f"✅ `{file.name}` - **OK** (Validated)")
                    else:
                        # Skip strict validation: Reindex forces the required columns to exist.
                        # If they are missing in the raw file, they become blank strings.
                        df = df.reindex(columns=REQUIRED_COLUMNS, fill_value="")
                        all_dataframes.append(df)
                        st.success(f"✅ `{file.name}` - **OK** (Validation Skipped)")

                except Exception as e:
                    st.error(f"❌ `{file.name}` - **FAILED TO READ** ({e})")
                    has_errors = True

        if has_errors and validate_choice == "Yes, validate columns":
            st.warning("⚠️ Processing halted. Please fix the file errors listed above or select 'No, skip validation'.")
            st.stop()
            
        if all_dataframes:
            st.session_state["master_preload_data"] = pd.concat(all_dataframes, ignore_index=True)
            st.info(f"💾 Successfully compiled data into memory. Total rows ready for sampling: **{len(st.session_state['master_preload_data'])}**")
            st.markdown("---")

    # --- STEP 2: SEQUENTIAL CASCADING FILTERS ---
    if "master_preload_data" in st.session_state:
        df_master = st.session_state["master_preload_data"].copy()
        
        st.markdown("### 🔍 1. Geographic Drill-Down Scope")
        st.caption("Select your exact working area step-by-step to prevent massive dropdown lists.")
        
        df_prov, df_dist, df_div, df_gn = fetch_geographic_tables()

        col1, col2, col3 = st.columns(3)

        # 1. Province (Single Select)
        prov_opts = {f"{r['name']} ({r['code']})": r['code'] for _, r in df_prov.iterrows()}
        sel_prov_label = col1.selectbox("📍 1. Select Province", ["-- Select Province --"] + list(prov_opts.keys()))
        if sel_prov_label == "-- Select Province --": return
        prov_code = prov_opts[sel_prov_label]

        # 2. District (Single Select)
        valid_dists = df_dist[df_dist['code'].astype(str).str.startswith(str(prov_code))]
        dist_opts = {f"{r['name']} ({r['code']})": r['code'] for _, r in valid_dists.iterrows()}
        sel_dist_label = col2.selectbox("📍 2. Select District", ["-- Select District --"] + list(dist_opts.keys()))
        if sel_dist_label == "-- Select District --": return
        dist_code = dist_opts[sel_dist_label]

        # 3. Division (Single Select)
        valid_divs = df_div[df_div['code'].astype(str).str.startswith(str(dist_code))]
        div_opts = {f"{r['name']} ({r['code']})": r['code'] for _, r in valid_divs.iterrows()}
        sel_div_label = col3.selectbox("📍 3. Select Division", ["-- Select Division --"] + list(div_opts.keys()))
        if sel_div_label == "-- Select Division --": return
        div_code = div_opts[sel_div_label]

        st.markdown("---")
        
        # 4. GN Division (Multi Select)
        valid_gns = df_gn[df_gn['code'].astype(str).str.startswith(str(div_code))]
        gn_opts = {f"{r['name']} ({r['code']})": r['code'] for _, r in valid_gns.iterrows()}
        
        sel_gn_labels = st.multiselect("📍 4. Select GN Division(s) for Export", options=list(gn_opts.keys()))
        if not sel_gn_labels: return
        selected_gn_codes = [gn_opts[g] for g in sel_gn_labels]

        # --- STEP 3: DYNAMIC BLOCK SELECTION PER GN ---
        st.markdown("### 🏢 2. Block Selection & Sampling")
        st.caption("Select the specific blocks for each GN Division.")
        
        div_suffix = str(div_code)[-2:]
        
        all_target_rows = [] # Will hold data for all chosen blocks across all GNs

        for gn_label, gn_code in zip(sel_gn_labels, selected_gn_codes):
            gn_suffix = str(gn_code)[-3:]
            
            # Filter master data for this specific GN
            df_gn_specific = df_master[
                (df_master['A2_DS_CODE'].astype(str).str.zfill(2).str.endswith(div_suffix)) &
                (
                    df_master['A3_GN_CODE'].astype(str).str.zfill(3).str.endswith(gn_suffix) |
                    df_master['A3_GN_NAME'].astype(str).str.zfill(3).str.endswith(gn_suffix)
                )
            ].copy()
            
            if df_gn_specific.empty:
                st.warning(f"No data found in uploaded files for {gn_label}.")
                continue
                
            df_gn_specific['Block_Combined'] = df_gn_specific['A0_MRCB_NUMBER'].astype(str) + df_gn_specific['A0.1_MRCB_LETTER'].fillna('').astype(str)
            blocks_in_gn = sorted(df_gn_specific['Block_Combined'].unique().tolist())
            
            # NEW FEATURE: Dynamic Multiselect for each GN Division
            chosen_blocks = st.multiselect(f"Blocks in **{gn_label}**:", options=blocks_in_gn, key=f"blk_sel_{gn_code}")
            
            if chosen_blocks:
                target_rows = df_gn_specific[df_gn_specific['Block_Combined'].isin(chosen_blocks)]
                all_target_rows.append(target_rows)

        if not all_target_rows:
            st.info("👆 Please select at least one block from the GN Divisions above to continue.")
            st.stop()
            
        df_final_target = pd.concat(all_target_rows, ignore_index=True)

        st.markdown("---")
        num_assignments = st.number_input("Number of Assignments per Block:", min_value=1, value=10, step=1)
        
        # --- STEP 4: EXPORT GENERATION ---
        if st.button("⚙️ Generate Preload File (with Fake PII)"):
            
            with st.spinner("Applying Fake Data, restructuring, and formatting for Survey Solutions..."):
                
                df_final_target.rename(columns=RENAME_MAP, inplace=True)
                
                # Apply Faker for PII protection
                df_final_target['B7'] = [fake.name() for _ in range(len(df_final_target))]
                df_final_target['B8'] = [fake.address().replace('\n', ', ') for _ in range(len(df_final_target))]
                
                df_final_target['_responsible'] = ""
                df_final_target['_quantity'] = 1
                
                for col in FINAL_COLUMN_ORDER:
                    if col not in df_final_target.columns:
                        df_final_target[col] = ""
                        
                df_final_target = df_final_target[FINAL_COLUMN_ORDER]
                
                # --- EXECUTE SAMPLING & APPEND -1 ROWS ---
                final_processed_rows = []
                # Group by GN code (A3b) and Block (A0, A01) to prevent blocks with the same name in different GNs from merging
                grouped = df_final_target.groupby(['A3b', 'A0', 'A01'], dropna=False)
                
                for (a3b, a0, a01), group in grouped:
                    sampled_group = group.head(num_assignments).copy()
                    final_processed_rows.append(sampled_group)
                    
                    # Create "Closing Row" logic
                    close_row = sampled_group.iloc[0].copy() 
                    keep_cols = ['A0', 'A01', 'A1a', 'A1b', 'A2a', 'A2b', 'A3a', 'A3b']
                    for col in close_row.index:
                        if col not in keep_cols:
                            close_row[col] = ""
                            
                    close_row['_quantity'] = -1
                    close_row['_responsible'] = ""
                    
                    final_processed_rows.append(close_row.to_frame().T)
                    
                df_export = pd.concat(final_processed_rows, ignore_index=True)
                
                # FEATURE: A01 Blank handling logic
                # Ensure it's a string, strip white space, and replace nan/None with empty string
                df_export['A01'] = df_export['A01'].astype(str).str.strip().replace(['nan', 'NaN', 'None'], '')
                
                # If A01 is empty AND _quantity is NOT -1, replace with "0"
                blank_mask = df_export['A01'] == ''
                normal_qty_mask = df_export['_quantity'] != -1
                
                df_export.loc[blank_mask & normal_qty_mask, 'A01'] = "0"
                
                # --- OUTPUT CREATION ---
                st.success(f"✅ Preload generation complete! Total rows: {len(df_export)}")
                
                csv_buffer = io.StringIO()
                df_export.to_csv(csv_buffer, sep='\t', index=False)
                
                st.download_button(
                    label="📥 Download Survey Solutions .TAB File",
                    data=csv_buffer.getvalue(),
                    file_name=f"SS_Fake_Preload_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.tab",
                    mime="text/tab-separated-values"
                )

                with st.expander("👁️ Preview Generated Output"):
                    st.dataframe(df_export.head(50))

if __name__ == "__main__":
    show_preload_generator()