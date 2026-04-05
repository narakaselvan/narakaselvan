import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from acsl.db import get_connection

try:
    import plotly.figure_factory as ff
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

# ==========================================
# 1. VARIABLE DEFINITIONS & FILTERING
# Text, Date, and GPS variables are strictly excluded.
# ==========================================

CATEGORICAL_VARS = {
    "Q1_3a": "Land for Agriculture Purpose", "Q1_3b": "Cultivation year ending", "Q1_3c": "Tending Livestock", 
    "Q1_3d": "Aquaculture Activties", "Q1_3e": "Fishing off the farm", "Q1_4a": "Legal status of the holding",
    "Q1_4b": "Type of juridical holding", "Q1_4c": "The main purpose of production", "Q1_4d": "Total land extent 20 perches+",
    "Q1_4e": "Wage work for others", "Q1_2c": "Relationship to holder", "Q2_1_3": "Gender of the Holder",
    "Q2_1_6": "Married status of the Holder", "Q2_1_7": "Higher Education of the Holder", "Q2_1_8": "Vocational Education",
    "Q2_1_9": "Gain Agriculture Knowledge through Internet", "Q2_1_10a": "Source of Income of the Household",
    "Q2_1_11": "Other Source of Income (Multi)", "Q2_3_2": "Gender of the household member", "Q2_3_4": "Worked on the holding",
    "Q2_3_5": "Holding work was the main activity", "Q2_4": "Other economic activities (Multi)",
    "Q2_5_1": "Did this holding have a hired manager", "Q2_5_2b": "Sex of the manager", "Q2_5_2e": "Educational attainment of the manager",
    "Q2_6_1": "Has this holding had employees", "Q2_7b": "Gender of Selected Person", "Q2_7d": "Has the selected person own agricultural Land?",
    "Q2_7e": "Has the selected person documented ownership?", "Q2_7f": "Was selected person's name on the document?",
    "Q3_2": "Unit of Measures", "Q3_5a": "GN Division of Land Parcel", "Q3_5b": "DS Division of Land Parcel",
    "Q3_5c": "District of Land Parcel", "Q3_6": "Tenure of the Land Parcel", "Q3_8": "Types of land use on this parcel (Multi)",
    "Q3_10": "Is cultivation activity carried out as a home gardening", "Q3_11a": "You own and rent out any land?",
    "Q4_0": "Did you grow paddy or any other seasonal crops", "Q4_1": "In which season did you cultivate crops?",
    "Q4_2a": "Did your holding use modern technology", "Q4_2b": "What modern technology method was used? (Multi)",
    "Q4_3a": "Fully or partially controlled irrigation?", "Q4_3b": "Source of irrigation water? (Multi)",
    "Q4_4a": "Fertilizer used for Seasonal crops", "Q4_4b": "Fungicide used for Seasonal crops",
    "Q4_4c": "Insecticide used for Seasonal crops", "Q4_4d": "Weedicide used for Seasonal crops",
    "Q6_0": "Did you grow any permanent/semi-permanent crops", "Q6_2": "Method of cultivation",
    "Q6_7": "Fertilizers used for permanent crops", "Q6_8": "Fungicides used for permanent crops",
    "Q6_9": "Insecticides used for permanent crops", "Q6_10": "Weedicides used for permanent crops",
    "Q7_1_2": "List of livestock (Multi)", "Q8_1b": "Aquatic species (Multi)", "Q8_2": "Nature of water for aquaculture",
    "Q8_3": "Method of aquaculture (Multi)", "Q8_4": "Type of aquaculture activity (Multi)",
    "Q9_1": "Was agriculture machinery used?", "Q9_5": "Machinery ownership status (Multi)",
    "Q10_1": "Are there permanent agricultural workers?"
}

