import streamlit as st
import pandas as pd
import numpy as np
from acsl.db import get_connection

try:
    import plotly.figure_factory as ff
    import plotly.express as px
except ImportError:
    st.error("⚠️ Plotly is not installed. Please run `pip install plotly` in your terminal.")
    st.stop()

def show_outliers():
    st.markdown(
        """
        <h1 style='text-align: left; color: #2c3e50; font-size: 24px;'>
            🔔 Variable Distribution & Outlier Detection
        </h1>
        <p style='color: gray; font-size: 14px;'>Select a numeric variable to view its statistical summary, bell curve, and explicitly identify outliers.</p>
        <hr>
        """,
        unsafe_allow_html=True
    )

    # ==========================================
    # 1. FETCH AVAILABLE COLUMNS
    # ==========================================
    @st.cache_data(show_spinner=False, ttl=300)
    def get_table_columns():
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
    
    ignore_cols = ['interview__id', 'interview__key', 'assignment__id', 'responsible__name', 'sssys_irnd', 'has__errors']
    
    valid_cols = [
        c for c in all_columns 
        if c not in ignore_cols 
        and "preload" not in c.lower()
    ]

    if not valid_cols:
        st.warning("No variables found in the survey table.")
        return

    # FIXED: Added key="outliers_var_select"
    selected_var = st.selectbox(
        "📊 Select a Variable to Analyze:", 
        ["-- Select Variable --"] + valid_cols,
        key="outliers_var_select"
    )

    if selected_var == "-- Select Variable --":
        return

    # ==========================================
    # 2. FETCH DATA & CALCULATE OUTLIERS
    # ==========================================
    with st.spinner(f"Calculating statistics and detecting outliers for {selected_var}..."):
        conn = get_connection()
        try:
            sql_data = f'SELECT interview__key::VARCHAR, "{selected_var}" FROM srilanka_agcensus2025 WHERE "{selected_var}" IS NOT NULL;'
            df_data = pd.read_sql(sql_data, conn)
        except Exception as e:
            st.error(f"Error fetching data for {selected_var}: {e}")
            return
        finally:
            conn.close()

        # Force conversion to numeric
        df_data['numeric_val'] = pd.to_numeric(df_data[selected_var], errors='coerce')
        df_clean = df_data.dropna(subset=['numeric_val']).copy()

        if df_clean.empty:
            st.error(f"🚫 No valid numeric data found for `{selected_var}`.")
            return

        data_series = df_clean['numeric_val']

        # --- OUTLIER MATH (IQR Method) ---
        Q1 = data_series.quantile(0.25)
        Q3 = data_series.quantile(0.75)
        IQR = Q3 - Q1
        
        # Define bounds (1.5 * IQR is the standard statistical rule)
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        # Flag the outliers in the dataframe
        df_clean['Is_Outlier'] = (df_clean['numeric_val'] < lower_bound) | (df_clean['numeric_val'] > upper_bound)
        
        # Extract just the outlier records
        df_outliers = df_clean[df_clean['Is_Outlier']].copy()
        
        # Sort outliers by magnitude (highest absolute distance from median)
        median_val = data_series.median()
        df_outliers['Deviation'] = abs(df_outliers['numeric_val'] - median_val)
        df_outliers = df_outliers.sort_values(by='Deviation', ascending=False).drop(columns=['Deviation', selected_var, 'Is_Outlier'])

    # ==========================================
    # 3. DISPLAY STATISTICS & GRAPHS
    # ==========================================
    col1, col2 = st.columns([1, 2])

    # --- LEFT COLUMN: STATS ---
    with col1:
        st.markdown("### 📋 Descriptive Statistics")
        
        stats = {
            "Valid Responses": len(data_series),
            "Mean (Average)": data_series.mean(),
            "Median (Middle)": data_series.median(),
            "Std Deviation": data_series.std(),
            "Minimum": data_series.min(),
            "Maximum": data_series.max(),
            "---": "---", # Visual separator
            "Lower Bound (IQR)": lower_bound,
            "Upper Bound (IQR)": upper_bound,
            "Total Outliers": len(df_outliers)
        }
        
        stats_df = pd.DataFrame(list(stats.items()), columns=["Statistic", "Value"])
        
        def format_stat(val):
            if val == "---": return ""
            return f"{val:,.2f}" if isinstance(val, (int, float)) else val
            
        stats_df['Value'] = stats_df['Value'].apply(format_stat)
        
        st.dataframe(
            stats_df.style.set_properties(**{'text-align': 'right'}, subset=['Value']),
            hide_index=True, 
            use_container_width=True
        )

        # Show the actual outlier records in a table
        if not df_outliers.empty:
            st.markdown(f"### 🚨 Outlier Records ({len(df_outliers)})")
            st.info("These interviews reported values outside the expected statistical range.")
            df_outliers.rename(columns={'numeric_val': f'Reported {selected_var}'}, inplace=True)
            st.dataframe(df_outliers, use_container_width=True, hide_index=True)

    # --- RIGHT COLUMN: GRAPHS ---
    with col2:
        graph_tabs = st.tabs(["📈 Box Plot (Outlier View)", "🔔 Bell Curve (Distribution)"])
        
        # 1. BOX PLOT (Best for Outliers)
        with graph_tabs[0]:
            st.markdown("##### Box Plot (Tukey's Fences)")
            st.caption("Dots outside the left/right 'whiskers' represent the exact outliers detected.")
            fig_box = px.box(
                df_clean, 
                x="numeric_val", 
                points="outliers", # Only show individual dots if they are outliers
                hover_data=["interview__key"], # Show interview key when hovering over a dot!
                labels={"numeric_val": selected_var}
            )
            fig_box.update_traces(marker=dict(color='#d9534f')) # Red outliers
            st.plotly_chart(fig_box, use_container_width=True)

        # 2. BELL CURVE / HISTOGRAM
        with graph_tabs[1]:
            st.markdown("##### Histogram & KDE Curve")
            if data_series.nunique() <= 1:
                st.warning("Not enough variation in the data to plot a bell curve.")
            else:
                try:
                    fig_dist = ff.create_distplot(
                        hist_data=[data_series.tolist()], 
                        group_labels=[selected_var], 
                        show_hist=True, show_curve=True, show_rug=False,
                        colors=['#007bff']
                    )
                    
                    # Add vertical lines to show the outlier bounds on the bell curve!
                    fig_dist.add_vline(x=lower_bound, line_dash="dash", line_color="red", annotation_text="Lower Bound")
                    fig_dist.add_vline(x=upper_bound, line_dash="dash", line_color="red", annotation_text="Upper Bound")
                    
                    fig_dist.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_dist, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not generate bell curve (data may be too skewed). Details: {e}")