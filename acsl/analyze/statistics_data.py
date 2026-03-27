import streamlit as st
import pandas as pd
import numpy as np
from acsl.db import get_connection

try:
    import plotly.figure_factory as ff
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

def show_variable_distribution():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            🔔 Variable Distribution & Statistics
        </h1>
        <p style='color: gray; font-size: 14px;'>Select a numeric variable from the survey to view its statistical summary and bell curve.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    # ==========================================
    # 1. FETCH AVAILABLE COLUMNS
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=300)
    def get_table_columns():
        """Fetches all column names from the main survey table."""
        sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'srilanka_agcensus2025';
        """
        conn = get_connection()
        try:
            df = pd.read_sql(sql, conn)
            return sorted(df['column_name'].tolist())
        except Exception as e:
            st.error(f"Error fetching columns: {e}")
            return []
        finally:
            conn.close()

    all_columns = get_table_columns()
    
    # System columns to explicitly ignore
    ignore_cols = ['interview__id', 'interview__key', 'assignment__id', 'responsible__name', 'sssys_irnd', 'has__errors']
    
    # NEW FILTER: Ignore explicit system columns AND any column containing "preload"
    valid_cols = [
        c for c in all_columns 
        if c not in ignore_cols 
        and "preload" not in c.lower()  # This removes preload_a0, age_preload, etc.
    ]

    if not valid_cols:
        st.warning("No variables found in the survey table.")
        return

    # Dropdown to select the variable
    selected_var = st.selectbox("📊 Select a Variable to Analyze:", ["-- Select Variable --"] + valid_cols)

    if selected_var == "-- Select Variable --":
        return

    # ==========================================
    # 2. FETCH AND CLEAN DATA FOR SELECTED VARIABLE
    # ==========================================
    with st.spinner(f"Calculating statistics for {selected_var}..."):
        conn = get_connection()
        try:
            # We use double quotes around the column name to prevent PostgreSQL syntax errors
            sql_data = f'SELECT "{selected_var}" FROM srilanka_agcensus2025 WHERE "{selected_var}" IS NOT NULL;'
            df_data = pd.read_sql(sql_data, conn)
        except Exception as e:
            st.error(f"Error fetching data for {selected_var}: {e}")
            return
        finally:
            conn.close()

        # IMPORTANT: Survey Solutions sometimes saves numeric answers as text in local databases.
        # We force conversion to numeric. Any text (like "Refused") becomes NaN and is dropped.
        df_data['numeric_val'] = pd.to_numeric(df_data[selected_var], errors='coerce')
        df_clean = df_data.dropna(subset=['numeric_val'])

        if df_clean.empty:
            st.error(f"🚫 No valid numeric data found for `{selected_var}`.")
            st.info("Hint: Bell curves can only be drawn for continuous numeric variables (like Age, Area, or Quantity). Categorical text variables cannot be plotted this way.")
            return

        data_series = df_clean['numeric_val']

    # ==========================================
    # 3. DISPLAY STATISTICS & GRAPH
    # ==========================================
    col1, col2 = st.columns([1, 2]) # Make the graph column twice as wide as the stats column

    # --- LEFT COLUMN: STATS ---
    with col1:
        st.markdown("### 📋 Descriptive Statistics")
        
        stats = {
            "Valid Responses (Count)": len(data_series),
            "Mean (Average)": data_series.mean(),
            "Median (Middle Value)": data_series.median(),
            "Standard Deviation": data_series.std(),
            "Minimum Value": data_series.min(),
            "Maximum Value": data_series.max()
        }
        
        # Create a clean dataframe for display
        stats_df = pd.DataFrame(list(stats.items()), columns=["Statistic", "Value"])
        
        # Format the numbers nicely (e.g., 1,234.56)
        stats_df['Value'] = stats_df['Value'].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "N/A")
        
        # Display using Pandas Styler for a clean look
        st.dataframe(
            stats_df.style.set_properties(**{'text-align': 'right'}, subset=['Value']),
            hide_index=True, 
            use_container_width=True
        )

    # --- RIGHT COLUMN: BELL CURVE GRAPH ---
    with col2:
        st.markdown("### 📈 Distribution (Bell Curve)")
        
        # Plotly's distplot crashes if every single number in the dataset is exactly the same
        if data_series.nunique() <= 1:
            st.warning("Not enough variation in the data to plot a bell curve (all values are identical).")
        else:
            try:
                # Create the distribution plot (Histogram + KDE Bell Curve)
                fig = ff.create_distplot(
                    hist_data=[data_series.tolist()], 
                    group_labels=[selected_var], 
                    show_hist=True,    # Shows the background bars
                    show_curve=True,   # Shows the smooth bell curve line
                    show_rug=False,    # Hides the tiny tick marks at the bottom for a cleaner look
                    colors=['#007bff'] # Nice professional blue
                )
                
                # Polish the layout
                fig.update_layout(
                    title_text=f"Distribution shape of {selected_var}",
                    xaxis_title="Reported Value",
                    yaxis_title="Density / Frequency",
                    showlegend=False,
                    margin=dict(t=40, b=10, l=10, r=10)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Could not generate plot. The data may contain extreme outliers causing calculation errors. Details: {e}")