NUMERICAL_VARS = {
    "Q1_5": "Eligibility of Holding", "Q2_1_5": "Age of the Holder", "Q2_1_10b": "Amount of other source of income",
    "Q2_2_1a": "Males aged below 5", "Q2_2_1b": "Females aged below 5", "Q2_2_2a": "Males aged 5 to 14",
    "Q2_2_2b": "Females aged 5 to 14", "Q2_2_3a": "Males aged more than 15", "Q2_2_3b": "Females aged more than 15",
    "Q2_2_4a": "Total Males in Household", "Q2_2_4b": "Total Females in Household", "Q2_2_5": "Total adults aged 15+",
    "Q2_3_3b": "Age of the household member", "Q2_3_6": "Months worked in cultivation year",
    "Q2_3_7": "Weeks worked per month", "Q2_3_8": "Hours worked per week", "Q2_5_2d": "Age of the Manager",
    "Q2_6_2a": "Male Employees", "Q2_6_2b": "Female Employees", "Q2_6_2c": "Total Employees",
    "Q2_6_3a": "Days worked by Males", "Q2_6_3b": "Days worked by Females", "Q2_6_3c": "Days worked by All",
    "Q2_7c": "Age of the selected person", "Q3_1": "No. of Land Parcels", "Q3_7_dec": "Parcel area in decimal acres",
    "Q3_12": "Area owned and operated", "Q3_16": "Total holding area", "Q4_2d": "Greenhouse area (sq. ft)",
    "MAHA": "Total area Maha season", "YALA": "Total area Yala season", "Q9_6": "Machinery owned count",
    "Q10_2_1a": "Total number of permanent employees (Male)", "Q10_2_1b": "Total number of female permanent employees"
}

# ==========================================
# 2. SURVEY SOLUTIONS RESPONSE CODE MAPPINGS
# ==========================================
YES_NO = {"1": "Yes", "0": "No"}
YES_NO_DK = {"1": "Yes", "0": "No", "98": "Don't know"}
GENDER = {"1": "Male", "2": "Female"}
AG_CHEM = {"1": "Chemical only", "2": "Organic only", "3": "Chemical & Organic", "4": "No use"}
EDU = {
    "1": "Never attended", "2": "Passed grade 1", "3": "Passed grade 2", "4": "Passed grade 3", 
    "5": "Passed grade 4", "6": "Passed grade 5", "7": "Passed grade 6", "8": "Passed grade 7",
    "9": "Passed grade 8", "10": "Passed grade 9", "11": "Passed grade 10", "12": "G.C.E. (O/L)", 
    "13": "G.C.E. (A/L)", "14": "Degree", "15": "Post graduate", "16": "Ph.D"
}

VALUE_MAPPINGS = {
    **{k: YES_NO for k in ["Q1_3a", "Q1_3b", "Q1_3c", "Q1_3d", "Q1_3e", "Q1_4d", "Q1_4e", "Q2_1_8", "Q2_1_9", "Q2_3_4", "Q2_3_5", "Q2_5_1", "Q2_6_1", "Q3_5a", "Q3_5b", "Q3_5c", "Q3_10", "Q3_11a", "Q4_0", "Q4_2a", "Q4_3a", "Q6_0", "Q9_1", "Q10_1"]},
    **{k: YES_NO_DK for k in ["Q2_7d", "Q2_7e", "Q2_7f"]},
    **{k: GENDER for k in ["Q2_1_3", "Q2_3_2", "Q2_5_2b", "Q2_7b"]},
    **{k: AG_CHEM for k in ["Q4_4a", "Q4_4b", "Q4_4c", "Q4_4d", "Q6_7", "Q6_8", "Q6_9", "Q6_10"]},
    **{k: EDU for k in ["Q2_1_7", "Q2_5_2e"]},
    "Q1_4a": {"1": "Civil person", "2": "Group of civil personnel", "3": "Juridical person"},
    "Q1_4b": {"1": "Private/commercial", "2": "Government", "3": "Semi-government"},
    "Q1_4c": {"1": "Only sales", "2": "Both sales & self-consumption", "3": "Only self-consumption"},
    "Q1_2c": {"1": "Self", "2": "Manager", "3": "Spouse", "4": "Child", "5": "Parent", "6": "Employee", "7": "Other"},
    "Q2_1_6": {"1": "Never married", "2": "Married", "3": "Widowed", "4": "Divorced", "5": "Separated"},
    "Q2_1_10a": {"1": "All income from Ag", "2": "Some Income from Ag", "3": "No income from Ag"},
    "Q3_2": {"1": "Acres/Roods/Perches", "2": "Decimal acres", "3": "Hectares"},
    "Q3_6": {"1": "Owned", "2": "Rented"},
    "Q4_1": {"1": "Both Maha and Yala", "2": "Only Maha", "3": "Only Yala"},
    "Q6_2": {"1": "Systematic planting", "2": "Scattered planting"},
    "Q8_2": {"1": "Inland water", "2": "Brackish water", "3": "Marine water"}
}

def apply_label_mapping(val, var_name):
    """
    Translates Survey Solutions numeric response codes into actual text labels.
    Unpacks PostgreSQL array strings (e.g., '{1,3}') for multi-selects.
    """
    val_str = str(val).strip()
    if val_str == "nan" or val_str == "None" or val_str == "":
        return None

    if var_name not in VALUE_MAPPINGS:
        return val_str 
    
    mapping = VALUE_MAPPINGS[var_name]
    
    # Handle Survey Solutions Postgres Array (Multi-select) -> formatted as "{1,3}"
    if val_str.startswith('{') and val_str.endswith('}'):
        items = val_str[1:-1].split(',')
        mapped_items = [mapping.get(str(int(i)), i) if i.strip().isdigit() else i for i in items]
        return " & ".join(mapped_items)
        
    # Handle Single-select codes
    if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
        code_key = str(int(float(val_str))) # Convert formats like '01' or '1.0' to '1'
        return mapping.get(code_key, val_str)
        
    return val_str

# ==========================================
# 3. MAIN APP FUNCTION
# ==========================================

def show_variable_distribution():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            🔔 Survey Solutions Data Analysis
        </h1>
        <p style='color: gray; font-size: 14px;'>Select the type of analysis and choose a variable to view its distribution.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    analysis_type = st.radio(
        "📌 Select Analysis Type:",
        ["Numeric / Area Analysis", "Categorical Analysis"],
        horizontal=True
    )

    # Fetch available columns from DB
    @st.cache_data(show_spinner=False, ttl=300)
    def get_table_columns():
        sql = "SELECT column_name FROM information_schema.columns WHERE table_name = 'srilanka_agcensus2025';"
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn)
            return set(df['column_name'].tolist())
        except Exception:
            return set()
        finally:
            conn.close()

    db_columns = get_table_columns()
    active_dict = NUMERICAL_VARS if analysis_type == "Numeric / Area Analysis" else CATEGORICAL_VARS
    
    # Filter variables to ensure they actually exist in the DB
    available_vars = {k: v for k, v in active_dict.items() if k in db_columns}

    if not available_vars:
        st.warning("⚠️ No variables found in the database for this category.")
        return

    # Dropdown to select the variable (Shows: Description (Code))
    options = ["-- Select Variable --"] + [f"{v} ({k})" for k, v in available_vars.items()]
    selected_label = st.selectbox("📊 Select a Variable to Analyze:", options)

    if selected_label == "-- Select Variable --":
        return

    # Extract the DB column name from the selection
    selected_var = selected_label.split("(")[-1].replace(")", "")

    # ==========================================
    # 4. FETCH AND CLEAN DATA
    # ==========================================
    df_data = pd.DataFrame()
    with st.spinner(f"Fetching data for {selected_var}..."):
        conn = get_connection()
        try:
            sql_data = f'SELECT "{selected_var}" FROM srilanka_agcensus2025 WHERE "{selected_var}" IS NOT NULL;'
            df_data = pd.read_sql(sql_data, conn)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return
        finally:
            conn.close()

    if df_data.empty:
        st.warning(f"🚫 No data recorded yet for `{selected_label}`.")
        return

    # Clean the data based on analysis type
    if analysis_type == "Categorical Analysis":
        df_data['clean_val'] = df_data[selected_var].apply(lambda x: apply_label_mapping(x, selected_var))
    else:
        df_data['clean_val'] = pd.to_numeric(df_data[selected_var], errors='coerce')
    
    df_clean = df_data.dropna(subset=['clean_val'])

    if df_clean.empty:
        st.warning(f"🚫 No valid data found for `{selected_label}`.")
        return

    data_series = df_clean['clean_val']

    # ==========================================
    # 5. DISPLAY DASHBOARDS
    # ==========================================
    col1, col2 = st.columns([1, 2])

    if analysis_type == "Numeric / Area Analysis":
        # --------- NUMERICAL ANALYSIS VIEW ---------
        valid_count = len(data_series)

        with col1:
            st.markdown("### 📋 Descriptive Statistics")
            mode_series = data_series.mode()
            
            stats = {
                "Valid Responses": valid_count,
                "Mean (Average)": data_series.mean(),
                "Median (Middle)": data_series.median(),
                "Mode (Most Frequent)": mode_series.iloc[0] if not mode_series.empty else "N/A",
                "Standard Deviation": data_series.std(),
                "Minimum Value": data_series.min(),
                "Maximum Value": data_series.max()
            }
            stats_df = pd.DataFrame(list(stats.items()), columns=["Statistical Factor", "Value"])
            stats_df['Value'] = stats_df['Value'].apply(lambda x: f"{x:,.2f}" if pd.api.types.is_numeric_dtype(type(x)) else str(x))
            st.dataframe(stats_df.style.set_properties(**{'text-align': 'right'}, subset=['Value']), hide_index=True, use_container_width=True)

        with col2:
            st.markdown("### 📈 Distribution")
            if data_series.nunique() <= 1:
                st.warning("Not enough variation to plot a distribution (all collected values are identical).")
            else:
                try:
                    # Dynamically turn off the Bell Curve if there are fewer than 10 interviews
                    draw_curve = valid_count >= 10
                    
                    fig = ff.create_distplot(
                        [data_series.tolist()], 
                        group_labels=[selected_var], 
                        show_hist=True, 
                        show_curve=draw_curve, # Hides curve if < 10 interviews
                        show_rug=True,         # Shows exact real data points as ticks at the bottom!
                        colors=['#007bff']
                    )
                    
                    title_text = f"Distribution of {selected_var}" if draw_curve else f"Histogram of {selected_var} (Curve hidden due to low sample)"
                    
                    fig.update_layout(
                        title_text=title_text, 
                        xaxis_title="Reported Value", 
                        yaxis_title="Density / Frequency", 
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Plot generation failed. Details: {e}")

    else:
        # --------- CATEGORICAL ANALYSIS VIEW ---------
        with col1:
            st.markdown("### 📋 Response Frequencies")
            val_counts = data_series.value_counts().reset_index()
            val_counts.columns = ['Survey Response', 'Count']
            val_counts['Percentage'] = (val_counts['Count'] / val_counts['Count'].sum()) * 100
            val_counts['Percentage'] = val_counts['Percentage'].apply(lambda x: f"{x:.1f}%")

            mode_cat = data_series.mode()
            if not mode_cat.empty:
                st.info(f"**Mode:** `{mode_cat.iloc[0]}` is the most frequent.")
            st.dataframe(val_counts, hide_index=True, use_container_width=True)

        with col2:
            st.markdown("### 📊 Category Bar Chart")
            fig = px.bar(
                val_counts, x='Survey Response', y='Count', text='Count',
                color='Survey Response', color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_xaxes(type='category')
            fig.update_layout(title_text=f"Response Counts for {selected_var}", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    show_variable_distribution()