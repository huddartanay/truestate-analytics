import streamlit as st
import streamlit.components.v1 as components
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


import streamlit as st

# ── UNIFIED PLATFORM INTEGRATION ─────────────────────────────────────────────
# Added so this app can run either standalone or embedded in the unified
# UAE Real Estate Analytics shell. See docs/INTEGRATION_CHANGES.md — DXB-1.
import sys as _sys
from pathlib import Path as _Path
_PLATFORM_ROOT = _Path(__file__).resolve().parent.parent.parent
if str(_PLATFORM_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PLATFORM_ROOT))
from platform_core.region_bridge import (
    page_config as _platform_page_config,
    experiment_selection as _platform_experiment,
    experiment_views as _platform_views,
    render_region_sidebar_title as _platform_sidebar_title,
)

# Page config
# DXB-2: the unified platform owns the single global page configuration.
# Standalone, this behaves exactly as st.set_page_config() did before.
_platform_page_config(initial_sidebar_state="expanded", layout="wide", page_title="FlipOse-RE-Analytics")

# Custom CSS
st.markdown("""
    <style>
        [data-testid="collapsedControl"] {
            position: fixed;
            top: 500px;
            left: 50px;
            z-index: 100;
        }
        .block-container {
            padding-top: 2.5rem;
        }
    </style>
""", unsafe_allow_html=True)
###

# Sidebar navigation
# DXB-3: embedded, the workspace is chosen from the global platform rail and
# resolved back to the SAME legacy identifiers used by every `if page == ...`
# branch below, which are unchanged. Standalone, the original radio renders.
page = _platform_experiment(["V1", "V2","V2.1", "FC","area_combination","V_2.2"])

if page == "V1":
    # Sidebar
    _platform_sidebar_title("🔍 FlipOse-RE-Analytics-V1")  # DXB-4
    
    ################################################################################################################################
    
    # --- File Paths ---
    df_path = "target_df.csv"
    area_stats_path = "df_area_plot_stats.xlsx"
    cat_plot_path = "original_df_description_year.xlsx"
    summary = "data_summary.xlsx"
    sample = "sample_df.csv"
    
    # --- Load Data with Error Handling ---
    
    def load_csv(file_path):
        try:
            return pd.read_csv(file_path)
        except FileNotFoundError:
            st.sidebar.error(f"File not found: {file_path}")
            st.stop()
    
    def load_excel(file_path):
        try:
            return pd.read_excel(file_path)
        except FileNotFoundError:
            st.sidebar.error(f"File not found: {file_path}")
            st.stop()
    
    # --- Load Main Dataset ---
    df = load_csv(df_path)
    st.sidebar.success("All data loaded, 🔍 Explore the Dash Board")
    
    # --- Load Area Stats ---
    df_area_plot_stats = load_excel(area_stats_path)
    
    # --- Sidebar Navigation ---
    # DXB-5: "Data Summary" is hidden from the Experimental Analysis interface
    # when embedded. The `if sidebar_option == "Data Summary"` block below is
    # left in place and simply becomes unreachable. Standalone, nothing changes.
    sidebar_option = st.sidebar.radio("Choose View", _platform_views([
        "Data Summary",
        "Pareto Analysis",
        "Univariate Analysis",
        "Bivariate Analysis",
        "Geo Graphical Analysis",
        "Price Prediction Model"
    ]))
    
    # --- View 1: Data Summary ---
    if sidebar_option == "Data Summary":
        st.subheader("📄 Transactions Data")
        tab1, tab2, tab3 = st.tabs(["Preview", "Summary","Notes"])
        with tab1:
            sample_df = pd.read_csv(sample)
            st.markdown("--> Repeated columns i.e Arabic and Id columns are dropped from Data")
            sample_df  = sample_df.drop(sample_df.columns[0], axis=1)
            st.dataframe(sample_df)
    
    
        with tab2:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label="Number Of Columns", value = 46)
            with col2:
                st.metric(label="Total Records", value = "1,424,588")
            with col3:
                st.metric(label="Start Date(Instance_date)", value="1966-01-18")
            with col4:
                st.metric(label="End Date(Instance_date)", value="2025-04-03")
            
            summary_df = pd.read_excel(summary)
            # Format all numeric columns with commas
            for col in summary_df.select_dtypes(include='number').columns:
                summary_df[col] = summary_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else x)
    
            summary_df.index = range(1, len(summary_df) + 1)
            summary_df.rename(columns={'No_of_units': 'Num_of_Unique_values'}, inplace=True)
            summary_df = summary_df.drop(columns = ["S.no", "Level"])
            st.dataframe(summary_df)
    
        with tab3:
            notes = "notes.xlsx"
            notes_df = pd.read_excel(notes)
            if 'nRecords' in notes_df.columns:
                notes_df['nRecords'] = notes_df['nRecords'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
                st.dataframe(notes_df)
            
    
    # --- View 2: Pareto Analysis ---
    elif sidebar_option == "Pareto Analysis":
        st.markdown("### Pareto Analysis by Area_name_en")
    
        try:
            pereto_file = "pereto_analysis_file.xlsx"
            pereto_analyis = pd.ExcelFile(pereto_file)
            pereto_sheet_names = pereto_analyis.sheet_names
        except FileNotFoundError:
            st.error(f"File not found: {pereto_file}")
            st.stop()
    
        # Read all sheets
        all_sheets_df = pd.read_excel(pereto_analyis, sheet_name=pereto_sheet_names)
    
        # Extract specific sheets
        pareto_summary = all_sheets_df["Pereto_Analysis_by_area_name"]
        ABC_summary = all_sheets_df["ABC_Area_name"]
    
        # Create tabs
        tab1, tab2, tab3 = st.tabs(["Table", "Chart", "ABC summary"])
    
        with tab1:
            #st.markdown("### Pareto Analysis by Area_name_en")
            pareto_summary.rename(columns={'Cum%_areas': 'Cum%_Areas'}, inplace=True)
            pareto_summary.rename(columns={'Percentage(%)': '%_nRecords'}, inplace=True) 
            pareto_summary.rename(columns={'Cumulative_%': 'Cum%_Records'}, inplace=True)
            pareto_summary['nRecords'] = pareto_summary['nRecords'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else x)
            pareto_summary['Cum%_Records'] = pareto_summary['Cum%_Records'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
            pareto_summary['%_nRecords'] = pareto_summary['%_nRecords'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
            pareto_summary['Cum%_Areas'] = pareto_summary['Cum%_Areas'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
            pareto_summary.index = range(1, len(pareto_summary) + 1)
            st.dataframe(pareto_summary, use_container_width=True)
    
        with tab2:
            # Load Excel data
            excel_file_path = "pereto_analysis_only.xlsx"
            df2 = pd.read_excel(excel_file_path)
    
            # Remove any row where area_name_en is 'Total' (case-insensitive)
            df2 = df2[~df2['area_name_en'].str.strip().str.lower().eq('total')]
    
            # Sort and calculate cumulative values
            df2_sorted = df2.sort_values(by='nRecords', ascending=False).reset_index(drop=True)
            df2_sorted['Cumulative_nRecords'] = df2_sorted['nRecords'].cumsum()
            df2_sorted['Cumulative_%'] = (df2_sorted['Cumulative_nRecords'] / df2_sorted['nRecords'].sum()) * 100
    
            # Create figure with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]])
    
            # Add bar for nRecords
            fig.add_trace(
                go.Bar(
                    name='nRecords',
                    x=df2_sorted['area_name_en'],
                    y=df2_sorted['nRecords'],
                    marker_color='blue',
                    hovertemplate='<b>%{x}</b><br>nRecords: %{y}<extra></extra>'
                ),
                secondary_y=False,
            )
    
            # Add line for Cumulative %
            fig.add_trace(
                go.Scatter(
                    name='Cumulative_%',
                    x=df2_sorted['area_name_en'],
                    y=df2_sorted['Cumulative_%'],
                    mode='lines',
                    marker_color='red',
                    hovertemplate='<b>%{x}</b><br>Cumulative %: %{y:.2f}%<extra></extra>'
                ),
                secondary_y=True,
            )
    
            # Axis settings
            fig.update_xaxes(title_text='area_name_en')
    
            # Set fixed linear y-axis for better scaling
            fig.update_yaxes(
                title_text='nRecords',
                tickvals=np.arange(0, 100001, 20000),
                range=[0, 100000],
                secondary_y=False
            )
            fig.update_yaxes(title_text='Cumulative %', secondary_y=True)
    
            # Add breakdown lines at specified areas
            wadi_safa_index = df2_sorted[df2_sorted['area_name_en'] == 'Wadi Al Safa 5'].index
            al_hebiah_index = df2_sorted[df2_sorted['area_name_en'] == 'Al Hebiah Third'].index
    
            if not wadi_safa_index.empty:
                fig.add_vline(
                    x=wadi_safa_index[0],
                    line_dash="dash",
                    line_color="green",
                    #annotation_text="Wadi Al Safa 5 (40%)",
                    #annotation_position="top"
                )
    
            if not al_hebiah_index.empty:
                fig.add_vline(
                    x=al_hebiah_index[0],
                    line_dash="dash",
                    line_color="purple",
                    #annotation_text="Al Hebiah Third (70%)",
                    #annotation_position="top"
                )
    
            # Layout settings
            fig.update_layout(
                title_text='Pareto Analysis by Area',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode='x unified',
                height=600,
                barmode='group'
            )
    
            # Display chart in Streamlit
            st.plotly_chart(fig, use_container_width=True)
    
    
        with tab3:
            st.markdown("ABC Table")
            ABC_summary.rename(columns={'Cum%_records': 'Cum%_Records'}, inplace=True)
            ABC_summary.rename(columns={'Cum%_areas': 'Cum%_Areas'}, inplace=True)
            ABC_summary.rename(columns={'Group_name': 'Group'}, inplace=True)
    
            ABC_summary['nRecords'] = ABC_summary['nRecords'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else x)
            ABC_summary['%Area'] = ABC_summary['%Area'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
            ABC_summary['%Records '] = ABC_summary['%Records '].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
            ABC_summary['Cum%_Records'] = ABC_summary['Cum%_Records'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
            ABC_summary['Cum%_Areas'] = ABC_summary['Cum%_Areas'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else x)
    
            ABC_summary.index = range(1, len(ABC_summary) + 1)
    
            # Swap the columns
            cols = list(ABC_summary.columns)
            i, j = cols.index('Cum%_Records'), cols.index('Cum%_Areas')
            cols[i], cols[j] = cols[j], cols[i]
            ABC_summary = ABC_summary[cols]
    
            st.dataframe(ABC_summary, use_container_width=True)
    
            
            df = ABC_summary
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Bar(name='%Area', x=df['Group'], y=df['%Area'], marker_color='skyblue',
                       hovertemplate='<b>%{x}</b><br>%Area: %{y:.2f}%<extra></extra>'),
                secondary_y=False)
            fig.add_trace(
                go.Bar(name='%Records', x=df['Group'], y=df['%Records '], marker_color='lightcoral',
                       hovertemplate='<b>%{x}</b><br>%Records: %{y:.2f}%<extra></extra>'),
                secondary_y=False)
            fig.add_trace(
                go.Scatter(name='Cum%_records', x=df['Group'], y=df['Cum%_Records'], mode='lines+markers',
                           marker_color='green',
                           hovertemplate='<b>%{x}</b><br>Cum% Records: %{y:.2f}%<extra></extra>'),
                secondary_y=True)
            fig.add_trace(
                go.Scatter(name='Cum%_areas', x=df['Group'], y=df['Cum%_Areas'], mode='lines+markers',
                           marker_color='darkorange',
                           hovertemplate='<b>%{x}</b><br>Cum% Areas: %{y:.2f}%<extra></extra>'),
                secondary_y=True)
            fig.update_xaxes(title_text='Group')
            fig.update_yaxes(title_text='Counts (%Area, %Records)', secondary_y=False)
            fig.update_yaxes(title_text='Cumulative Percentage', secondary_y=True)
            fig.update_layout(
                title_text='ABC chart',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode='x unified'
            )
            st.plotly_chart(fig)
            
    # --- View 3: Univariate Analysis  ---
    if sidebar_option == "Univariate Analysis":
    
        # Load Excel Sheets
        try:
            cat_plot_path = "original_df_description_tables.xlsx"
            xls = pd.ExcelFile(cat_plot_path)
            sheet_names = xls.sheet_names
        except FileNotFoundError:
            st.error(f"File not found: {cat_plot_path}")
            st.stop()
    
        main_tabs = st.tabs([ "Dimensions","Metrics"])
    
        with main_tabs[0]:
            # Select sheet before tabs
            selected_sheet = st.selectbox("Distribution of nRecords by", sheet_names)
            df = pd.read_excel(xls, sheet_name=selected_sheet)
            col1 = df.columns[0]  # Category column
            #st.markdown("### 📊 Bar Plot (nRecords)")
            if "nRecords" in df.columns:
                fig_bar = px.bar(df, x=col1, y="nRecords", title=f"nRecords by {col1}", color=col1)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.warning("'nRecords' column not found.")
        with main_tabs[1]:
            # Dropdown for selecting the category column
            cat_cols = ["meter_sale_price", "procedure_area"]
            cat = st.selectbox("Select the metrics column:", cat_cols)
    
            # Create sub-tabs under the selected category
            sub_tabs = st.tabs(["Table", "Histogram", "Boxplot"])
    
            # 1️⃣ TABLE TAB
            with sub_tabs[0]:
                # Define mapping of category to list of files
                table_files = {
                    "meter_sale_price": [
                        "meter_sale_price_table_final.xlsx",
                        "bin_df_manual.xlsx"
                    ],
                    "procedure_area": [
                        "procedure_area_table_final.xlsx",
                        "bin_df_Procedure_area_manual_xyz.xlsx"
                    ]
                }
    
                # Get the selected category (ensure 'cat' is assigned earlier in your code)
                selected_tables = table_files.get(cat)
    
                if selected_tables:
                    for table_file in selected_tables:
                        try:
                            df = pd.read_excel(table_file)
    
                            # Apply comma formatting ONLY to bin files
                            if "bin_df" in table_file and "nRecords" in df.columns:
                                df['nRecords'] = df['nRecords'].apply(lambda x: f"{x:,}")
    
                            # Display the table
                            #st.markdown(f"#### Displaying: `{table_file}`")
                            st.dataframe(df, use_container_width=True)
    
                        except FileNotFoundError:
                            st.error(f"File not found: {table_file}")
                        except Exception as e:
                            st.error(f"Error reading `{table_file}`: {e}")
    
    
            # 2️⃣ HISTOGRAM TAB
            with sub_tabs[1]:
                # Mapping for bar chart Excel files (inside tab for clarity)
                plot_bar = {
                    "meter_sale_price": "bin_df_manual.xlsx",
                    "procedure_area": "bin_df_Procedure_area_manual_xyz.xlsx"
                }
    
                selected_bar = plot_bar.get(cat)
                if selected_bar:
                    try:
                        df_bar = pd.read_excel(selected_bar)
                        #st.markdown(f"### Barchart for `{cat}`")
                        fig = px.bar(
                            df_bar,
                            x= "bin_range",
                            y="nRecords",
                            #labels={"meter_sale_price": "meter_sale_price", "nRecords": "Number of Records"},
                            title=f"Distribution of {cat.replace('_', ' ').title()}",
                            text_auto=True)
                        # Add black border and control bar width
                        fig.update_traces(marker_line_color='black', marker_line_width=1)
    
                        # Optional: customize layout
                        fig.update_layout(
                            #xaxis_title="meter_sale_price",
                            #yaxis_title="Number of Records",
                            bargap=0,  # Adjust space between bars
                            height=500
                            )
                        st.plotly_chart(fig, use_container_width=True)
                    except FileNotFoundError:
                        st.error(f"File not found: {selected_bar}")
                    except Exception as e:
                        st.error(f"Error creating bar chart: {e}")
    
            with sub_tabs[2]:
                # Mapping for boxplot HTML files
                plot_box = {
                    "meter_sale_price": "meter_sale_price_with_boxplot.html",
                    "procedure_area": "procedure_area_with_boxplot.html"
                }
    
                # Mapping for corresponding PNG images
                plot_images = {
                    "meter_sale_price": "boxplot_meter_sale_price_raw.png",
                    "procedure_area": "boxplot_procedure_area_raw.png"
                }
    
                selected_file = plot_box.get(cat)
                selected_image = plot_images.get(cat)
    
                # Adjusting columns: 2 for image (col1), 3 for boxplot (col2)
                col1, col2 = st.columns([2, 3])
    
                with col1:
                    if selected_image:
                        try:
                            # Display image with automatic scaling to container width
                            st.image(selected_image, use_container_width=True)
                        except FileNotFoundError:
                            st.error(f"Image not found: {selected_image}")
                        except Exception as e:
                            st.error(f"Error loading image: {e}")
    
                with col2:
                    if selected_file:
                        try:
                            with open(selected_file, "r") as file:
                                html_content = file.read()
                                components.html(html_content, height=500, width=800, scrolling=True)
                        except FileNotFoundError:
                            st.error(f"File not found: {selected_file}")
                        except Exception as e:
                            st.error(f"Error loading boxplot HTML: {e}")
    
            
                        
    # --- View 3: Bivariate Analysis  ---
    if sidebar_option == "Bivariate Analysis":
        
        # Step 1: Dropdown selector at the top
        cat_cols = [
            "trans_group_en", "property_type_en", "property_sub_type_en", "property_usage_en", 
            "nearest_metro_en","nearest_landmark_en","nearest_mall_en", "room_en", "reg_type_en", 
            "procedure_name_en","instance_year"
        ]
        cat = st.selectbox("nRecords and Avg_Meter_Sale_Price (Dirham) by:", cat_cols)
        main_tabs = st.tabs([ "Table","charts"])
        with main_tabs[1]:
            # Step 3: Read the Excel for box plot data
            try:
                cat_plot_path = "original_df_description_tables.xlsx"
                xls = pd.ExcelFile(cat_plot_path)
                sheet_names = xls.sheet_names
                selected_sheet = sheet_names[cat_cols.index(cat)]  # Optional: auto match sheet to cat
                df = pd.read_excel(xls, sheet_name=selected_sheet)
            except FileNotFoundError:
                st.error(f"Excel file not found: {cat_plot_path}")
                st.stop()
            except Exception as e:
                st.error(f"Error loading Excel sheet: {e}")
                st.stop()
    
            # Step 4: Display two columns
            col1, col2 = st.columns(2)
    
        with col1:
            # Function to create overlay plot for a single sheet
            def plot_avg_price_and_count_overlay(df1, df2, category_col, labels=("Raw data", "Model_Data")):
                """
                Returns a Plotly figure showing average meter sale price and record count overlay for two DataFrames.
                """
                target_col = "Avg_meter_sale_price"
    
                fig = make_subplots(specs=[[{"secondary_y": True}]])
    
                # First DataFrame
                fig.add_trace(go.Bar(
                    x=df1[category_col],
                    y=df1['nRecords'],
                    name=f'nRecords ({labels[0]})',
                    opacity=0.6
                ), secondary_y=False)
    
                fig.add_trace(go.Scatter(
                    x=df1[category_col],
                    y=df1[target_col],
                    mode='lines+markers',
                    name=f'Avg Price ({labels[0]})'
                ), secondary_y=True)
    
                # Second DataFrame
                fig.add_trace(go.Bar(
                    x=df2[category_col],
                    y=df2['nRecords'],
                    name=f'nRecords ({labels[1]})',
                    opacity=0.6
                ), secondary_y=False)
    
                fig.add_trace(go.Scatter(
                    x=df2[category_col],
                    y=df2[target_col],
                    mode='lines+markers',
                    name=f'Avg Price ({labels[1]})'
                ), secondary_y=True)
    
                # Layout
                fig.update_layout(
                    title=(f'nRecords & Avg Price'),
                    xaxis_title=category_col,
                    yaxis=dict(title='nRecords'),
                    yaxis2=dict(title='Average Meter Sale Price', overlaying='y', side='right'),
                    legend=dict(x=0.99, y=1.2),
                    hovermode='x unified',
                    barmode='group'
                )
    
                return fig
                
            file1 = "description_raw.xlsx"
            file2 = "description_units20.xlsx"
    
            if file1 and file2:
                    raw_excel = pd.read_excel(file1, sheet_name=None)
                    model_excel = pd.read_excel(file2, sheet_name=None)
    
                    #common_sheets = sorted(set(raw_excel.keys()) & set(model_excel.keys()))
    
                    if selected_sheet:
                            # Load data from the selected sheet
                            df1 = raw_excel[selected_sheet]
                            df2 = model_excel[selected_sheet]
    
                            if len(df1.columns) > 0:
                                category_col = df1.columns[0]
                                fig = plot_avg_price_and_count_overlay(df1, df2, category_col)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning(f"⚠️ Sheet '{selected_sheet}' has no columns to plot.")
            else:
                    st.info("Upload both Excel files to continue.")
    
    
        with col2:
            def plot_boxplot_per_category(df, cat_col):
                required_cols = {'min', '25%', '50%', '75%', 'max'}
                if not required_cols.issubset(df.columns):
                    st.warning("DataFrame missing required quantile columns.")
                    return None
    
                fig = go.Figure()
                for _, row in df.iterrows():
                    category = row[cat_col]
                    q1 = row['25%']
                    median = row['50%']
                    q3 = row['75%']
                    min_val = row['min']
                    max_val = row['max']
                    iqr = q3 - q1
                    lower_fence = max(min_val, q1 - 1.5 * iqr)
                    upper_fence = min(max_val, q3 + 1.5 * iqr)
    
                    fig.add_trace(go.Box(
                        name=str(category),  # Label on x-axis
                        q1=[q1],
                        median=[median],
                        q3=[q3],
                        lowerfence=[lower_fence],
                        upperfence=[upper_fence],
                        boxpoints=False,
                    ))
    
                fig.update_layout(
                    title=("Distribution of meter_sale_price"),
                    yaxis_title="Meter Sale Price",
                    boxmode='group',
                    xaxis_title=cat_col,
                    xaxis=dict(tickangle=45, automargin=True),  # Label rotation
                )
                return fig
    
            box_plot = plot_boxplot_per_category(df, df.columns[0])
            if box_plot:
                st.plotly_chart(box_plot, use_container_width=True)
                
        with main_tabs[0]:
            note = "notes.xlsx"
            note_df = pd.read_excel(note)
            st.markdown("Data Explaination")
            st.dataframe(note_df)
            try:
                # Load the raw description data from the corresponding sheet
                description_data = pd.read_excel("table_stats_bivariate.xlsx", sheet_name=cat)
                description_data['Avg_meter_sale_price'] = description_data['Avg_meter_sale_price'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else x)
                description_data['q1'] = description_data['q1'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else x)
                description_data['Median'] = description_data['Median'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else x)
                description_data['q3'] = description_data['q3'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else x)
                #st.subheader(f"Raw Description Table - {cat}")
                st.dataframe(description_data, use_container_width=True)
            except Exception as e:
                st.error(f"Failed to load data for table view: {e}")
    
    
            
            
            
            
    # --- View 5: Price Prediction Model ---
    # Define file paths
    EXCEL_PATH = "Over_all_output.xlsx"
    model_perfomance =  "Model_performance.xlsx"
    html_lr = "predicted_vs_actual_linear.html"
    html_dt = "predicted_vs_actual_decision_tree.html"
    html_xgb = "predicted_vs_actual_XGB_regressor.html"
    html_comparision = "model_perfor_comparision.html"
    
    # Load Excel file with caching
    @st.cache_data
    def load_excel(path):
        xls = pd.ExcelFile(path)
        sheets = xls.sheet_names
        data = {sheet: xls.parse(sheet) for sheet in sheets}
        return data
    
    
    # === Sidebar Selection ===
    if sidebar_option == "Price Prediction Model":
    
        # === Top-Level Tabs ===
        if st.sidebar.button("Show Data Preparation Details"):
            st.markdown("""
                - Data used for model is based on the following:
                    - Outliers removed using `meter_sale_price` and `procedure_area` columns.
                    - From outliers-removed data, we have considered data from the year **2020**.
                        - For the model, we have used data with property type **"Units"**.
                - We had a large number of independent variables in the dataset.
                - To identify the most relevant predictors, we applied a **stepwise regression model**.
                - This method helped us select the best combination of input variables for modeling.
                - Using these selected variables, we built the final model and obtained the results.
                """)
        main_tabs = st.tabs(["📈 Model Performance Tables","📉 Prediction Model Visuals"])
        
        # === Tab 1: Prediction Model Visuals ===
        with main_tabs[1]:
            if os.path.exists(EXCEL_PATH):
                xl = pd.ExcelFile(EXCEL_PATH)
                sheet_names = xl.sheet_names
    
            if len(sheet_names) >= 2:
                first_sheet_name = sheet_names[0]  # Index 1 = second sheet
                df = xl.parse(sheet_name=first_sheet_name)
                df = df.round(2)
                if 'nObservations' in df.columns:
                    df['nObservations'] = df['nObservations'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else x)
                    if 'MAPE' in df.columns:
                        df['MAPE'] = df['MAPE'].apply(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else x)
                df.index = range(1, len(df) + 1)
    
                st.subheader(f"📊 {first_sheet_name}")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("The Excel file has less than 2 sheets.")
                
            st.subheader("🔍 Overall Comparison Report")
            if os.path.exists(html_comparision):
                with open(html_comparision, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=300, scrolling=True)
            else:
                st.warning(f"Comparison HTML not found at: {html_comparision}")
    
            st.subheader("📊 Logistic Regression")
            st.markdown("###Equation : Predicted_price = 0.40134 * Actual_price + 8966.97")
            if os.path.exists(html_lr):
                with open(html_lr, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=400, scrolling=True)
            else:
                st.warning(f"Logistic Regression HTML not found at: {html_lr}")
    
            st.subheader("🌳 Decision Tree")
            st.markdown("###Equation : Predicted_price = 0.465166 * Actual_price + 7993.22")
            if os.path.exists(html_dt):
                with open(html_dt, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=400, scrolling=True)
            else:
                st.warning(f"Decision Tree HTML not found at: {html_dt}")
    
            st.subheader("🚀 XGBoost")
            st.markdown("###Equation : Predicted_price = 0.463650 * Actual_price + 8055.86")
            if os.path.exists(html_xgb):
                with open(html_xgb, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=400, scrolling=True)
            else:
                st.warning(f"XGBoost HTML not found at: {html_xgb}")
    
        # === Tab 3: Area & Sector Sheets ===
        with main_tabs[0]:
                
            Over_all, sector_tab,area_tab = st.tabs(["Over All","Sector wise","Area wise"])
            with Over_all:
                abc = "Over_all_output.xlsx"
                overall_sheets = pd.read_excel(abc, sheet_name=None)
                if overall_sheets:
                    # Process each sheet
                    for sheet_name in overall_sheets:
                        df = overall_sheets[sheet_name]
                        # Format 'MAPE' as percentage string
                        if 'MAPE' in df.columns:
                            df['MAPE'] = df['MAPE'].apply(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else x)
                            # Format 'nObservations' with commas
                            if 'nObservations' in df.columns:
                                df['nObservations'] = df['nObservations'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
                                overall_sheets[sheet_name] = df  # Update in dictionary
                                # Display each sheet in a tab
                    overall_tabs = st.tabs(list(overall_sheets.keys()))
                    for tab, (sheet_name, df) in zip(overall_tabs, overall_sheets.items()):
                        with tab:
                            st.dataframe(df, use_container_width=True)
                
               
            with sector_tab:
                pqr = "sector_name_Output.xlsx"
    
                # Read all sheets
                sector_sheets = pd.read_excel(pqr, sheet_name=None)
    
                if sector_sheets:
                    # Process each sheet
                    for sheet_name in sector_sheets:
                        df = sector_sheets[sheet_name]
                
                        # Format 'MAPE' as percentage string
                        if 'MAPE' in df.columns:
                            df['MAPE'] = df['MAPE'].apply(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else x)
    
                        # Format 'nObservations' with commas
                        if 'nObservations' in df.columns:
                            df['nObservations'] = df['nObservations'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
    
                        sector_sheets[sheet_name] = df  # Update in dictionary
    
                    # Display each sheet in a tab
                    sector_tabs = st.tabs(list(sector_sheets.keys()))
                    for tab, (sheet_name, df) in zip(sector_tabs, sector_sheets.items()):
                        with tab:
                            st.dataframe(df, use_container_width=True)
            
            with area_tab:
                xyz = "Area_name_output.xlsx"
    
                # Read all sheets
                area_sheets = pd.read_excel(xyz, sheet_name=None)
    
                if area_sheets:
                    for sheet_name in area_sheets:
                        df = area_sheets[sheet_name]
                
                        # Convert MAPE to percentage
                        if 'MAPE' in df.columns:
                            df['MAPE'] = df['MAPE'].apply(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else x)
    
                        # Format nObservations with commas
                        if 'nObservations' in df.columns:
                            df['nObservations'] = df['nObservations'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
    
                        area_sheets[sheet_name] = df  # Update back in dict
    
                    # Create tabs and display each sheet
                    area_tabs = st.tabs(list(area_sheets.keys()))
                    for tab, (sheet_name, df) in zip(area_tabs, area_sheets.items()):
                        with tab:
                            st.dataframe(df, use_container_width=True)
    
                        
                    
    
    # --- View 6: Geo Graphical Analysis ---
    if sidebar_option == "Geo Graphical Analysis":
        st.subheader("Dubai Area-wise Bubble Map")
        
        df_excel = pd.read_excel("new_tdf.xlsx")
        units_excel = pd.read_excel("units_20.xlsx")
        outlier_excel = pd.read_excel("outliers.xlsx")  # Replace with your actual outlier dataset
        tab1, = st.tabs(["Average Meter Sale Price"])
    
        # Create the single tab
        with tab1:
    
            # Add filtered data (e.g., >= 2020)
            figs = px.scatter_mapbox(
                units_excel,
                lat='area_lat',
                lon='area_lon',
                size='Transaction Count',
                color='Average Meter Sale Price',
                hover_name='area_name_en',
                hover_data={
                    'Transaction Count': True,
                    'Average Meter Sale Price': ':.2f',
                    'area_lat': False,
                    'area_lon': False
                },
                color_continuous_scale='Hot',
                size_max=30,
                zoom=9,
                title="Dubai Area-wise Average Meter Sale Price(Dirham) and Transaction Count"
            )
    
            for trace in figs.data:
                trace.name = "Model_Data"
                trace.legendgroup = "Model_Data"
                trace.showlegend = True
                
                
    
            # Add filtered data (e.g., >= 2020)
            fig2 = px.scatter_mapbox(
                df_excel,
                lat='area_lat',
                lon='area_lon',
                size='Transaction Count',
                color='Average Meter Sale Price',
                hover_name='area_name_en',
                hover_data={
                    'Transaction Count': True,
                    'Average Meter Sale Price': ':.2f',
                    'area_lat': False,
                    'area_lon': False
                },
                color_continuous_scale='Hot',
                size_max=30,
                opacity=0.8,
                zoom=9,
            )
    
            for trace in fig2.data:
                trace.name = "Raw data"
                trace.legendgroup = "Raw data"
                trace.showlegend = True
                figs.add_trace(trace)
                
    
            # Add outlier data
            fig3 = px.scatter_mapbox(
                outlier_excel,
                lat='area_lat',
                lon='area_lon',
                size='Transaction Count',
                color='Average Meter Sale Price',
                hover_name='area_name_en',
                hover_data={
                    'Transaction Count': True,
                    'Average Meter Sale Price': ':.2f',
                    'area_lat': False,
                    'area_lon': False
                },
                color_continuous_scale='Hot',
                size_max=30,
                opacity=0.7,
                zoom=9
            )
    
            for trace in fig3.data:
                trace.name = "Non_Model_Data"
                trace.legendgroup = "Non_Model_Data"
                trace.showlegend = True
                figs.add_trace(trace)
    
            figs.update_layout(
                mapbox_style='open-street-map',
                margin={"r": 0, "t": 40, "l": 0, "b": 0},
                legend=dict(
                    x=0.01,
                    y=0.99,
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='black',
                    borderwidth=1
                )
            )
    
            st.plotly_chart(figs, use_container_width=True)
            st.markdown(
                """
                <div style="text-align: left; font-size: 15px; margin-top: 10px;">
                    <b>Size of bubble</b> = Number of Transactions &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; 
                    <b>Colour of bubble</b> = Average Meter Sale Price
                </div>
                """,
                unsafe_allow_html=True
            )


elif page == "V2":
    
    # Custom CSS (same style if you want consistency)
    st.markdown("""
        <style>
            [data-testid="collapsedControl"] {
                position: fixed;
                top: 500px;
                left: 50px;
                z-index: 100;
            }
            .block-container {
                padding-top: 2.5rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    _platform_sidebar_title("🔍 FlipOse-RE-Analytics-V2")  # DXB-4
    
    def load_csv(file_path):
        try:
            return pd.read_csv(file_path)
        except FileNotFoundError:
            st.sidebar.error(f"File not found: {file_path}")
            st.stop()
    
    def load_excel(file_path):
        try:
            return pd.read_excel(file_path)
        except FileNotFoundError:
            st.sidebar.error(f"File not found: {file_path}")
            st.stop()
    
    # --- Load Main Dataset ---
        # --- File Paths ---
    #df_path = "target_df.csv"
    #area_stats_path = "df_area_plot_stats.xlsx"
    #cat_plot_path = "original_df_description_year.xlsx"
    summary = "V2_data_summary.xlsx"
    #sample = "sample_df.csv"
    # --- Load Area Stats ---
    #df_area_plot_stats = load_excel(area_stats_path)
    
    # --- Sidebar Navigation ---
    # DXB-5: see the note in the V1 block above.
    sidebar_option = st.sidebar.radio("Choose View", _platform_views([
        "Data Summary",
        #"Pareto Analysis",
        "Univariate Analysis",
        "Bivariate Analysis",
        "Correlation",
        "Price Prediction Model"
    ]))
    
    # --- View 1: Data Summary ---
    if sidebar_option == "Data Summary":
        st.subheader("📄 Micro_Data_combined")
        tab1, tab2 = st.tabs(["Summary","Notes"])
        with tab1:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label="Number Of Columns", value = 107)
            with col2:
                st.metric(label="Total Records", value = "5,88,863")
            with col3:
                st.metric(label="Start Date(Instance_date)", value="2020-01-01")
            with col4:
                st.metric(label="End Date(Instance_date)", value="2025-04-03")
            
            summary_df = pd.read_excel(summary)
            # Format all numeric columns with commas
            for col in summary_df.select_dtypes(include='number').columns:
                summary_df[col] = summary_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else x)
    
            summary_df.index = range(1, len(summary_df) + 1)
            #summary_df.rename(columns={'No_of_units': 'Num_of_Unique_values'}, inplace=True)
            #summary_df = summary_df.drop(columns = ["S.no", "Level"])
            st.dataframe(summary_df)
    
        with tab2:
            notes = "V2_Notes.xlsx"
            notes_df = pd.read_excel(notes)
            if 'nRecords' in notes_df.columns:
                notes_df['nRecords'] = notes_df['nRecords'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
                st.dataframe(notes_df)
    if sidebar_option == "Univariate Analysis":
        
        # Load Excel Sheets
        try:
            cat_plot_path = "V2-column_value_counts_with_avg_price.xlsx"
            xls = pd.ExcelFile(cat_plot_path)
            sheet_names = xls.sheet_names
        except FileNotFoundError:
            st.error(f"File not found: {cat_plot_path}")
            st.stop()
    
        main_tabs = st.tabs(["Dimensions", "Metrics"])
    
        with main_tabs[0]:  # DIMENSIONS
            dim_tabs = st.tabs(["nRecords Chart & Table", "Area-wise Chart & Table"])
        
            # 1️⃣ FIRST TAB
            with dim_tabs[0]:
                selected_sheet = st.selectbox("Distribution of nRecords by", sheet_names, key="nrecords_sheet")
                df = pd.read_excel(xls, sheet_name=selected_sheet)
                col_x = df.columns[0]  # Category column
        
                if "nRecords" in df.columns:
                    chart_df = df[df["nRecords"] != 0]  # filter out zero y-values
                    if not chart_df.empty:
                        fig_bar = px.bar(chart_df, x=col_x, y="nRecords",
                                         title=f"nRecords by {col_x}",
                                         color=col_x)
                        st.plotly_chart(fig_bar, use_container_width=True, key="nrecords_chart")
                    else:
                        st.warning("No data available with non-zero nRecords.")
                else:
                    st.warning("'nRecords' column not found.")
        
                st.dataframe(df, use_container_width=True, key="nrecords_table")
        
            # 2️⃣ SECOND TAB
            with dim_tabs[1]:
                cat_plot_path_1 = "V2_area_wise_value_counts.xlsx"
                area_wise = pd.ExcelFile(cat_plot_path_1)
                sheet_names_1 = area_wise.sheet_names
                selected_sheet_custom_1 = st.selectbox("Select Area_name", sheet_names_1, key="custom_sheet")
                df_custom_1 = pd.read_excel(area_wise, sheet_name=selected_sheet_custom_1)
            
                col_x_1 = df_custom_1.columns[0]  # X-axis
                y_axis_col = st.sidebar.selectbox(
                    "Select Area_name:",
                    [col for col in df_custom_1.columns if col != col_x_1],
                    key="custom_y_axis"
                )
            
                chart_df_custom = df_custom_1[df_custom_1[y_axis_col] != 0]  # filter out zero Y values
            
                if not chart_df_custom.empty:
                    fig_custom = px.bar(chart_df_custom, x=col_x_1, y=y_axis_col,
                                        title=f"{y_axis_col} by {col_x_1}",
                                        color=col_x_1)
                    st.plotly_chart(fig_custom, use_container_width=True)
                else:
                    st.warning(f"No data available for {y_axis_col} with non-zero values.")
            
                # Show only X and selected Y column (non-zero rows)
                st.dataframe(chart_df_custom[[col_x_1, y_axis_col]], use_container_width=True, key="custom_table")






    
        # ----------------- METRICS TAB -----------------
        with main_tabs[1]:
            
            # Map display names to file paths
            html_files = {
                "Meter Sale Price ": "meter_sale_price_boxplot.html",
                "Procedure Area ": "procedure_area_boxplot.html",
                "Actual_worth": "actual_worth_boxplot.html",
                "Unit balcony area": "unit_balcony_area_boxplot.html"
            }
            
            # Dropdown for selection
            selected_name = st.selectbox("Select a visualization:", list(html_files.keys()))
            
            # Get the corresponding HTML file path
            selected_file = html_files[selected_name]
            
            # Display the HTML
            try:
                with open(selected_file, "r") as file:
                    html_content = file.read()
                    components.html(html_content, height=600, scrolling=True)
            except FileNotFoundError:
                st.error(f"File not found: {selected_file}")
            except Exception as e:
                st.error(f"Error loading HTML: {e}")

        # --- View 3: Bivariate Analysis  ---
    if sidebar_option == "Bivariate Analysis":
                # Load Excel Sheets
        try:
            cat_plot_path = "V2-column_value_counts_with_avg_price.xlsx"
            xls = pd.ExcelFile(cat_plot_path)
            sheet_names = xls.sheet_names
        except FileNotFoundError:
            st.error(f"File not found: {cat_plot_path}")
            st.stop()
        selected_sheet = st.selectbox("Distribution of nRecords by", sheet_names, key="nrecords_sheet")
        df = pd.read_excel(xls, sheet_name=selected_sheet)
        col_x = df.columns[0]  # Category column

        if "nRecords" in df.columns and "Avg_Meter_Sale_Price" in df.columns:
            chart_df = df[(df["nRecords"] != 0) & (df["Avg_Meter_Sale_Price"].notnull())]  # filter out zero y-values
            if not chart_df.empty:
                # Create figure with secondary y-axis
                from plotly.subplots import make_subplots
                import plotly.graph_objects as go

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Bar for nRecords
                fig.add_trace(
                    go.Bar(x=chart_df[col_x], y=chart_df["nRecords"], name="nRecords"),
                    secondary_y=False
                )

                # Line for Avg_meter_sale_price
                fig.add_trace(
                    go.Scatter(x=chart_df[col_x], y=chart_df["Avg_Meter_Sale_Price"],
                               mode="lines+markers", name="Avg_meter_sale_price"),
                    secondary_y=True
                )

                fig.update_layout(
                    title=f"nRecords and Avg_meter_sale_price by {col_x}",
                    xaxis_title=col_x,
                    yaxis_title="nRecords",
                    yaxis2_title="Avg_meter_sale_price (Dirham)"
                )

                st.plotly_chart(fig, use_container_width=True, key="nrecords_chart")
            else:
                st.warning("No data available with non-zero nRecords and valid Avg_meter_sale_price.")
        else:
            st.warning("'nRecords' or 'Avg_meter_sale_price' column not found.")

        st.dataframe(df, use_container_width=True, key="nrecords_table")

 # Define file paths
    metrics = "V2_Model_metrics.xlsx"
    model_perfomance =  "Model_performance.xlsx"
    html_lr = "predicted_vs_actual_linear.html"
    html_dt = "predicted_vs_actual_decision_tree.html"
    html_xgb = "predicted_vs_actual_XGB_regressor.html"
    html_comparision = "model_perfor_comparision.html"
    
    # Load Excel file with caching
    @st.cache_data
    def load_excel(path):
        xls = pd.ExcelFile(path)
        sheets = xls.sheet_names
        data = {sheet: xls.parse(sheet) for sheet in sheets}
        return data
    
    
    # === Sidebar Selection ===
    if sidebar_option == "Price Prediction Model":
    
        # === Top-Level Tabs ===
        if st.sidebar.button("Show Data Preparation Details"):
            st.markdown("""
                - Data used for model is based on the following:
                    - Outliers removed using `meter_sale_price` and `procedure_area` columns.
                    - From outliers-removed data, we have considered data from the year **2020**.
                        - For the model, we have used data with property type **"Units"**.
                - We had a large number of independent variables in the dataset.
                - To identify the most relevant predictors, we applied a **stepwise regression model**.
                - This method helped us select the best combination of input variables for modeling.
                - Using these selected variables, we built the final model and obtained the results.
                """)
        main_tabs = st.tabs(["📈 Model Performance Tables","📉 Prediction Model Visuals"])
        
        # === Tab 1: Prediction Model Visuals ===
                
        with main_tabs[1]:
            area_sheet = "V2_area_wise outputs.xlsx"
        
            # Load Excel file as ExcelFile so we can parse by sheet name
            xl = pd.ExcelFile(area_sheet)
            sheet_names = xl.sheet_names
        
            combined_df = pd.DataFrame()
        
            for sheet in sheet_names[:2]:  # Take only first 2 sheets
                df_temp = xl.parse(sheet_name=sheet)
                df_temp = df_temp.round(2)
        
                if 'area_name_en' in df_temp.columns and 'R2' in df_temp.columns:
                    df_temp['R2'] = pd.to_numeric(df_temp['R2'], errors='coerce')
                    df_temp['Sheet'] = sheet  # Label for distinguishing lines
                    combined_df = pd.concat([combined_df, df_temp[['area_name_en', 'R2', 'Sheet']]])
        
            if not combined_df.empty:
                # Sort for proper plotting
                combined_df = combined_df.sort_values(by='area_name_en')
        
                # Plot both sheets on same line chart
                fig = px.line(
                    combined_df,
                    x='area_name_en',
                    y='R2',
                    color='Sheet',
                    markers=True,
                    title="R² Comparison by Area (Both Sheets)"
                )
                fig.update_layout(
                    xaxis_title="Area Name",
                    yaxis_title="R²",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
        
                # Show combined dataframe
                st.dataframe(combined_df, use_container_width=True)
            else:
                st.warning("No valid data found in the first two sheets.")

        
        



    
        # === Tab 3: Area & Sector Sheets ===
        with main_tabs[0]:
                
            Over_all,area_tab = st.tabs(["Over All","Area wise"])
            with Over_all:
                abc_1 = "V2_Model_metrics.xlsx"
                overall_sheets = pd.read_excel(abc_1, sheet_name=None)
                if overall_sheets:
                    # Process each sheet
                    for sheet_name in overall_sheets:
                        df = overall_sheets[sheet_name]
                        # Format 'MAPE' as percentage string
                        if 'MAPE' in df.columns:
                            df['MAPE'] = df['MAPE'].apply(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else x)
                            # Format 'nObservations' with commas
                            #if 'nObservations' in df.columns:
                                #df['nObservations'] = df['nObservations'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
                            overall_sheets[sheet_name] = df  # Update in dictionary
                                # Display each sheet in a tab
                    overall_tabs = st.tabs(list(overall_sheets.keys()))
                    for tab, (sheet_name, df) in zip(overall_tabs, overall_sheets.items()):
                        with tab:
                            st.dataframe(df, use_container_width=True)
            
            with area_tab:
                xyz = "V2_area_wise outputs.xlsx"
    
                # Read all sheets
                area_sheets = pd.read_excel(xyz, sheet_name=None)
    
                if area_sheets:
                    for sheet_name in area_sheets:
                        df = area_sheets[sheet_name]
                
                        # Convert MAPE to percentage
                        if 'MAPE' in df.columns:
                            df['MAPE'] = df['MAPE'].apply(lambda x: f"{x :.2f}%" if pd.notnull(x) else x)
    
                        # Format nObservations with commas
                        if 'nObservations' in df.columns:
                            df['nObservations'] = df['nObservations'].apply(lambda x: f"{x:,}" if pd.notnull(x) else x)
    
                        area_sheets[sheet_name] = df  # Update back in dict
    
                    # Create tabs and display each sheet
                    area_tabs = st.tabs(list(area_sheets.keys()))
                    for tab, (sheet_name, df) in zip(area_tabs, area_sheets.items()):
                        with tab:
                            st.dataframe(df, use_container_width=True)

    # --- View 6: Geo Graphical Analysis ---
    if sidebar_option == "Correlation":
        from PIL import Image
        import plotly.express as px
    
        correlation, Dropping_Features = st.tabs(["correlation", "Dropping_Features"])
    
        with correlation:
            # Read PNG file
            image = Image.open("Associations_correlation.png")
            img_array = np.array(image)
    
            # Create Plotly figure for zoom/pan
            fig_corr = px.imshow(img_array)
            fig_corr.update_xaxes(visible=False)
            fig_corr.update_yaxes(visible=False)
            fig_corr.update_layout(
                title="Dython Nominal Associayions",
                dragmode="pan"
            )
    
            # Show in Streamlit
            st.plotly_chart(fig_corr, use_container_width=True, key="corr_tab")
    
        with Dropping_Features:
            # First image
            image_1 = Image.open("V2_high_correlated.png")
            img_array_1 = np.array(image_1)
    
            fig_drop1 = px.imshow(img_array_1)
            fig_drop1.update_xaxes(visible=False)
            fig_drop1.update_yaxes(visible=False)
            fig_drop1.update_layout(
                title="High Correlated Features",
                dragmode="pan"
            )
    
            st.plotly_chart(fig_drop1, use_container_width=True, key="drop_tab_1")
    
            # Second image
            image_2 = Image.open("V2_drop_features.png")
            img_array_2 = np.array(image_2)
    
            fig_drop2 = px.imshow(img_array_2)
            fig_drop2.update_xaxes(visible=False)
            fig_drop2.update_yaxes(visible=False)
            fig_drop2.update_layout(
                title="Dropped Features",
                dragmode="pan"
            )
    
            st.plotly_chart(fig_drop2, use_container_width=True, key="drop_tab_2")

    
#########################################################################################################################################################################
#######################################################################################################################################################################

elif page == "V2.1":
    
    _platform_sidebar_title("🔍 FlipOse-RE-Analytics-V2.1")  # DXB-4
    
    # Sidebar navigation
    sidebar_option = st.sidebar.radio("Choose Section", [
        "📂 Data Understanding",
        "📊 EDA & Feature Engineering",
        "📈 Model Results",
        "validation",
        "🤖 Model Input / Prediction"
    ])
    drop_col = ['Unnamed: 0']  # list instead of string
    
    train_file_path1 = "df_trained_dataset_6000.csv"  # Replace with your CSV path
    test_file_path = "test_data_20 areas_1.csv"  # Replace with your CSV path
    train_file_path = "over_all_dataset_og.csv"
    forecasting_data = "forcast_model_16_25.csv"
    # --- Load Train Data ---
    try:
        df_train = pd.read_csv(train_file_path)
        # Drop columns if they exist
        df_train = df_train.drop(columns=[col for col in drop_col if col in df_train.columns])
        # st.dataframe(df_train)
    except FileNotFoundError:
        st.error(f"Training file not found: {train_file_path}")
    
    # --- Load Test Data ---
    try:
        df_test = pd.read_csv(test_file_path)
        df_test = df_test.drop(columns=[col for col in drop_col if col in df_test.columns])
        # st.dataframe(df_test)
    except FileNotFoundError:
        st.error(f"Test file not found: {test_file_path}")
        # --- Load forcast raw Data ---
    try:
        df_forecast_raw = pd.read_csv(forecasting_data)
        df_forecast_raw = df_forecast_raw.drop(columns=[col for col in drop_col if col in df_forecast_raw.columns])
        # st.dataframe(df_test)
    except FileNotFoundError:
        st.error(f"Test file not found: {df_forecast_raw}")


        
    # --- Data Files Tab with inner tabs ---
    if sidebar_option == "📂 Data Understanding":
        #st.header("📂 Data Files Overview")
        
        # Create inner tabs for Training and Test data
        tab1, tab2,tab3,tab4 = st.tabs(["Overview","Train Data","pareto_analysis","forecast_data_raw"])
        
        # --- Training Data Tab ---
        with tab1:  
            st.subheader("Data Overview")
            st.markdown("""
            - We have considered **data from 2022 to June 2025**.
            - **Property usage**: Residential only.
            - **Property type**: Units only.
            """)
            
            st.subheader("🛠️ Feature Engineering")
            st.markdown("""
            -  **18 areas** filtered having more than **6,000 records**.
            - For these areas 6000 sample records have taken into consideration for the model.
            -
            - Features considered from **user perspective**:
              - Rooms
              - Procedure area
              - Floor bins
              - Has parking
              - Swimming pools
              - Elevators
              - Nearby metro
              - Has balcony
            """)
            
            st.subheader("🤖 Models Used")
            st.markdown("""
            1. **Decision Tree** – for regression (price prediction). (2022-2025)
            2. **Auto ARIMA** – for time series forecasting.  (2016-2025)
            -----------------------------------------------------------------
            3. **Final prediction = regresion prediction * Growth factor (forcast Model)
            """)

    
        with tab2:
            import streamlit as st
            import pandas as pd
            
            def data_summary(df: pd.DataFrame):
                """Return dataframe summary for Streamlit display."""
                summary = pd.DataFrame({
                    "DataType": df.dtypes.astype(str),
                    "Non-Null Count": df.notnull().sum(),
                    "Missing Values": df.isnull().sum(),
                    "Unique Values": df.nunique(),
                    # Convert to string so Streamlit/PyArrow can handle it
                    "Sample Unique (first 10)": [", ".join(map(str, df[col].unique()[:10])) for col in df.columns]
                })
                return summary
            
            #st.title("📊 Dataset Summary")
            
            # Example: load your dataset
            # df_train = pd.read_csv("your_dataset.csv")
            
            # Show dataset shape
            st.write(f"**Total Rows:** {df_train.shape[0]}")
            st.write(f"**Total Columns:** {df_train.shape[1]}")
            
            # Show preview of data
            st.subheader("🔎 Data Preview")
            st.dataframe(df_train.sample(10))
            
            # Show summary
            st.subheader("📑 Column-wise Summary")
            summary = data_summary(df_train)
            st.dataframe(summary)

        with tab3:
            
            import streamlit as st
            import plotly.graph_objects as go
            pareto_df = pd.read_csv('pareto_df_22_25.csv')
            pareto_df = pareto_df.drop(columns=[col for col in drop_col if col in pareto_df.columns])
            #st.subheader("📈 Area Wise Records")
            
            # --- Find the 80% threshold from your existing table ---
            threshold_index = pareto_df[pareto_df['cum_percent'] >= 80].index.min()
            threshold_area = pareto_df.loc[threshold_index, 'area_name_en']
            threshold_value = pareto_df.loc[threshold_index, 'cum_percent']
            
            # --- Build Plotly chart ---
            fig = go.Figure()
            
            # Bar chart for record counts
            fig.add_trace(go.Bar(
                x=pareto_df['area_name_en'],
                y=pareto_df['count'],
                name='Record Count',
                marker_color='steelblue',
                yaxis='y1'
            ))
            
            # Line chart for cumulative %
            fig.add_trace(go.Scatter(
                x=pareto_df['area_name_en'],
                y=pareto_df['cum_percent'],
                name='Cumulative %',
                yaxis='y2',
                mode='lines+markers',
                marker=dict(color='darkorange'),
                line=dict(width=2)
            ))
            
            # --- Add 80% horizontal line ---
            fig.add_hline(
                y=80,
                line_dash="dash",
                line_color="red",
                annotation_text="80% Threshold",
                annotation_position="top left"
            )
            
            # --- Add vertical line at threshold area ---
            fig.add_vline(
                x=threshold_index,
                line_dash="dot",
                line_color="red",
                annotation_text=f"{threshold_area} ({threshold_value:.1f}%)",
                annotation_position="top right"
            )
            
            # --- Layout settings ---
            fig.update_layout(
                title='Pareto Chart - Area Wise Records (with 80% Line)',
                xaxis=dict(title='Area Name', tickangle=45, showgrid=False),
                yaxis=dict(title='Record Count'),
                yaxis2=dict(title='Cumulative %', overlaying='y', side='right', range=[0, 110]),
                legend=dict(x=0.75, y=1.15, orientation='h'),
                height=650,
                width=1100,
                template='plotly_white'
            )
            
            # --- Display chart ---
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(pareto_df)
            
        # --- Test Data Tab ---
        with tab4:
            import streamlit as st
            import pandas as pd
            
            def data_summary(df: pd.DataFrame):
                """Return dataframe summary for Streamlit display."""
                summary = pd.DataFrame({
                    "DataType": df.dtypes.astype(str),
                    "Non-Null Count": df.notnull().sum(),
                    "Missing Values": df.isnull().sum(),
                    "Unique Values": df.nunique(),
                    # Convert to string so Streamlit/PyArrow can handle it
                    "Sample Unique (first 10)": [", ".join(map(str, df[col].unique()[:10])) for col in df.columns]
                })
                return summary
            
            #st.title("📊 Dataset Summary")
            
            # Example: load your dataset
            # df_train = pd.read_csv("your_dataset.csv")
            
            # Show dataset shape
            st.write(f"**Total Rows:** {df_forecast_raw.shape[0]}")
            st.write(f"**Total Columns:** {df_forecast_raw.shape[1]}")
            
            # Show preview of data
            st.subheader("🔎 Data Preview")
            st.dataframe(df_forecast_raw.sample(10))
            
            # Show summary
            st.subheader("📑 Column-wise Summary")
            summary = data_summary(df_forecast_raw)
            st.dataframe(summary)
        
    # --- EDA & Feature Engineering Tab ---
    if sidebar_option == "📊 EDA & Feature Engineering":
        #st.header("📊 EDA & Feature Engineering")
        
        main_tabs = st.tabs(["Price_trend_areawise", "Price_trend_columnwise","Column-wise Analysis"])
        with main_tabs[0]:
            import streamlit as st
            import pandas as pd
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import os
            
            # -------------------------
            # 1️⃣ Time period helper
            # -------------------------
            def create_time_period_column(df, time_period):
                df = df.copy()
                df['instance_date'] = pd.to_datetime(df['instance_date'])
                
                if time_period == 'Daily':
                    df['time_period'] = df['instance_date'].dt.strftime('%Y-%m-%d')
                    df['sort_key'] = df['instance_date']
                elif time_period == 'Weekly':
                    df['time_period'] = df['instance_date'].dt.strftime('W%U %Y')
                    df['sort_key'] = df['instance_date'] - pd.to_timedelta(df['instance_date'].dt.weekday, unit='d')  # Monday of week
                elif time_period == 'Monthly':
                    df['time_period'] = df['instance_date'].dt.strftime('%b %Y')
                    df['sort_key'] = df['instance_date'].values.astype('datetime64[M]')
                elif time_period == 'Quarterly':
                    df['time_period'] = 'Q' + df['instance_date'].dt.quarter.astype(str) + ' ' + df['instance_date'].dt.year.astype(str)
                    df['sort_key'] = pd.PeriodIndex(df['instance_date'], freq='Q').start_time
                elif time_period == 'Half-Yearly':
                    df['half_year'] = ((df['instance_date'].dt.month - 1) // 6) + 1
                    df['time_period'] = 'H' + df['half_year'].astype(str) + ' ' + df['instance_date'].dt.year.astype(str)
                    # Sort key as first day of half-year
                    df['sort_key'] = df['instance_date'].dt.year.astype(str) + '-' + df['half_year'].astype(str)
                    df['sort_key'] = pd.to_datetime(df['instance_date'].dt.year.astype(str) + '-' + ((df['half_year']-1)*6 + 1).astype(str) + '-01')
                elif time_period == 'Yearly':
                    df['time_period'] = df['instance_date'].dt.strftime('%Y')
                    df['sort_key'] = pd.to_datetime(df['instance_date'].dt.year.astype(str) + '-01-01')
                
                return df
            
            # -------------------------
            # 2️⃣ Create area box plot function
            # -------------------------
            def create_area_box_plot(df, time_period, plot_title="Area Analysis"):
                df = create_time_period_column(df, time_period)
                
                # Calculate stats per period
                box_stats = []
                for period, group in df.groupby('time_period'):
                    vals = group['meter_sale_price']
                    q1 = vals.quantile(0.25)
                    q3 = vals.quantile(0.75)
                    iqr = q3 - q1
                    lower = q1 - 1.5*iqr
                    upper = q3 + 1.5*iqr
                    median = vals.median()
                    outliers = vals[(vals < lower) | (vals > upper)]
                    
                    # Impute outliers
                    s_imputed = vals.copy()
                    if len(outliers) > 0:
                        s_imputed[outliers.index] = vals.rolling(window=3, center=True, min_periods=1).median().loc[outliers.index]
                    
                    box_stats.append({
                        'period': period,
                        'vals': vals,
                        'median': median,
                        'imputed_median': s_imputed.median(),
                        'n_records': len(vals),
                        'lower': lower,
                        'upper': upper,
                        'sort_key': group['sort_key'].min()  # Use for ordering
                    })
                
                # Sort by sort_key
                box_stats = sorted(box_stats, key=lambda x: x['sort_key'])
                
                x_periods = [p['period'] for p in box_stats]
                y_original = [p['median'] for p in box_stats]
                y_imputed = [p['imputed_median'] for p in box_stats]
                x_keys = [p['sort_key'] for p in box_stats]
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Box plots
                for i, stats in enumerate(box_stats):
                    fig.add_trace(go.Box(
                        y=stats['vals'],
                        x=[stats['sort_key']]*len(stats['vals']),
                        name='Box Plot',
                        marker_color='lightblue',
                        line=dict(color='blue'),
                        boxpoints='outliers',
                        showlegend=True if i==0 else False,
                        width=0.4,
                        hovertemplate=(
                            f"<b>Period:</b> {stats['period']}<br>"
                            f"Min: {stats['lower']:.1f}<br>"
                            f"Median: {stats['median']:.1f}<br>"
                            f"Max: {stats['upper']:.1f}<br>"
                            f"Outliers: {len(stats['vals'][(stats['vals'] < stats['lower']) | (stats['vals'] > stats['upper'])])}<br>"
                            f"Records: {stats['n_records']}"
                        )
                    ), secondary_y=False)
                    
                    # Record count bars
                    fig.add_trace(go.Bar(
                        x=[stats['sort_key']],
                        y=[stats['n_records']],
                        name='No. of Records',
                        marker_color='lightgray',
                        opacity=0.5,
                        showlegend=False
                    ), secondary_y=True)
                
                # Original median line
                fig.add_trace(go.Scatter(
                    x=x_keys,
                    y=y_original,
                    mode='lines+markers',
                    name='Original Median',
                    line=dict(color='blue'),
                    marker=dict(size=8)
                ), secondary_y=False)
                
                # Imputed median line
                fig.add_trace(go.Scatter(
                    x=x_keys,
                    y=y_imputed,
                    mode='lines+markers',
                    name='Imputed Median',
                    line=dict(color='orange', dash='dash'),
                    marker=dict(size=8)
                ), secondary_y=False)
                
                # Layout
                fig.update_layout(
                    title=plot_title,
                    xaxis_title="Period",
                    yaxis_title="Meter Sale Price",
                    yaxis2_title="No. of Records",
                    template="plotly_white",
                    boxmode='group',
                    height=600,
                    legend=dict(x=0, y=1)
                )
                
                # Show proper period labels
                fig.update_xaxes(
                    tickvals=x_keys,
                    ticktext=x_periods,
                    tickangle=45
                )
                
                return fig
            
            # -------------------------
            # 3️⃣ Main Streamlit App
            # -------------------------
            def main():
               # st.title("📊 Area-wise Meter Sale Price Analysis")
                
                # Dataset selection
                st.sidebar.header("Dataset Selection")
                dataset_options = {
                    "fore_cast_raw_data" : "forcast_model_16_25.csv",
                    "Actual_data": "over_all_dataset_og.csv",
                    #"Data without_outliers": "over_all_dataset.csv",
                    "Areas with 6000": "df_trained_dataset_6000.csv"
                }
                
                selected_dataset = st.sidebar.selectbox("Choose Dataset", options=list(dataset_options.keys()))
                file_path = dataset_options[selected_dataset]
                
                if not os.path.exists(file_path):
                    st.error(f"File not found: {file_path}")
                    return
                
                df = pd.read_csv(file_path)
                required_columns = ['instance_date', 'area_name_en', 'meter_sale_price']
                missing = [c for c in required_columns if c not in df.columns]
                if missing:
                    st.error(f"Missing required columns: {', '.join(missing)}")
                    return
                
                tabs = st.tabs(["📈 Whole Data Analysis", "🏘️ Area-wise Analysis"])
                
                # Whole Data Tab
                with tabs[0]:
                    time_period_whole = st.selectbox("Select Time Period", ['Daily','Weekly','Monthly','Quarterly','Half-Yearly','Yearly'], index=2, key="whole_time_period")
                    st.plotly_chart(create_area_box_plot(df, time_period_whole, "Whole Dataset Analysis"), use_container_width=True)
                
                # Area-wise Tab
                with tabs[1]:
                    areas_all = ["All Areas"] + sorted(list(df['area_name_en'].unique()))
                    selected_area = st.selectbox("Select Area", areas_all, index=0, key="area_select")
                    time_period_area = st.selectbox("Select Time Period", ['Daily','Weekly','Monthly','Quarterly','Half-Yearly','Yearly'], index=2, key="area_time_period")
                    
                    if selected_area != "All Areas":
                        df_area = df[df['area_name_en'] == selected_area]
                        title = f"{selected_area} Analysis"
                    else:
                        df_area = df.copy()
                        title = "All Areas Analysis"
                    
                    st.plotly_chart(create_area_box_plot(df_area, time_period_area, title), use_container_width=True)
            
            if __name__ == "__main__":
                main()
        with main_tabs[1]:
            import streamlit as st
            import pandas as pd
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import os
        
            # -------------------------
            # 1️⃣ Time period helper
            # -------------------------
            def create_time_period_column(df, time_period):
                df = df.copy()
                df['instance_date'] = pd.to_datetime(df['instance_date'])
                
                if time_period == 'Daily':
                    df['time_period'] = df['instance_date'].dt.strftime('%Y-%m-%d')
                    df['sort_key'] = df['instance_date']
                elif time_period == 'Weekly':
                    df['time_period'] = df['instance_date'].dt.strftime('W%U %Y')
                    df['sort_key'] = df['instance_date'] - pd.to_timedelta(df['instance_date'].dt.weekday, unit='d')  # Monday of week
                elif time_period == 'Monthly':
                    df['time_period'] = df['instance_date'].dt.strftime('%b %Y')
                    df['sort_key'] = df['instance_date'].values.astype('datetime64[M]')
                elif time_period == 'Quarterly':
                    df['time_period'] = 'Q' + df['instance_date'].dt.quarter.astype(str) + ' ' + df['instance_date'].dt.year.astype(str)
                    df['sort_key'] = pd.PeriodIndex(df['instance_date'], freq='Q').start_time
                elif time_period == 'Half-Yearly':
                    df['half_year'] = ((df['instance_date'].dt.month - 1) // 6) + 1
                    df['time_period'] = 'H' + df['half_year'].astype(str) + ' ' + df['instance_date'].dt.year.astype(str)
                    # Sort key as first day of half-year
                    df['sort_key'] = df['instance_date'].dt.year.astype(str) + '-' + df['half_year'].astype(str)
                    df['sort_key'] = pd.to_datetime(df['instance_date'].dt.year.astype(str) + '-' + ((df['half_year']-1)*6 + 1).astype(str) + '-01')
                elif time_period == 'Yearly':
                    df['time_period'] = df['instance_date'].dt.strftime('%Y')
                    df['sort_key'] = pd.to_datetime(df['instance_date'].dt.year.astype(str) + '-01-01')
                
                return df
            
            # -------------------------
            # 2️⃣ Create categorical trend plot function - FIXED VERSION
            # -------------------------
            def create_categorical_trend_plot(df, selected_column, time_period, area_name="Area"):
                try:
                    df_processed = create_time_period_column(df, time_period)
                    
                    # Convert numerical columns to categorical bins if needed
                    if pd.api.types.is_numeric_dtype(df_processed[selected_column]):
                        # Create bins for numerical columns
                        if df_processed[selected_column].nunique() > 10:
                            # For numerical columns with many unique values, create bins
                            df_processed[selected_column] = pd.cut(df_processed[selected_column], bins=5, duplicates='drop')
                        else:
                            # For numerical columns with few unique values, keep as is but convert to string
                            df_processed[selected_column] = df_processed[selected_column].astype(str)
                    
                    # Group by time period and selected column, calculate average meter_sale_price
                    trend_data = df_processed.groupby(['time_period', 'sort_key', selected_column])['meter_sale_price'].mean().reset_index()
                    
                    # Sort by sort_key to ensure chronological order
                    trend_data = trend_data.sort_values('sort_key')
                    
                    # Get unique categories for legend
                    categories = trend_data[selected_column].unique()
                    
                    fig = go.Figure()
                    
                    # Add a line for each category
                    for category in categories:
                        category_data = trend_data[trend_data[selected_column] == category]
                        
                        # Ensure the category data is also sorted by sort_key
                        category_data = category_data.sort_values('sort_key')
                        
                        fig.add_trace(go.Scatter(
                            x=category_data['time_period'],  # Use the string labels for display
                            y=category_data['meter_sale_price'],
                            mode='lines+markers',
                            name=str(category),
                            hovertemplate=(
                                f"<b>Period:</b> %{{x}}<br>" +
                                f"<b>{selected_column}:</b> {category}<br>" +
                                f"<b>Avg Price:</b> %{{y:.2f}}<br>" +
                                "<extra></extra>"
                            )
                        ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"{area_name} - {selected_column} Analysis",
                        xaxis_title=time_period,
                        yaxis_title="Average Meter Sale Price",
                        template="plotly_white",
                        height=500,
                        showlegend=True,
                        legend=dict(
                            title=selected_column,
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=1.02
                        )
                    )
                    
                    # Set up x-axis to maintain chronological order
                    # Get unique time periods in sorted order
                    unique_periods = trend_data[['time_period', 'sort_key']].drop_duplicates().sort_values('sort_key')
                    
                    fig.update_xaxes(
                        categoryorder='array',
                        categoryarray=unique_periods['time_period'].tolist(),
                        tickangle=45
                    )
                    
                    return fig, trend_data
                    
                except Exception as e:
                    st.error(f"Error creating trend plot: {str(e)}")
                    return go.Figure(), pd.DataFrame()
            
            # -------------------------
            # 3️⃣ Get available columns (excluding specified columns)
            # -------------------------
            def get_available_columns(df):
                # Columns to exclude
                excluded_columns = [
                    'instance_date', 'area_name_en', 'meter_sale_price', 
                    'procedure_area', 'Unnamed: 0'
                ]
                
                # Get all columns except the excluded ones
                available_columns = [col for col in df.columns if col not in excluded_columns]
                
                return available_columns
            
            # -------------------------
            # 4️⃣ Dataset selection and main app
            # -------------------------
            
            # Dataset selection
            st.sidebar.header("Dataset Selection - Price Trend Columnwise")
            dataset_options = {
                "Actual_data": "over_all_dataset_og.csv"
            }
            
            selected_dataset = st.sidebar.selectbox(
                "Choose Dataset", 
                options=list(dataset_options.keys()),
                key="dataset_select_columnwise"
            )
            file_path = dataset_options[selected_dataset]
            
            if not os.path.exists(file_path):
                st.error(f"File not found: {file_path}")
                st.stop()
            
            try:
                df = pd.read_csv(file_path)
                required_columns = ['instance_date', 'area_name_en', 'meter_sale_price']
                missing = [c for c in required_columns if c not in df.columns]
                if missing:
                    st.error(f"Missing required columns: {', '.join(missing)}")
                    st.stop()
            except Exception as e:
                st.error(f"Error loading dataset: {str(e)}")
                st.stop()
            
            # Create tabs
            tabs = st.tabs(["📈 Whole Data Analysis", "🏘️ Area-wise Analysis"])
            
            # Whole Data Analysis Tab
            with tabs[0]:
                st.header("Whole Dataset Analysis")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    time_period_whole = st.selectbox(
                        "Select Time Period", 
                        ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly'], 
                        index=2, 
                        key="whole_time_period_columnwise"
                    )
                    
                    # Get available columns for analysis
                    available_columns_whole = get_available_columns(df)
                    if available_columns_whole:
                        selected_column_whole = st.selectbox(
                            "Select Column for Analysis",
                            options=available_columns_whole,
                            help="Choose any column to analyze price trends by category",
                            key="whole_column_select_columnwise"
                        )
                        
                        # Show column info
                        col_info = f"Data Type: {df[selected_column_whole].dtype} | Unique Values: {df[selected_column_whole].nunique()}"
                        st.caption(col_info)
                        
                    else:
                        st.warning("No available columns found in the dataset")
                        selected_column_whole = None
                
                with col2:
                    if selected_column_whole:
                        # Create and display the plot for whole data with column breakdown
                        fig_whole, trend_data_whole = create_categorical_trend_plot(
                            df, selected_column_whole, time_period_whole, "Whole Dataset"
                        )
                        st.plotly_chart(fig_whole, use_container_width=True)
                    else:
                        st.info("Please select a column to view the analysis")
                
            
            # Area-wise Analysis Tab
            with tabs[1]:
                st.header("Area-wise Analysis")
                
                # Flow: Area → Column → Time Period
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    areas_all = ["All Areas"] + sorted(list(df['area_name_en'].unique()))
                    selected_area = st.selectbox(
                        "Select Area", 
                        areas_all, 
                        index=0, 
                        key="area_select_columnwise"
                    )
                    
                    if selected_area != "All Areas":
                        df_area = df[df['area_name_en'] == selected_area]
                        area_title = selected_area
                    else:
                        df_area = df.copy()
                        area_title = "All Areas"
                
                with col2:
                    # Get available columns for the selected area
                    available_columns_area = get_available_columns(df_area)
                    if available_columns_area:
                        selected_column_area = st.selectbox(
                            "Select Column for Analysis",
                            options=available_columns_area,
                            help="Choose any column to analyze price trends by category",
                            key="area_column_select_columnwise"
                        )
                        
                        # Show column info
                        if selected_column_area in df_area.columns:
                            col_info = f"Data Type: {df_area[selected_column_area].dtype} | Unique Values: {df_area[selected_column_area].nunique()}"
                            st.caption(col_info)
                    else:
                        st.warning("No available columns found for selected area")
                        selected_column_area = None
                
                with col3:
                    time_period_area = st.selectbox(
                        "Select Time Period",
                        options=['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly'],
                        index=2,
                        key="area_time_period_columnwise"
                    )
                
                # Create and display the plot for area-wise data with column breakdown
                if selected_column_area:
                    fig_area, trend_data_area = create_categorical_trend_plot(
                        df_area, selected_column_area, time_period_area, area_title
                    )
                    st.plotly_chart(fig_area, use_container_width=True)
                else:
                    st.info("Please select a column to view the analysis")
        
                    
                    # Data table
                    with st.expander("View Detailed Data"):
                        display_df = trend_data_area[['time_period', selected_column_area, 'meter_sale_price', 'sort_key']].copy()
                        display_df = display_df.sort_values('sort_key')  # Sort by chronological order
                        display_df['meter_sale_price'] = display_df['meter_sale_price'].round(2)
                        display_df = display_df.rename(columns={
                            'time_period': 'Period',
                            selected_column_area: 'Category',
                            'meter_sale_price': 'Average Price (₹)'
                        })
                        display_df = display_df.drop('sort_key', axis=1)  # Remove sort_key from display
                        st.dataframe(display_df, use_container_width=True)
        with main_tabs[2]:            
            import streamlit as st
            import pandas as pd
            import plotly.express as px
            
            # =========================
            # Load datasets
            # =========================
            df_before = pd.read_csv("over_all_dataset_og.csv")
            df_before = df_before.drop(columns=[col for col in drop_col if col in df_before.columns])
            df_after = pd.read_csv("over_all_dataset.csv")
            df_after = df_after.drop(columns=[col for col in drop_col if col in df_after.columns])
            
            
            # Select which dataset to view
            dataset_choice = st.radio(
                "Choose Dataset:",
                ("Before Outlier Removal", "After Outlier Removal"),
                horizontal=True
            )
            
            # Assign based on choice
            if dataset_choice == "Before Outlier Removal":
                df_train = df_before.copy()
            else:
                df_train = df_after.copy()
            
            # =========================
            # Main Tabs
            # =========================
            main_tabs = st.tabs(["Distributions & Metrics", "Area-wise Analysis"])
            
            # =========================
            # 1️⃣ Distributions & Metrics
            # =========================
            with main_tabs[0]:
                sub_tab1, sub_tab2 = st.tabs(["Distribution", "Metrics"])
                
                # --- Distribution Tab ---
                with sub_tab1:
                    #st.subheader(f"Categorical Columns Distribution — {dataset_choice}")
                    
                    cat_cols = ['rooms_en','floor_bin','swimming_pool','balcony','elevator', 
                                'metro','has_parking','area_name_en','property_sub_type_en']
                    cat_cols_existing = [col for col in cat_cols if col in df_train.columns]
                    
                    if not cat_cols_existing:
                        st.warning("No categorical columns found in the dataset.")
                    else:
                        for col in cat_cols_existing:
                            chart_df = df_train.groupby(col).agg(
                                nRecords=('meter_sale_price','count'),
                                Avg_Meter_Sale_Price=('meter_sale_price','mean')
                            ).reset_index()
                            
                            fig = px.bar(chart_df, x=col, y='nRecords', color=col,
                                         title=f"{col} Distribution vs Avg Meter Sale Price — {dataset_choice}")
                            fig.add_scatter(x=chart_df[col], y=chart_df['Avg_Meter_Sale_Price'],
                                            mode='lines+markers', name='Avg Meter Sale Price', yaxis='y2')
                            fig.update_layout(
                                yaxis2=dict(title='Avg Meter Sale Price', overlaying='y', side='right')
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                # --- Metrics Tab ---
                with sub_tab2:
                    #st.subheader(f"Metrics on meter_sale_price & procedure_area — {dataset_choice}")
                    
                    numeric_cols = ['meter_sale_price', 'procedure_area']
                    numeric_cols_existing = [col for col in numeric_cols if col in df_train.columns]
                    
                    if not numeric_cols_existing:
                        st.warning("No numeric columns found in the dataset.")
                    else:
                        for col in numeric_cols_existing:
                            st.markdown(f"### {col} Distribution")
                            fig_hist = px.histogram(df_train, x=col, nbins=50, marginal="box",
                                                    title=f"{col} Distribution with Boxplot — {dataset_choice}")
                            st.plotly_chart(fig_hist, use_container_width=True)
                        
                        st.dataframe(df_train[numeric_cols_existing].describe().round(2))
            
            # =========================
            # 2️⃣ Area-wise Analysis
            # =========================
            with main_tabs[1]:
                #st.subheader(f"Area-wise Analysis — {dataset_choice}")
                
                if 'area_name_en' not in df_train.columns:
                    st.warning("'area_name_en' column not found in dataset.")
                else:
                    areas = df_train['area_name_en'].unique().tolist()
                    selected_area = st.selectbox("Select Area", areas, key=f"select_area_{dataset_choice}")
                    df_area = df_train[df_train['area_name_en'] == selected_area]
                    
                    area_tabs = st.tabs(["Dimensions", "Metrics", "Categorical Distributions"])
                    
                    # --- Dimensions Tab ---
                    with area_tabs[0]:
                        #st.subheader(f"Dimensions for {selected_area} — {dataset_choice}")
                        st.dataframe(df_area.describe(include='all').transpose())
                    
                    # --- Metrics Tab ---
                    with area_tabs[1]:
                        #st.subheader(f"Metrics on meter_sale_price & procedure_area for {selected_area} — {dataset_choice}")
                        
                        numeric_cols = ['meter_sale_price', 'procedure_area']
                        numeric_cols_existing = [col for col in numeric_cols if col in df_area.columns]
                        
                        if not numeric_cols_existing:
                            st.warning("No numeric columns found in the area dataset.")
                        else:
                            for col in numeric_cols_existing:
                                st.markdown(f"### {col} Distribution for {selected_area}")
                                fig_area = px.histogram(df_area, x=col, nbins=50, marginal="box",
                                                        title=f"{col} Distribution with Boxplot for {selected_area} — {dataset_choice}")
                                st.plotly_chart(fig_area, use_container_width=True)
                            
                            st.dataframe(df_area[numeric_cols_existing].describe().round(2))
                    
                    # --- Categorical Distributions Tab ---
                    with area_tabs[2]:
                       # st.subheader(f"Categorical Column Distributions for {selected_area} — {dataset_choice}")
                        
                        cat_cols = ['rooms_en','floor_bin','swimming_pool','balcony','elevator', 
                                    'metro','has_parking','property_sub_type_en']
                        cat_cols_existing = [col for col in cat_cols if col in df_area.columns]
                        
                        if not cat_cols_existing:
                            st.warning("No categorical columns found for this area.")
                        else:
                            for col in cat_cols_existing:
                                chart_df = df_area.groupby(col).agg(
                                    nRecords=('meter_sale_price','count'),
                                    Avg_Meter_Sale_Price=('meter_sale_price','mean')
                                ).reset_index()
                                
                                fig = px.bar(chart_df, x=col, y='nRecords', color=col,
                                             title=f"{col} Distribution vs Avg Meter Sale Price for {selected_area} — {dataset_choice}")
                                fig.add_scatter(x=chart_df[col], y=chart_df['Avg_Meter_Sale_Price'],
                                                mode='lines+markers', name='Avg Meter Sale Price', yaxis='y2')
                                fig.update_layout(
                                    yaxis2=dict(title='Avg Meter Sale Price', overlaying='y', side='right')
                                )
                                st.plotly_chart(fig, use_container_width=True, key=f"{col}_{selected_area}_{dataset_choice}")



    import pandas as pd
    import numpy as np
    import pickle
    import glob
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    if sidebar_option == "📈 Model Results":
        # =========================
        # 0️⃣ IMPORT REQUIRED LIBRARIES
        # =========================
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        import numpy as np
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import plotly.express as px
        import pandas as pd
        import pickle
        
        # =========================
        # 1️⃣ LOAD ONEHOT ENCODER
        # =========================
        try:
            with open("onehot_encoder.pkl", "rb") as f:
                ohe = pickle.load(f)
            #st.sidebar.success("✅ OneHot Encoder loaded")
        except Exception as e:
            st.error(f"❌ Error loading OneHot encoder: {e}")
            st.stop()
        
        file_options = {
            "Test_data": "test_data_20 areas_1.csv",
            "Test_data_sample_50": "all_values_area_data_test.csv",
            "all_data_sample_50": "all_values_area_data.csv"
        }
        
        # Create selectbox
        selected_file_label = st.selectbox("Choose data file to load:", options=list(file_options.keys()))
        file_path = file_options[selected_file_label]
        
        # =========================
        # 2️⃣ LOAD AREA-WISE MODELS
        # =========================
        area_models = {}
        area_files = [
            "dt_model_Al_Barsha_South_Fifth.pkl", "dt_model_Al_Barsha_South_Fourth.pkl", 
            "dt_model_Al_Barshaa_South_Third.pkl", "dt_model_Al_Hebiah_Fourth.pkl",
            "dt_model_Al_Khairan_First.pkl", "dt_model_Al_Merkadh.pkl", 
            "dt_model_Al_Thanyah_Fifth.pkl", "dt_model_Al_Warsan_First.pkl",
            "dt_model_Al_Yelayiss_2.pkl", "dt_model_Bukadra.pkl", 
            "dt_model_Burj_Khalifa.pkl", "dt_model_Business_Bay.pkl",
            "dt_model_Hadaeq_Sheikh_Mohammed_Bin_Rashid.pkl", "dt_model_Jabal_Ali_First.pkl",
            "dt_model_Madinat_Al_Mataar.pkl", "dt_model_Madinat_Dubai_Almelaheyah.pkl",
            "dt_model_Marsa_Dubai.pkl", "dt_model_Me'Aisem_First.pkl",
            "dt_model_Nadd_Hessa.pkl", "dt_model_Wadi_Al_Safa_5.pkl"
        ]
        
        for model_file in area_files:
            try:
                area_name = model_file.split("dt_model_")[1].replace(".pkl", "").replace("_", " ")
                with open(model_file, "rb") as f:
                    area_models[area_name] = pickle.load(f)
                #st.sidebar.success(f"✅ {area_name}")
            except FileNotFoundError:
                st.sidebar.warning(f"⚠️ {model_file} not found")
            except Exception as e:
                st.sidebar.error(f"❌ {model_file}: {str(e)}")
        
        # =========================
        # 3️⃣ STREAMLIT UI
        # =========================
        # Create tabs for different functionalities
        tab1, tab2, tab3 = st.tabs(["📊 Regression Model Prection", "🔮 Forcasting Model", "Regression+Forcasting"])
        
        with tab1:
            # Define drop_cols (you need to define this based on your actual columns)
            drop_cols = ['Unnamed: 0', 'instance_date', 'quarter', 'Year']  # Add your actual columns to drop
            
            # Create sub-tabs for Regression Model Prediction
            reg_tab1, reg_tab2 = st.tabs(["Model Metrics", "Feature Importance"])
            
            # -----------------------------
            # Load Data for Tab1
            # -----------------------------
            try:
                # Model metrics per area
                metrics_df = pd.read_csv('area_train_metrics.csv')  # Fixed: added .csv extension
                metrics_df = metrics_df.drop(columns=[col for col in drop_cols if col in metrics_df.columns])
                # Rename columns to match what the code expects
                column_mapping = {
                    'R2': 'r2',
                    'RMSE': 'rmse', 
                    'MAPE': 'mape'
                    # 'area_name_en' stays the same
                }
                
                metrics_df = metrics_df.rename(columns=column_mapping)
                # Feature importance per area
                feature_importance_df = pd.read_csv('area_feature_importances.csv')  # Fixed: added .csv extension
                feature_importance_df = feature_importance_df.drop(columns=[col for col in drop_cols if col in feature_importance_df.columns])
                
            except FileNotFoundError as e:
                st.error(f"❌ Data file not found: {e}")
            except Exception as e:
                st.error(f"❌ Error loading data: {e}")
            
            # -----------------------------
            # Sub-tab 1: Model Metrics
            # -----------------------------
            with reg_tab1:
                #st.subheader("📊 Model Metrics Comparison by Area")
                
                # Check if required columns exist
                required_cols = ['area_name_en', 'r2', 'mape', 'rmse']
                if all(col in metrics_df.columns for col in required_cols):
                    fig = go.Figure()
        
                    # R² (left axis)
                    fig.add_trace(go.Bar(
                        x=metrics_df['area_name_en'],
                        y=metrics_df['r2'],
                        name='R²',
                        marker_color='royalblue',
                        yaxis='y1'
                    ))
        
                    # MAPE (left axis)
                    fig.add_trace(go.Bar(
                        x=metrics_df['area_name_en'],
                        y=metrics_df['mape'],
                        name='MAPE (%)',
                        marker_color='lightseagreen',
                        yaxis='y1'
                    ))
        
                    # RMSE (right axis)
                    fig.add_trace(go.Bar(
                        x=metrics_df['area_name_en'],
                        y=metrics_df['rmse'],
                        name='RMSE',
                        marker_color='firebrick',
                        yaxis='y2'
                    ))
        
                    # Layout
                    fig.update_layout(
                        title='Model Performance by Area (R², MAPE, RMSE)',
                        xaxis=dict(title='Area Name', tickangle=45),
                        yaxis=dict(title='R² / MAPE (%)', side='left'),
                        yaxis2=dict(title='RMSE', overlaying='y', side='right', showgrid=False),
                        barmode='group',
                        legend=dict(title='Metrics', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                        template='plotly_white',
                        height=500
                    )
        
                    st.plotly_chart(fig, use_container_width=True)
        
                    # Optional: Show table
                    with st.expander("📋 View Actual Metrics Table"):
                        # Only format numeric columns that exist in the dataframe
                        format_dict = {}
                        if 'r2' in metrics_df.columns:
                            format_dict['r2'] = "{:.3f}"
                        if 'rmse' in metrics_df.columns:
                            format_dict['rmse'] = "{:,.0f}"
                        if 'mape' in metrics_df.columns:
                            format_dict['mape'] = "{:.2f}%"
                        
                        if format_dict:
                            st.dataframe(metrics_df.style.format(format_dict))
                        else:
                            st.dataframe(metrics_df)
            
            # -----------------------------
            # Sub-tab 2: Feature Importance
            # -----------------------------
            with reg_tab2:
                st.subheader("📊 Feature Importance by Area")
                
                # Check if required columns exist
                if 'area_name_en' in feature_importance_df.columns and len(feature_importance_df.columns) > 1:
                    fig2 = go.Figure()
            
                    # Add each feature as a line (skip the first column which is area_name_en)
                    for feature in feature_importance_df.columns[1:]:
                        fig2.add_trace(go.Scatter(
                            x=feature_importance_df['area_name_en'],
                            y=feature_importance_df[feature],
                            name=feature,
                            mode='lines+markers',  # This creates both lines and markers
                            line=dict(width=3),
                            marker=dict(size=8)
                        ))
            
                    fig2.update_layout(
                        title='Feature Importance Trends Across Areas',
                        xaxis=dict(title='Area Name', tickangle=45),
                        yaxis=dict(title='Importance Value'),
                        template='plotly_white',
                        height=500,
                        legend=dict(title='Features', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                        hovermode='x unified'  # Shows all values for a given area on hover
                    )
            
                    st.plotly_chart(fig2, use_container_width=True)
            
                    # Optional: Show table
                    with st.expander("📋 View Feature Importance Table"):
                        # Only format numeric columns, exclude the first column (area_name_en)
                        numeric_cols = feature_importance_df.columns[1:]
                        st.dataframe(feature_importance_df.style.format("{:.3f}", subset=numeric_cols))
                else:
                    st.error("❌ Required columns not found in feature importance data")
            # -----------------------------
            # Predictions Section
            # -----------------------------
            st.header("🎯 Model Predictions on Test Data")
            
            try:
                test_samples = pd.read_csv(file_path)
                test_samples = test_samples.drop(columns=[col for col in drop_cols if col in test_samples.columns])
                
                #st.subheader("📁 Test Data Preview")
                #st.dataframe(test_samples.head())
                
                # Remove unwanted columns including 'Unnamed: 0'
                columns_to_drop = ['Unnamed: 0', 'instance_date', 'quarter', 'area_name_en', 'Year']
                columns_to_drop = [col for col in columns_to_drop if col in test_samples.columns]
                
                X_test = test_samples.drop(columns=columns_to_drop + ['meter_sale_price'], errors='ignore')
                y_test = test_samples['meter_sale_price']
                
                # Identify categorical columns
                cat_cols = X_test.select_dtypes(include='object').columns.tolist()
        
                # Apply saved encoder
                if cat_cols:
                    X_cat_test = ohe.transform(X_test[cat_cols])
                    X_cat_test = pd.DataFrame(X_cat_test, columns=ohe.get_feature_names_out(cat_cols), index=X_test.index)
                    X_test = X_test.drop(columns=cat_cols)
                    X_test = pd.concat([X_test, X_cat_test], axis=1)
                
                # Ensure we only have numeric columns
                X_test = X_test.select_dtypes(include=[np.number])
                
                # =========================
                # PREDICTION & METRICS
                # =========================
                if st.button("🚀 Run Predictions", type="primary", key="predict_btn"):
                    if len(area_models) == 0:
                        st.error("❌ No models loaded. Please check model files.")
                        st.stop()
                    
                    y_pred_total = pd.Series(index=test_samples.index, dtype=float)
                    test_metrics = {}
                    area_predictions = {}
        
                    progress_bar = st.progress(0)
                    status_text = st.empty()
        
                    areas = test_samples['area_name_en'].unique()
                    for i, area in enumerate(areas):
                        status_text.text(f"Processing {area}... ({i+1}/{len(areas)})")
                        progress_bar.progress((i + 1) / len(areas))
                        
                        if area not in area_models:
                            st.warning(f"⚠️ Skipping area '{area}' (model not available)")
                            continue
        
                        model = area_models[area]
                        mask = test_samples['area_name_en'] == area
                        X_area_test = X_test.loc[mask]
                        y_area_test = y_test.loc[mask]
        
                        if len(X_area_test) > 0:
                            try:
                                y_pred = model.predict(X_area_test)
                                y_pred_total.loc[mask] = y_pred
        
                                # Metrics
                                r2 = r2_score(y_area_test, y_pred)
                                rmse = np.sqrt(mean_squared_error(y_area_test, y_pred))
                                mae = mean_absolute_error(y_area_test, y_pred)
        
                                test_metrics[area] = {
                                    'R2': round(r2, 4), 
                                    'RMSE': round(rmse, 2), 
                                    'MAE': round(mae, 2),
                                    'Samples': len(y_area_test),
                                    'Avg_Actual_Price': round(y_area_test.mean(), 2),
                                    'Avg_Predicted_Price': round(y_pred.mean(), 2)
                                }
                                
                                # Store predictions for plotting
                                area_predictions[area] = {
                                    'actual': y_area_test,
                                    'predicted': y_pred
                                }
                            except Exception as e:
                                st.error(f"❌ Error predicting for {area}: {e}")
                                continue
        
                    progress_bar.empty()
                    status_text.text("✅ Prediction completed!")
        
                    # =========================
                    # DISPLAY RESULTS
                    # =========================
                    if test_metrics:
                        test_metrics_df = pd.DataFrame(test_metrics).T
                        test_metrics_df = test_metrics_df.sort_values(by='R2', ascending=False)
                        
                        # Display metrics table
                        st.subheader("📈 Prediction Results")
                        st.dataframe(test_metrics_df.style.format({
                            'R2': '{:.4f}',
                            'RMSE': '{:.2f}',
                            'MAE': '{:.2f}',
                            'Avg_Actual_Price': '{:,.2f}',
                            'Avg_Predicted_Price': '{:,.2f}'
                        }), use_container_width=True)
                        
                        # Summary statistics
                        st.subheader("📊 Summary Statistics")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Areas Processed", len(test_metrics))
                        with col2:
                            avg_r2 = test_metrics_df['R2'].mean()
                            st.metric("Average R² Score", f"{avg_r2:.4f}")
                        with col3:
                            total_samples = test_metrics_df['Samples'].sum()
                            st.metric("Total Samples", total_samples)
                        with col4:
                            avg_rmse = test_metrics_df['RMSE'].mean()
                            st.metric("Average RMSE", f"{avg_rmse:.2f}")
                        
                        # Best and worst performing areas
                        col1, col2 = st.columns(2)
                        with col1:
                            best_area = test_metrics_df.loc[test_metrics_df['R2'].idxmax()]
                            st.metric("Best R² Score", 
                                     f"{best_area['R2']:.4f}", 
                                     f"{test_metrics_df['R2'].idxmax()}")
                        
                        with col2:
                            worst_area = test_metrics_df.loc[test_metrics_df['R2'].idxmin()]
                            st.metric("Worst R² Score", 
                                     f"{worst_area['R2']:.4f}", 
                                     f"{test_metrics_df['R2'].idxmin()}")
                        
                        # =========================
                        # VISUALIZATIONS FOR PREDICTIONS
                        # =========================
                        st.subheader("📊 Prediction Visualizations")
                        
                        # Tab for different visualizations
                        viz_tab1, viz_tab2, viz_tab3 = st.tabs(["📈 Performance Metrics", "🔍 Actual vs Predicted", "📊 Area wise Comparison"])
                        
                        with viz_tab1:
                            # R2 Score Bar Chart
                            fig_r2 = px.bar(
                                x=test_metrics_df.index,
                                y=test_metrics_df['R2'],
                                title="R² Scores by Area",
                                labels={'x': 'Area', 'y': 'R² Score'},
                                color=test_metrics_df['R2'],
                                color_continuous_scale="RdYlGn"
                            )
                            fig_r2.update_layout(height=500)
                            st.plotly_chart(fig_r2, use_container_width=True)
                            
                            # RMSE and MAE comparison
                            fig_errors = go.Figure()
                            fig_errors.add_trace(go.Bar(name='RMSE', x=test_metrics_df.index, y=test_metrics_df['RMSE']))
                            fig_errors.add_trace(go.Bar(name='MAE', x=test_metrics_df.index, y=test_metrics_df['MAE']))
                            fig_errors.update_layout(title="Error Metrics by Area", barmode='group', height=500)
                            st.plotly_chart(fig_errors, use_container_width=True)
                        
                        with viz_tab2:
                            # Scatter plots for actual vs predicted
                            selected_area = st.selectbox("Select Area for Detailed Analysis", list(area_predictions.keys()))
                            
                            if selected_area in area_predictions:
                                actual = area_predictions[selected_area]['actual']
                                predicted = area_predictions[selected_area]['predicted']
                                
                                fig_scatter = px.scatter(
                                    x=actual, y=predicted,
                                    title=f"Actual vs Predicted Prices - {selected_area}",
                                    labels={'x': 'Actual Price', 'y': 'Predicted Price'},
                                    trendline="ols"
                                )
                                
                                # Add perfect prediction line
                                max_val = max(actual.max(), predicted.max())
                                min_val = min(actual.min(), predicted.min())
                                fig_scatter.add_trace(go.Scatter(
                                    x=[min_val, max_val], y=[min_val, max_val],
                                    mode='lines', name='Perfect Prediction',
                                    line=dict(dash='dash', color='red')
                                ))
                                
                                fig_scatter.update_layout(height=500)
                                st.plotly_chart(fig_scatter, use_container_width=True)
                        
                        with viz_tab3:
                            # Price comparison chart
                            fig_prices = go.Figure()
                            fig_prices.add_trace(go.Bar(name='Actual Price', x=test_metrics_df.index, y=test_metrics_df['Avg_Actual_Price']))
                            fig_prices.add_trace(go.Bar(name='Predicted Price', x=test_metrics_df.index, y=test_metrics_df['Avg_Predicted_Price']))
                            fig_prices.update_layout(title="Average Actual vs Predicted Prices by Area", barmode='group', height=500)
                            st.plotly_chart(fig_prices, use_container_width=True)
                            
                            # Error percentage by area
                            error_percentage = ((test_metrics_df['Avg_Actual_Price'] - test_metrics_df['Avg_Predicted_Price']) / test_metrics_df['Avg_Actual_Price'] * 100).abs()
                            fig_error_pct = px.bar(
                                x=error_percentage.index,
                                y=error_percentage.values,
                                title="Absolute Error Percentage by Area",
                                labels={'x': 'Area', 'y': 'Error %'},
                                color=error_percentage.values,
                                color_continuous_scale="Reds"
                            )
                            fig_error_pct.update_layout(height=400)
                            st.plotly_chart(fig_error_pct, use_container_width=True)
                        
                        # Download results
                        results_df = test_samples.copy()
                        results_df['predicted_price'] = y_pred_total
                        results_df['prediction_error'] = results_df['meter_sale_price'] - results_df['predicted_price']
                        results_df['error_percentage'] = (results_df['prediction_error'] / results_df['meter_sale_price'] * 100).round(2)
                        
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Full Predictions CSV",
                            data=csv,
                            file_name="dubai_real_estate_predictions.csv",
                            mime="text/csv"
                        )
                            
                    else:
                        st.warning("No predictions were made. Check if area names match the trained models.")
                        
            except FileNotFoundError:
                st.error(f"❌ Test data file '{file_path}' not found. Please make sure the file exists.")
            except Exception as e:
                st.error(f"❌ Error loading test data: {str(e)}")
                
    
    ####################################################################________________________>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>______________________________________################################################
        with tab3:
            #st.header("🔮 Price Forecasting")
            #st.markdown("Area-wise predictions with growth factor projections")
            
            import streamlit as st
            import pandas as pd
            import numpy as np
            import pickle
            import plotly.express as px
            import plotly.graph_objects as go
            import os
            from datetime import datetime
            
            # =========================
            # INITIALIZATION & SETUP
            # =========================
            
            # Initialize session state for models if not exists
            if 'area_models' not in st.session_state:
                st.session_state.area_models = {}
            if 'ohe' not in st.session_state:
                st.session_state.ohe = None
            
            # Define global variables
            file_path = "test_data_20 areas_1.csv"
            drop_col = ['Unnamed: 0']
            
            # Load models and preprocessing objects
            @st.cache_resource
            def load_models_and_preprocessing():
                """Load trained models and preprocessing objects"""
                try:
                    # Load area models
                    area_models = {}
                    area_files = [
                        "dt_model_Al_Barsha_South_Fifth.pkl", "dt_model_Al_Barsha_South_Fourth.pkl", 
                        "dt_model_Al_Barshaa_South_Third.pkl", "dt_model_Al_Hebiah_Fourth.pkl",
                        "dt_model_Al_Khairan_First.pkl", "dt_model_Al_Merkadh.pkl", 
                        "dt_model_Al_Thanyah_Fifth.pkl", "dt_model_Al_Warsan_First.pkl",
                        "dt_model_Al_Yelayiss_2.pkl", "dt_model_Bukadra.pkl", 
                        "dt_model_Burj_Khalifa.pkl", "dt_model_Business_Bay.pkl",
                        "dt_model_Hadaeq_Sheikh_Mohammed_Bin_Rashid.pkl", "dt_model_Jabal_Ali_First.pkl",
                        "dt_model_Madinat_Al_Mataar.pkl", "dt_model_Madinat_Dubai_Almelaheyah.pkl",
                        "dt_model_Marsa_Dubai.pkl", "dt_model_Me'Aisem_First.pkl",
                        "dt_model_Nadd_Hessa.pkl", "dt_model_Wadi_Al_Safa_5.pkl"
                    ]
                    
                    # Extract area names from filenames and load models
                    for model_file in area_files:
                        try:
                            # Extract area name from filename
                            area_name = model_file.replace('dt_model_', '').replace('.pkl', '')
                            area_name = area_name.replace('_', ' ').title()
                            
                            # Load the model
                            if os.path.exists(model_file):
                                with open(model_file, 'rb') as f:
                                    area_models[area_name] = pickle.load(f)
                            else:
                                st.warning(f"⚠️ Model file not found: {model_file}")
                        except Exception as e:
                            st.error(f"❌ Error loading model {model_file}: {str(e)}")
                    
                    # Load OHE transformer
                    if os.path.exists("onehot_encoder.pkl"):
                        with open("onehot_encoder.pkl", "rb") as f:
                            ohe = pickle.load(f)
                    else:
                        st.error("❌ OHE transformer file not found: onehot_encoder.pkl")
                        ohe = None
                        
                    return area_models, ohe
                except Exception as e:
                    st.error(f"Error loading models: {str(e)}")
                    return {}, None
            
            # Load models and preprocessing
            area_models, ohe = load_models_and_preprocessing()
            
            
            # =========================
            # LOAD DATA FOR FORECASTING TAB
            # =========================
            @st.cache_data
            def load_forecasting_data():
                """Load forecasting-specific data"""
                try:
                    # Load test data for forecasting
                    test_samples_forecast = pd.read_csv("test_data_20 areas_1.csv")
                    test_samples_forecast = test_samples_forecast.drop(columns=[col for col in drop_col if col in test_samples_forecast.columns])
                    
                    # Remove unwanted columns
                    columns_to_drop = ['Unnamed: 0', 'instance_date', 'quarter', 'Year']
                    columns_to_drop = [col for col in columns_to_drop if col in test_samples_forecast.columns]
                    X_test_forecast = test_samples_forecast.drop(columns=columns_to_drop + ['meter_sale_price'], errors='ignore')
                    
                    # Load train columns
                    with open("train_columns.pkl", "rb") as f:
                        train_columns = pickle.load(f)
                    
                    # Load and process growth factors from ARIMA forecast
                    growth_df = pd.read_csv('arima_areas_growth_6M.csv')
                    
                    # Convert date strings to proper datetime
                    growth_df['ds'] = pd.to_datetime(growth_df['ds'], errors='coerce')
                    
                    # If conversion failed, try specific formats
                    if growth_df['ds'].isna().any():
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                            growth_df['ds'] = pd.to_datetime(growth_df['ds'], format=fmt, errors='coerce')
                            if not growth_df['ds'].isna().all():
                                break
                    
                    # Define the base prediction quarter (2025 Q2)
                    base_prediction_quarter = pd.Timestamp('2025-06-30')  # 2025 Q2 end
                    
                    # Filter to include 2025 Q3 and beyond (quarters after base prediction)
                    growth_df = growth_df[growth_df['ds'] >= base_prediction_quarter]
                    
                    # Ensure we only have quarterly data (end of quarter)
                    growth_df = growth_df[growth_df['ds'].dt.is_quarter_end]
                    
                    # Limit forecast to end of 2028
                    target_end_date = pd.Timestamp('2026-12-31')
                    growth_df = growth_df[growth_df['ds'] <= target_end_date]
                    
                    # Check if we have the required growth factor columns
                    required_cols = ['growth_factor', 'growth_factor_lower', 'growth_factor_upper']
                    missing_cols = [col for col in required_cols if col not in growth_df.columns]
                    if missing_cols:
                        st.error(f"❌ Missing required columns in ARIMA data: {missing_cols}")
                        return None, None, None, None, None, None, None, None, None, None
                    
                    # Check if we have any future data
                    if len(growth_df) == 0:
                        st.warning("⚠️ No future forecast data found in ARIMA file. Generating default future quarters.")
                        # Create default future quarters starting from 2025 Q3
                        future_dates = pd.date_range(start=pd.Timestamp('2025-09-30'), end=target_end_date, freq='Q')
                        
                        # Create default growth data (no growth)
                        default_growth_data = []
                        for area in growth_df['area_name_en'].unique():
                            for date in future_dates:
                                default_growth_data.append({
                                    'ds': date,
                                    'area_name_en': area,
                                    'growth_factor': 1.0,
                                    'growth_factor_lower': 0.95,
                                    'growth_factor_upper': 1.05
                                })
                        
                        growth_df = pd.DataFrame(default_growth_data)
                    
                    growth_df = growth_df[['ds', 'area_name_en', 'growth_factor', 'growth_factor_lower', 'growth_factor_upper']]
                    
                    # Create pivot tables for all three growth factors
                    growth_pivot = growth_df.pivot(index='area_name_en', columns='ds', values='growth_factor').reset_index()
                    growth_lower_pivot = growth_df.pivot(index='area_name_en', columns='ds', values='growth_factor_lower').reset_index()
                    growth_upper_pivot = growth_df.pivot(index='area_name_en', columns='ds', values='growth_factor_upper').reset_index()
                    
                    # Load and prepare historical quarterly mean prices from training data
                    train_data = pd.read_csv("df_trained_dataset_6000.csv")
                    train_data['instance_date'] = pd.to_datetime(train_data['instance_date'])
                    train_data['year_quarter'] = train_data['instance_date'].dt.year.astype(str) + '-Q' + train_data['instance_date'].dt.quarter.astype(str)
                    
                    # Calculate mean prices per area per quarter
                    historical_mean = train_data.groupby(['area_name_en', 'year_quarter'])['meter_sale_price'].mean().reset_index()
                    historical_pivot = historical_mean.pivot(index='area_name_en', columns='year_quarter', values='meter_sale_price').reset_index()
                    
                    # Overall historical trends
                    overall_historical_mean = train_data.groupby(['year_quarter'])['meter_sale_price'].mean().reset_index()
                    overall_historical_pivot = overall_historical_mean.set_index('year_quarter')['meter_sale_price'].to_dict()
                    
                    # Get recent quarters
                    recent_quarters = sorted(historical_mean['year_quarter'].unique())
                    historical_pivot_recent = historical_pivot[['area_name_en'] + recent_quarters]
                    
                    return test_samples_forecast, X_test_forecast, train_columns, growth_pivot, growth_lower_pivot, growth_upper_pivot, historical_pivot_recent, recent_quarters, overall_historical_pivot, train_data
                except Exception as e:
                    st.error(f"Error loading forecasting data: {str(e)}")
                    return None, None, None, None, None, None, None, None, None, None
            
            # Load data
            with st.spinner("Loading forecasting data..."):
                test_samples_forecast, X_test_forecast_raw, train_columns, growth_pivot, growth_lower_pivot, growth_upper_pivot, historical_pivot, historical_quarters, overall_historical_pivot, train_data = load_forecasting_data()
            
            if test_samples_forecast is None:
                st.error("❌ Failed to load forecasting data")
                st.stop()
            
            # =========================
            # Prepare test data
            # =========================
            try:
                area_names_forecast = X_test_forecast_raw['area_name_en']
                X_test_forecast_no_area = X_test_forecast_raw.drop(columns=['area_name_en'], errors='ignore')
                
                cat_cols = X_test_forecast_no_area.select_dtypes(include='object').columns.tolist()
                if cat_cols:
                    X_cat_test = ohe.transform(X_test_forecast_no_area[cat_cols])
                    X_cat_test = pd.DataFrame(X_cat_test, columns=ohe.get_feature_names_out(cat_cols), index=X_test_forecast_no_area.index)
                    X_test_forecast = X_test_forecast_no_area.drop(columns=cat_cols)
                    X_test_forecast = pd.concat([X_test_forecast, X_cat_test], axis=1)
                else:
                    X_test_forecast = X_test_forecast_no_area.copy()
                
                for col in train_columns:
                    if col not in X_test_forecast.columns:
                        X_test_forecast[col] = 0
                
                X_test_forecast = X_test_forecast[train_columns]
                X_test_forecast = X_test_forecast.select_dtypes(include=[np.number])
            except Exception as e:
                st.error(f"❌ Error preparing forecasting data: {str(e)}")
                st.stop()
            
            # =========================
            # Forecasting controls
            # =========================
            st.sidebar.title("🔧 Forecast Controls")
            
            # Check if area_models is loaded
            if not area_models:
                st.sidebar.error("❌ No area models loaded. Please check your model files.")
                available_areas = []
            else:
                available_areas = list(area_models.keys())
            
            # Single area selection instead of multiselect
            selected_area = st.sidebar.selectbox(
                "Select Area for Forecasting",
                options=available_areas,
                index=0 if available_areas else None,
                key="forecast_area_select"
            )
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("📊 Display Options")
            show_historical = st.sidebar.checkbox("Show Historical Quarterly Trends", value=True)
            show_actual_vs_predicted = st.sidebar.checkbox("Show Actual vs Predicted", value=True)
            show_growth_scenarios = st.sidebar.checkbox("Show Growth Scenarios", value=True)
            num_historical_quarters = st.sidebar.slider("Number of Historical Quarters to Show", min_value=1, max_value=12, value=4)
            
            # =========================
            # Generate forecast
            # =========================
            if st.button("🚀 Generate Forecast", type="primary"):
                if not selected_area:
                    st.warning("Please select an area for forecasting")
                    st.stop()
                
                with st.spinner("Generating forecast..."):
                    if selected_area not in area_models:
                        st.error(f"Model not found for area: {selected_area}")
                        st.stop()
                        
                    model = area_models[selected_area]
                    mask = test_samples_forecast['area_name_en'] == selected_area
                    X_area_test = X_test_forecast.loc[mask]
                    
                    if len(X_area_test) == 0:
                        st.error(f"No test data found for area: {selected_area}")
                        st.stop()
                    
                    # Generate predictions
                    y_pred = model.predict(X_area_test)
                    
                    # Get actual values from test data
                    actual_values = test_samples_forecast.loc[mask, 'meter_sale_price'].values
                    
                    # Create predictions dataframe with individual predictions
                    pred_df = pd.DataFrame({
                        'area_name_en': [selected_area] * len(y_pred), 
                        'prediction': y_pred,
                        'actual': actual_values
                    })
                    
                    # Use the mean prediction for consistent forecasting
                    mean_prediction = pred_df['prediction'].mean()
                    mean_actual = pred_df['actual'].mean()
                    
                    # Check if selected area exists in growth factors
                    if selected_area not in growth_pivot['area_name_en'].values:
                        st.warning(f"⚠️ No growth factors found for area: {selected_area}. Using default growth factor of 1.0")
                        
                        # Create default growth factors for future quarters only (starting from 2025 Q3)
                        future_quarters = [col for col in growth_pivot.columns if col != 'area_name_en']
                        default_growth_data = {'area_name_en': [selected_area]}
                        for q in future_quarters:
                            default_growth_data[q] = [1.0]  # No growth
                        
                        forecast_df = pd.DataFrame(default_growth_data)
                        forecast_df['prediction'] = [mean_prediction]
                        forecast_df['actual'] = [mean_actual]
                        
                        forecast_lower_df = pd.DataFrame(default_growth_data)
                        forecast_lower_df['prediction'] = [mean_prediction]
                        forecast_lower_df['actual'] = [mean_actual]
                        
                        forecast_upper_df = pd.DataFrame(default_growth_data)
                        forecast_upper_df['prediction'] = [mean_prediction]
                        forecast_upper_df['actual'] = [mean_actual]
                        
                    else:
                        # Merge with growth factors - normal case
                        forecast_df = pd.DataFrame({
                            'area_name_en': [selected_area],
                            'prediction': [mean_prediction],
                            'actual': [mean_actual]
                        }).merge(growth_pivot, on='area_name_en', how='left')
                        
                        forecast_lower_df = pd.DataFrame({
                            'area_name_en': [selected_area],
                            'prediction': [mean_prediction],
                            'actual': [mean_actual]
                        }).merge(growth_lower_pivot, on='area_name_en', how='left')
                        
                        forecast_upper_df = pd.DataFrame({
                            'area_name_en': [selected_area],
                            'prediction': [mean_prediction],
                            'actual': [mean_actual]
                        }).merge(growth_upper_pivot, on='area_name_en', how='left')
                    
                    # Merge with historical data
                    if historical_pivot is not None and selected_area in historical_pivot['area_name_en'].values:
                        forecast_df = forecast_df.merge(historical_pivot, on='area_name_en', how='left')
                        forecast_lower_df = forecast_lower_df.merge(historical_pivot, on='area_name_en', how='left')
                        forecast_upper_df = forecast_upper_df.merge(historical_pivot, on='area_name_en', how='left')
                    
                    # Get future quarter columns from growth factors
                    future_quarter_cols = [col for col in growth_pivot.columns if col != 'area_name_en']
                    
                    # Sort the future quarters chronologically
                    future_quarter_cols_sorted = sorted(future_quarter_cols)
                    
                    # Display forecast period information
                    if future_quarter_cols_sorted:
                        start_quarter = future_quarter_cols_sorted[0]
                        end_quarter = future_quarter_cols_sorted[-1]
                        
                        # Format quarter labels for display
                        def format_quarter_display(quarter_str):
                            if isinstance(quarter_str, pd.Timestamp):
                                quarter_num = (quarter_str.month - 1) // 3 + 1
                                return f"Q{quarter_num} {quarter_str.year}"
                            return str(quarter_str)
                        
                        st.info(f"**Forecast Period:** {format_quarter_display(start_quarter)} to {format_quarter_display(end_quarter)} ({len(future_quarter_cols_sorted)} quarters)")
                        st.info(f"**Base Prediction:** Current model prediction represents 2025 Q2")
                    else:
                        st.warning("⚠️ No future quarters found for forecasting")
                        future_quarter_cols_sorted = []
                    
                    # Apply growth factors to future quarters based on actual prediction
                    for q in future_quarter_cols_sorted:
                        if q in forecast_df.columns:
                            # Apply growth factor to predicted price
                            forecast_df[q] = forecast_df['prediction'] * forecast_df[q]
                            forecast_lower_df[q] = forecast_lower_df['prediction'] * forecast_lower_df[q]
                            forecast_upper_df[q] = forecast_upper_df['prediction'] * forecast_upper_df[q]
                    
                    # Prepare final forecast data
                    all_quarter_cols = []
                    if show_historical and historical_pivot is not None and selected_area in historical_pivot['area_name_en'].values:
                        available_historical = [col for col in historical_pivot.columns if col != 'area_name_en']
                        selected_historical = available_historical[-num_historical_quarters:]
                        all_quarter_cols = selected_historical + ['prediction', 'actual'] + future_quarter_cols_sorted
                    else:
                        all_quarter_cols = ['prediction', 'actual'] + future_quarter_cols_sorted
                    
                    # Create final dataframes
                    final_forecast = forecast_df[['area_name_en'] + all_quarter_cols]
                    final_forecast_lower = forecast_lower_df[['area_name_en'] + all_quarter_cols]
                    final_forecast_upper = forecast_upper_df[['area_name_en'] + all_quarter_cols]
            
                # =========================
                # VISUALIZATIONS
                # =========================
                st.success(f"✅ Forecast generated for {selected_area}")
                
                # Helper function for formatting quarters
                def format_quarter_label(quarter_str):
                    if isinstance(quarter_str, pd.Timestamp):
                        quarter_num = (quarter_str.month - 1) // 3 + 1
                        return f"Q{quarter_num} {quarter_str.year}"
                    elif isinstance(quarter_str, str) and '-' in quarter_str:
                        try:
                            date_obj = pd.to_datetime(quarter_str)
                            quarter_num = (date_obj.month - 1) // 3 + 1
                            return f"Q{quarter_num} {date_obj.year}"
                        except:
                            return quarter_str
                    return str(quarter_str).replace('_', ' ').title()
                
                # Helper function to prepare forecast data for plotting
                def prepare_forecast_data(forecast_row, selected_historical, future_quarter_cols, show_historical, include_actual=True):
                    time_periods = []
                    predicted_prices = []
                    actual_prices = []
                    
                    # Add historical quarters
                    if show_historical:
                        historical_cols = [col for col in selected_historical if col in forecast_row.index and pd.notna(forecast_row[col])]
                        for hq in historical_cols:
                            time_periods.append(format_quarter_label(hq))
                            actual_prices.append(forecast_row[hq])
                            predicted_prices.append(np.nan)
                    
                    # Add current prediction and actual (2025 Q2)
                    time_periods.append('2025 Q2 (Current)')
                    predicted_prices.append(forecast_row['prediction'])
                    if include_actual and 'actual' in forecast_row and pd.notna(forecast_row['actual']):
                        actual_prices.append(forecast_row['actual'])
                    else:
                        actual_prices.append(np.nan)
                    
                    # Add future quarters in chronological order (starting from 2025 Q3)
                    sorted_future_cols = sorted(future_quarter_cols)
                    for fq in sorted_future_cols:
                        if fq in forecast_row.index and pd.notna(forecast_row[fq]):
                            time_periods.append(format_quarter_label(fq))
                            predicted_prices.append(forecast_row[fq])
                            actual_prices.append(np.nan)
                    
                    return time_periods, predicted_prices, actual_prices
                
                # 1️⃣ Main Forecast Visualization
                st.subheader(f"📈 Quarterly Price Forecast for {selected_area}")
                
                if not final_forecast.empty:
                    row = final_forecast.iloc[0]
                    available_historical = [col for col in historical_pivot.columns if col != 'area_name_en'] if historical_pivot is not None and selected_area in historical_pivot['area_name_en'].values else []
                    selected_historical = available_historical[-num_historical_quarters:] if show_historical and available_historical else []
                    
                    time_periods, predicted_prices, actual_prices = prepare_forecast_data(
                        row, selected_historical, future_quarter_cols_sorted, show_historical, include_actual=True
                    )
                    
                    fig_main = go.Figure()
                    
                    # Add historical actual data
                    if show_historical and selected_historical:
                        historical_points = len([hq for hq in selected_historical if hq in row and pd.notna(row[hq])])
                        if historical_points > 0:
                            fig_main.add_trace(go.Scatter(
                                x=time_periods[:historical_points],
                                y=actual_prices[:historical_points],
                                mode='lines+markers',
                                name='Historical Actual',
                                line=dict(color='blue', width=3),
                                marker=dict(size=8, color='blue')
                            ))
                    
                    # Add current actual vs predicted (2025 Q2)
                    current_idx = len([hq for hq in selected_historical if hq in row and pd.notna(row[hq])]) if show_historical and selected_historical else 0
                    
                    # Current actual value
                    if pd.notna(actual_prices[current_idx]):
                        fig_main.add_trace(go.Scatter(
                            x=[time_periods[current_idx]],
                            y=[actual_prices[current_idx]],
                            mode='markers',
                            name='2025 Q2 Actual',
                            marker=dict(size=12, color='green', symbol='diamond')
                        ))
                    
                    # Current predicted value
                    fig_main.add_trace(go.Scatter(
                        x=[time_periods[current_idx]],
                        y=[predicted_prices[current_idx]],
                        mode='markers',
                        name='2025 Q2 Predicted',
                        marker=dict(size=12, color='red', symbol='star')
                    ))
                    
                    # Add future forecast with growth factors applied (starting from 2025 Q3)
                    future_start_idx = current_idx + 1
                    if future_start_idx < len(time_periods) and len(future_quarter_cols_sorted) > 0:
                        fig_main.add_trace(go.Scatter(
                            x=time_periods[future_start_idx:],
                            y=predicted_prices[future_start_idx:],
                            mode='lines+markers',
                            name='Future Forecast',
                            line=dict(color='orange', width=3, dash='solid'),
                            marker=dict(size=8, color='orange')
                        ))
                    
                    # Add confidence intervals if showing scenarios
                    if show_growth_scenarios and not final_forecast_lower.empty and not final_forecast_upper.empty and len(future_quarter_cols_sorted) > 0:
                        row_lower = final_forecast_lower.iloc[0]
                        row_upper = final_forecast_upper.iloc[0]
                        
                        _, lower_prices, _ = prepare_forecast_data(row_lower, selected_historical, future_quarter_cols_sorted, show_historical, include_actual=False)
                        _, upper_prices, _ = prepare_forecast_data(row_upper, selected_historical, future_quarter_cols_sorted, show_historical, include_actual=False)
                        
                        # Add confidence area for future periods
                        future_time_periods = time_periods[future_start_idx:]
                        future_lower = lower_prices[future_start_idx:]
                        future_upper = upper_prices[future_start_idx:]
                        
                        if future_lower and future_upper:
                            fig_main.add_trace(go.Scatter(
                                x=future_time_periods + future_time_periods[::-1],
                                y=future_upper + future_lower[::-1],
                                fill='toself',
                                fillcolor='rgba(255,165,0,0.2)',
                                line=dict(color='rgba(255,255,255,0)'),
                                name='Confidence Interval',
                                showlegend=True
                            ))
                    
                    fig_main.update_layout(
                        title=f"Quarterly Price Forecast - {selected_area}",
                        xaxis_title="Time Period",
                        yaxis_title="Price per Square Meter (AED)",
                        height=500,
                        template="plotly_white",
                        showlegend=True,
                        xaxis=dict(tickangle=45)
                    )
                    
                    st.plotly_chart(fig_main, use_container_width=True)
                    
                    # Display forecast summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("2025 Q2 Prediction", f"AED {mean_prediction:,.0f}")
                    with col2:
                        if pd.notna(mean_actual):
                            st.metric("2025 Q2 Actual", f"AED {mean_actual:,.0f}")
                    with col3:
                        future_quarters_count = len(future_quarter_cols_sorted)
                        st.metric("Future Quarters", f"{future_quarters_count}")
                
                # 2️⃣ Growth Factors Display
                if future_quarter_cols_sorted:
                    st.subheader("📊 Applied Growth Factors")
                    
                    if not forecast_df.empty:
                        growth_data = []
                        row = forecast_df.iloc[0]
                        
                        for q in future_quarter_cols_sorted:
                            if q in row and pd.notna(row[q]):
                                original_pred = row['prediction']
                                forecasted_price = row[q]
                                growth_factor = forecasted_price / original_pred if original_pred != 0 else 1
                                growth_percentage = (growth_factor - 1) * 100
                                
                                growth_data.append({
                                    'Quarter': format_quarter_label(q),
                                    'Growth Factor': f"{growth_factor:.4f}",
                                    'Growth %': f"{growth_percentage:+.2f}%",
                                    'Forecasted Price (AED)': f"{forecasted_price:,.0f}"
                                })
                        
                        if growth_data:
                            growth_df_display = pd.DataFrame(growth_data)
                            st.dataframe(growth_df_display, use_container_width=True, hide_index=True)
                
                # 3️⃣ Detailed Forecast Data
                st.subheader("📈 Detailed Forecast Data")
                
                display_data = []
                if not final_forecast.empty:
                    row = final_forecast.iloc[0]
                    
                    # Historical data
                    if show_historical:
                        for hq in selected_historical:
                            if hq in row and pd.notna(row[hq]):
                                display_data.append({
                                    'Period': format_quarter_label(hq),
                                    'Type': 'Historical',
                                    'Price (AED)': f"{row[hq]:,.0f}",
                                    'Growth Factor': '-'
                                })
                    
                    # Current prediction and actual (2025 Q2)
                    display_data.append({
                        'Period': '2025 Q2',
                        'Type': 'Prediction',
                        'Price (AED)': f"{row['prediction']:,.0f}",
                        'Growth Factor': '1.0000 (Base)'
                    })
                    
                    if pd.notna(row['actual']):
                        display_data.append({
                            'Period': '2025 Q2',
                            'Type': 'Actual',
                            'Price (AED)': f"{row['actual']:,.0f}",
                            'Growth Factor': '-'
                        })
                    
                    # Future forecasts with growth factors (starting from 2025 Q3)
                    for fq in future_quarter_cols_sorted:
                        if fq in row and pd.notna(row[fq]):
                            growth_factor = row[fq] / row['prediction'] if row['prediction'] != 0 else 1
                            display_data.append({
                                'Period': format_quarter_label(fq),
                                'Type': 'Forecast',
                                'Price (AED)': f"{row[fq]:,.0f}",
                                'Growth Factor': f"{growth_factor:.4f}"
                            })
                
                if display_data:
                    display_df = pd.DataFrame(display_data)
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("No forecast data available to display")
            
            else:
                st.info("👆 Select an area and click 'Generate Forecast' to see predictions")
                    #####################################################################################################################_____________________________________+++++++++++++++++++++++++++++++++++++++++++++++++
        with tab2:
            import streamlit as st
            import plotly.graph_objects as go
            import plotly.express as px
            import pandas as pd
            
            # Set page configuration
            #st.set_page_config(page_title="ARIMA Forecast", layout="wide")
            arima_forecast_df_quarterly = pd.read_csv("arima_forecast_quarterly_all_areas.csv")
            arima_forecast_df_quarterly = arima_forecast_df_quarterly.drop(columns=[col for col in drop_col if col in arima_forecast_df_quarterly.columns])
            # Title
            st.title("ARIMA Forecast - Quarterly Data")
            
            # Your metrics data (replace this with your actual metrics DataFrame)
            metrics_data = {
                'area_name_en': [
                    'Al Barsha South Fifth', 'Al Barsha South Fourth', 'Al Barshaa South Third',
                    'Al Hebiah Fourth', 'Al Khairan First', 'Al Merkadh', 'Al Thanyah Fifth',
                    'Al Yelayiss 2', 'Burj Khalifa', 'Business Bay', 
                    'Hadaeq Sheikh Mohammed Bin Rashid', 'Jabal Ali First', 'Madinat Al Mataar',
                    'Madinat Dubai Almelaheyah', 'Marsa Dubai', 'Me\'Aisem First', 'Nadd Hessa',
                    'Wadi Al Safa 5'
                ],
                'MAE': [
                    1080.890459, 721.225994, 1118.409692, 579.593767, 1337.522897, 1096.323912,
                    523.932791, 666.745732, 1589.888349, 1357.038565, 1076.517280, 858.558121,
                    768.352293, 1152.594843, 1289.914164, 498.010100, 404.747743, 631.813785
                ],
                'RMSE': [
                    1512.120078, 1622.076318, 1949.541688, 750.356845, 2793.295634, 2892.483144,
                    749.020401, 888.454287, 3318.609051, 3090.978111, 2431.840921, 1096.402134,
                    1082.907618, 1685.947827, 2683.503879, 655.352504, 575.951861, 838.465041
                ],
                'MAPE': [
                    10.080573, 7.733304, 10.709510, 6.610677, 7.758506, 6.363154, 4.782912,
                    6.877848, 8.668525, 7.722372, 7.249083, 9.661324, 9.512773, 6.104294,
                    8.397232, 5.758879, 5.387785, 9.256670
                ]
            }
            
            metrics_df = pd.read_csv('arima_fitted_metrics_all_areas.csv')
            metrics_df = metrics_df.drop(columns=[col for col in drop_col if col in metrics_df.columns])
            
            # Create tabs
            tab1, tab2 = st.tabs(["Forecast", "Metrics"])
            
            with tab1:
                # Forecast Tab
                st.header("ARIMA Forecast by Area")
                
                # Area selection
                areas = arima_forecast_df_quarterly['area_name_en'].unique()
                selected_area = st.selectbox("Select Area:", areas, key="forecast_select")
                
                # Get metrics for selected area
                area_metrics = metrics_df[metrics_df['area_name_en'] == selected_area]
                
                # Display metrics for selected area
                if not area_metrics.empty:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("MAE", f"{area_metrics['MAE'].iloc[0]:.2f}")
                    with col2:
                        st.metric("RMSE", f"{area_metrics['RMSE'].iloc[0]:.2f}")
                    with col3:
                        st.metric("MAPE", f"{area_metrics['MAPE'].iloc[0]:.2f}%")
                
                # Filter data for selected area
                df_area = arima_forecast_df_quarterly[arima_forecast_df_quarterly['area_name_en'] == selected_area]
                
                # Separate actual and forecast data
                actual_df = df_area[df_area['type'] == 'fitted']
                forecast_df = df_area[df_area['type'] == 'forecast']
                
                # Create plot
                fig = go.Figure()
                
                # Actual (fitted)
                if not actual_df.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=actual_df['ds'],
                            y=actual_df['actual'],
                            mode='lines+markers',
                            name='Actual',
                            line=dict(color='blue', width=3),
                            marker=dict(size=8)
                        )
                    )
                
                # Forecast
                if not forecast_df.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=forecast_df['ds'],
                            y=forecast_df['yhat'],
                            mode='lines+markers',
                            name='Forecast',
                            line=dict(color='orange', width=3),
                            marker=dict(size=8)
                        )
                    )
                
                    # Confidence interval
                    fig.add_trace(
                        go.Scatter(
                            x=forecast_df['ds'].tolist() + forecast_df['ds'].tolist()[::-1],
                            y=forecast_df['yhat_upper'].tolist() + forecast_df['yhat_lower'].tolist()[::-1],
                            fill='toself',
                            fillcolor='rgba(255,165,0,0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            hoverinfo="skip",
                            showlegend=False,
                            name='Confidence Interval'
                        )
                    )
                
                    # Connect last actual to first forecast
                    if not actual_df.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=[actual_df['ds'].iloc[-1], forecast_df['ds'].iloc[0]],
                                y=[actual_df['actual'].iloc[-1], forecast_df['yhat'].iloc[0]],
                                mode='lines',
                                line=dict(color='green', dash='dash', width=2),
                                name='Connection'
                            )
                        )
                
                # X-axis labels
                tickvals = df_area['ds'].tolist()
                ticktext = df_area['quarter_label'].tolist()
                
                fig.update_layout(
                    title=f"{selected_area} - Actual vs Forecast (Quarterly)",
                    xaxis_title="Quarter",
                    yaxis_title="Meter Sale Price",
                    xaxis=dict(tickmode='array', tickvals=tickvals, ticktext=ticktext),
                    template='plotly_white',
                    hovermode="x unified",
                    height=600,
                    showlegend=True
                )
                
                # Display the plot
                st.plotly_chart(fig, use_container_width=True)
                
                # Optional: Show data table
                if st.checkbox("Show Forecast Data Table", key="forecast_table"):
                    st.subheader("Forecast Data")
                    
                    # Create a display dataframe with relevant columns
                    display_columns = ['ds', 'quarter_label', 'type', 'actual', 'yhat', 'yhat_lower', 'yhat_upper']
                    available_columns = [col for col in display_columns if col in df_area.columns]
                    
                    display_df = df_area[available_columns].copy()
                    
                    # Format the display
                    if 'actual' in display_df.columns:
                        display_df['actual'] = display_df['actual'].round(2)
                    if 'yhat' in display_df.columns:
                        display_df['yhat'] = display_df['yhat'].round(2)
                    if 'yhat_lower' in display_df.columns:
                        display_df['yhat_lower'] = display_df['yhat_lower'].round(2)
                    if 'yhat_upper' in display_df.columns:
                        display_df['yhat_upper'] = display_df['yhat_upper'].round(2)
                    
                    st.dataframe(display_df.sort_values('ds'))
            
            with tab2:
                # Metrics Tab
                st.header("Model Performance Metrics")
                
                # Display metrics table
                st.subheader("All Areas Metrics")
                
                # Format the metrics for display
                display_metrics = metrics_df.copy()
                display_metrics['MAE'] = display_metrics['MAE'].round(2)
                display_metrics['RMSE'] = display_metrics['RMSE'].round(2)
                display_metrics['MAPE'] = display_metrics['MAPE'].round(2)
                
                st.dataframe(display_metrics, use_container_width=True)
                
                # Create bar charts for each metric
                st.subheader("Metrics Visualization")
                
                # Sort metrics by area name for better visualization
                sorted_metrics = metrics_df.sort_values('area_name_en')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # MAE Bar Chart
                    fig_mae = px.bar(
                        sorted_metrics,
                        x='area_name_en',
                        y='MAE',
                        title='MAE by Area',
                        color='MAE',
                        color_continuous_scale='blues'
                    )
                    fig_mae.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig_mae, use_container_width=True)
                    
                    # RMSE Bar Chart
                    fig_rmse = px.bar(
                        sorted_metrics,
                        x='area_name_en',
                        y='RMSE',
                        title='RMSE by Area',
                        color='RMSE',
                        color_continuous_scale='reds'
                    )
                    fig_rmse.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig_rmse, use_container_width=True)
                
                with col2:
                    # MAPE Bar Chart
                    fig_mape = px.bar(
                        sorted_metrics,
                        x='area_name_en',
                        y='MAPE',
                        title='MAPE by Area (%)',
                        color='MAPE',
                        color_continuous_scale='greens'
                    )
                    fig_mape.update_layout(xaxis_tickangle=-45, height=400)
                    st.plotly_chart(fig_mape, use_container_width=True)
                    
                    # Summary statistics
                    st.subheader("Metrics Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Average MAE", f"{metrics_df['MAE'].mean():.2f}")
                    with col2:
                        st.metric("Average RMSE", f"{metrics_df['RMSE'].mean():.2f}")
                    with col3:
                        st.metric("Average MAPE", f"{metrics_df['MAPE'].mean():.2f}%")


    ###############################################################################################################################################################################################################################

    import pandas as pd
    import streamlit as st
    import pickle
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    from datetime import datetime, timedelta
    import warnings
    warnings.filterwarnings('ignore')
    # =====================
    # TAB 3: Area-wise Prediction & Forecast
    # =====================
    if sidebar_option == "validation":
        import streamlit as st
        import plotly.graph_objects as go
        import pandas as pd
    
        df_test_forcast = pd.read_csv('df_test_forcast.csv')
        df_test_forcast['diff_%'] = (df_test_forcast['median_growth'] - df_test_forcast['actual_median']) / df_test_forcast['median_growth'] * 100
        
        #st.title("📊 Predicted vs Actual Median Prices with Difference %")
        
        fig = go.Figure()
        
        # --- Bars (side by side) ---
        fig.add_trace(go.Bar(
            x=df_test_forcast["area_name_en"],
            y=df_test_forcast["median_growth"],
            name="Predicted Median Price"
        ))
        
        fig.add_trace(go.Bar(
            x=df_test_forcast["area_name_en"],
            y=df_test_forcast["actual_median"],
            name="Actual Median Price"
        ))
        
        # --- Line on secondary y-axis ---
        fig.add_trace(go.Scatter(
            x=df_test_forcast["area_name_en"],
            y=df_test_forcast["diff_%"],
            name="Difference %",
            mode="lines+markers",
            yaxis="y2"
        ))
        
        # --- Layout ---
        fig.update_layout(
            title="Predicted vs Actual Median Prices with Diff %",
            xaxis=dict(title="area_name_en"),
            yaxis=dict(title="Meter sale price"),
            yaxis2=dict(
                title="Difference %",
                overlaying="y",
                side="right",
                zeroline=True,      # show zero line
                zerolinecolor="red",
                zerolinewidth=2
            ),
            barmode="group",
            xaxis_tickangle=-45,
            bargap=0.2,
        )
        
        # --- Show in Streamlit ---
        
        st.plotly_chart(fig, use_container_width=True)


    
    if sidebar_option == "🤖 Model Input / Prediction":
    
    
        st.title("V_2.1: prediction dashboard")
        
        # This will display the external app in a box on your dashboard
        st.link_button("Go to Price Predictor", "https://flipose-re-price-prediction.streamlit.app/")


###########################################################################################################################################################################################################################
###########################################################################################################################################################################################################################

# =========================
# 🤖 MODEL INPUT / PREDICTION SECTION
# =========================
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pickle
import os
from statsmodels.nonparametric.smoothers_lowess import lowess
from datetime import datetime, timedelta

# =========================
# INITIALIZATION & MODEL LOADING
# =========================
@st.cache_resource
def load_area_models():
    """Load all area-specific models"""
    area_models = {}
    area_files = [
        "dt_model_Al_Barsha_South_Fifth.pkl", "dt_model_Al_Barsha_South_Fourth.pkl", 
        "dt_model_Al_Barshaa_South_Third.pkl", "dt_model_Al_Hebiah_Fourth.pkl",
        "dt_model_Al_Khairan_First.pkl", "dt_model_Al_Merkadh.pkl", 
        "dt_model_Al_Thanyah_Fifth.pkl", "dt_model_Al_Warsan_First.pkl",
        "dt_model_Al_Yelayiss_2.pkl", "dt_model_Bukadra.pkl", 
        "dt_model_Burj_Khalifa.pkl", "dt_model_Business_Bay.pkl",
        "dt_model_Hadaeq_Sheikh_Mohammed_Bin_Rashid.pkl", "dt_model_Jabal_Ali_First.pkl",
        "dt_model_Madinat_Al_Mataar.pkl", "dt_model_Madinat_Dubai_Almelaheyah.pkl",
        "dt_model_Marsa_Dubai.pkl", "dt_model_Me'Aisem_First.pkl",
        "dt_model_Nadd_Hessa.pkl", "dt_model_Wadi_Al_Safa_5.pkl"
    ]
    
    loaded_models = {}
    missing_models = []
    
    for model_file in area_files:
        try:
            # Extract area name from filename
            area_name = model_file.replace('dt_model_', '').replace('.pkl', '').replace('_', ' ')
            
            # Load the model
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
            
            loaded_models[area_name] = model
            
        except FileNotFoundError:
            missing_models.append(model_file)
        except Exception as e:
            st.sidebar.error(f"❌ Error loading {model_file}: {str(e)}")
    
    if missing_models:
        st.sidebar.warning(f"Missing models: {len(missing_models)} files")
    
    return loaded_models

# =========================
# LOAD ENCODER AND TRAIN COLUMNS
# =========================
@st.cache_resource
def load_encoder_and_columns():
    """Load the encoder and training columns"""
    try:
        with open('onehot_encoder.pkl', 'rb') as f:
            ohe = pickle.load(f)
        with open('train_columns.pkl', 'rb') as f:
            train_columns = pickle.load(f)
        return ohe, train_columns
    except Exception as e:
        st.error(f"Error loading encoder/columns: {str(e)}")
        return None, None

# =========================
# LOAD TRAINING DATA WITH SELECTED FEATURES
# =========================
@st.cache_data
def load_training_data():
    """Load training data with selected features for LOESS trend analysis"""
    try:
        # Load your training data
        train_data = pd.read_csv('df_trained_dataset_6000.csv')
        
        # Ensure we have the necessary columns for trend analysis
        required_cols = ['area_name_en', 'instance_date', 'meter_sale_price', 
                        'rooms_en', 'floor_bin', 'swimming_pool', 'balcony', 
                        'elevator', 'metro', 'has_parking', 'procedure_area']
        
        if all(col in train_data.columns for col in required_cols):
            # Convert date column to datetime and extract year
            train_data['instance_date'] = pd.to_datetime(train_data['instance_date'])
            train_data['year'] = train_data['instance_date'].dt.year
            return train_data
        else:
            missing_cols = [col for col in required_cols if col not in train_data.columns]
            st.warning(f"Training data missing columns: {missing_cols}")
            return None
    except Exception as e:
        st.warning(f"Could not load training data for trend analysis: {str(e)}")
        return None

# =========================
# LOAD FORECASTING DATA
# =========================
@st.cache_data
def load_forecasting_data():
    """Load forecasting-specific data with all growth factors"""
    try:
        # Load growth factors with all three columns
        growth_df = pd.read_csv('arima_areas_growth_6M.csv')
        
        # Check if all required columns exist
        required_growth_cols = ['ds', 'area_name_en', 'growth_factor', 'growth_factor_upper', 'growth_factor_lower']
        
        if all(col in growth_df.columns for col in required_growth_cols):
            return growth_df
        else:
            st.warning("Forecasting data missing some growth factor columns")
            return None
    except Exception as e:
        st.error(f"Error loading forecasting data: {str(e)}")
        return None

# =========================
# FILTER TRAINING DATA BY EXACT SELECTED FEATURES
# =========================
def filter_training_data_by_exact_features(train_data, selected_features, area_name):
    """Filter training data to show only properties with EXACT same features in the same area"""
    try:
        filtered_data = train_data.copy()
        
        # First filter by area
        filtered_data = filtered_data[filtered_data['area_name_en'] == area_name]
        
        # Apply filters based on EXACT selected features
        if 'rooms_en' in selected_features and selected_features['rooms_en']:
            filtered_data = filtered_data[filtered_data['rooms_en'] == selected_features['rooms_en']]
        
        if 'floor_bin' in selected_features and selected_features['floor_bin']:
            filtered_data = filtered_data[filtered_data['floor_bin'] == selected_features['floor_bin']]
        
        # Filter binary features EXACTLY
        binary_features = ['swimming_pool', 'balcony', 'elevator', 'metro', 'has_parking']
        for feature in binary_features:
            if feature in selected_features and selected_features[feature] is not None:
                filtered_data = filtered_data[filtered_data[feature] == selected_features[feature]]
        
        # Filter area within a reasonable range (±10% for exact matching)
        if 'procedure_area' in selected_features and selected_features['procedure_area']:
            area_value = selected_features['procedure_area']
            lower_bound = area_value * 0.9
            upper_bound = area_value * 1.1
            filtered_data = filtered_data[
                (filtered_data['procedure_area'] >= lower_bound) & 
                (filtered_data['procedure_area'] <= upper_bound)
            ]
        
        return filtered_data
        
    except Exception as e:
        st.warning(f"Error filtering training data: {str(e)}")
        return train_data[train_data['area_name_en'] == area_name]  # Return area data if filtering fails

# =========================
# CALCULATE TREND FOR EXACT SAME FEATURES
# =========================
def calculate_trend_for_exact_features(filtered_data, current_year):
    """Calculate trend for properties with exact same features"""
    try:
        if len(filtered_data) < 2:  # Need at least 2 data points for trend
            return None, None, None
        
        # Group by year and calculate median price
        yearly_data = filtered_data.groupby('year')['meter_sale_price'].agg(['median', 'count']).reset_index()
        yearly_data = yearly_data.rename(columns={'median': 'meter_sale_price', 'count': 'data_points'})
        
        if len(yearly_data) < 2:
            return None, None, None
        
        # Apply LOESS smoothing
        y_values = yearly_data['meter_sale_price'].values
        x_values = yearly_data['year'].values
        
        loess_smoothed = lowess(y_values, x_values, frac=0.8, it=3)
        
        # Create trend DataFrame
        trend_df = pd.DataFrame({
            'year': loess_smoothed[:, 0],
            'smoothed_price': loess_smoothed[:, 1]
        })
        
        # Calculate latest trend
        if len(trend_df) >= 2:
            trend_df = trend_df.sort_values('year')
            latest_trend = trend_df.iloc[-1]['smoothed_price']
            return trend_df, latest_trend, yearly_data
        else:
            return trend_df, None, yearly_data
            
    except Exception as e:
        st.warning(f"Could not calculate trend for exact features: {str(e)}")
        return None, None, None

# =========================
# CREATE COMBINED TREND AND FORECAST PLOT WITH ALL GROWTH FACTORS
# =========================
def create_combined_trend_forecast_plot(historical_data, trend_data, current_price, forecast_data, area_name, selected_features):
    """Create a combined plot showing historical trend for exact features and future forecast with confidence intervals"""
    
    fig = go.Figure()
    current_year = datetime.now().year
    
    # Add historical data points (EXACT same features)
    if historical_data is not None and len(historical_data) > 0:
        # Add individual data points
        fig.add_trace(go.Scatter(
            x=historical_data['year'],
            y=historical_data['meter_sale_price'],
            mode='markers',
            name=f'Historical Properties (Exact Features)',
            marker=dict(color='blue', size=8, opacity=0.7),
            hovertemplate='Year: %{x}<br>Price: AED %{y:,.0f}<br>Data Points: %{customdata}<extra></extra>',
            customdata=historical_data['data_points']
        ))
    
    # Add LOESS trend line for exact features
    if trend_data is not None and len(trend_data) > 0:
        fig.add_trace(go.Scatter(
            x=trend_data['year'],
            y=trend_data['smoothed_price'],
            mode='lines',
            name='Historical Trend (Exact Features)',
            line=dict(color='red', width=3),
            hovertemplate='Year: %{x}<br>Trend Price: AED %{y:,.0f}<extra></extra>'
        ))
    
    # Add current prediction point
    fig.add_trace(go.Scatter(
        x=[current_year],
        y=[current_price],
        mode='markers',
        name='Current Prediction',
        marker=dict(color='green', size=15, symbol='star'),
        hovertemplate='Current Prediction<br>Price: AED %{y:,.0f}<extra></extra>'
    ))
    
    # Add forecast data with confidence intervals
    if forecast_data is not None and len(forecast_data) > 0:
        forecast_years = []
        forecast_main = []
        forecast_upper = []
        forecast_lower = []
        
        # Sort forecast data by period to ensure chronological order
        sorted_periods = sorted(forecast_data.keys())
        
        for i, period in enumerate(sorted_periods):
            growth_factors = forecast_data[period]
            forecast_year = current_year + (i + 1) * 0.25  # Quarterly increments
            
            forecast_years.append(forecast_year)
            forecast_main.append(current_price * growth_factors['main'])
            forecast_upper.append(current_price * growth_factors['upper'])
            forecast_lower.append(current_price * growth_factors['lower'])
        
        # Add confidence interval area
        fig.add_trace(go.Scatter(
            x=forecast_years + forecast_years[::-1],
            y=forecast_upper + forecast_lower[::-1],
            fill='toself',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Forecast Confidence Interval',
            showlegend=True,
            hoverinfo='skip'
        ))
        
        # Add main forecast line
        fig.add_trace(go.Scatter(
            x=forecast_years,
            y=forecast_main,
            mode='lines+markers',
            name='Future Forecast (Main)',
            line=dict(color='orange', width=3),
            marker=dict(color='orange', size=8),
            hovertemplate='Year: %{x:.2f}<br>Forecast: AED %{y:,.0f}<extra></extra>'
        ))
        
        # Add upper bound line
        fig.add_trace(go.Scatter(
            x=forecast_years,
            y=forecast_upper,
            mode='lines',
            name='Forecast Upper Bound',
            line=dict(color='orange', width=1, dash='dash'),
            opacity=0.7,
            hovertemplate='Year: %{x:.2f}<br>Upper Bound: AED %{y:,.0f}<extra></extra>'
        ))
        
        # Add lower bound line
        fig.add_trace(go.Scatter(
            x=forecast_years,
            y=forecast_lower,
            mode='lines',
            name='Forecast Lower Bound',
            line=dict(color='orange', width=1, dash='dash'),
            opacity=0.7,
            hovertemplate='Year: %{x:.2f}<br>Lower Bound: AED %{y:,.0f}<extra></extra>'
        ))
    
    # Create feature description for title
    feature_desc = f"{selected_features['rooms_en']}, {selected_features['floor_bin']}, {selected_features['procedure_area']} sqMt"
    
    # Update layout
    fig.update_layout(
        title=f"Price Timeline - {area_name}<br><sub>Features: {feature_desc}</sub>",
        xaxis_title="Year",
        yaxis_title="Price (AED)",
        height=500,
        template="plotly_white",
        hovermode='closest',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# =========================
# PREPARE FORECAST DATA WITH ALL GROWTH FACTORS
# =========================
def prepare_forecast_data(growth_pivot, area_name):
    """Prepare forecast data with all three growth factors"""
    if growth_pivot is None:
        return None
    
    try:
        # Filter growth data for the selected area
        area_growth = growth_pivot[growth_pivot['area_name_en'] == area_name]
        
        if area_growth.empty:
            return None
        
        # Get unique periods (ds values)
        periods = area_growth['ds'].unique()
        
        forecast_data = {}
        
        for period in periods:
            period_data = area_growth[area_growth['ds'] == period].iloc[0]
            
            forecast_data[period] = {
                'main': period_data['growth_factor'],
                'upper': period_data['growth_factor_upper'],
                'lower': period_data['growth_factor_lower']
            }
        
        return forecast_data
        
    except Exception as e:
        st.warning(f"Error preparing forecast data: {str(e)}")
        return None

# =========================
# MAIN APP
# =========================

# Load models and data
with st.spinner("Loading models and data..."):
    area_models = load_area_models()
    ohe, train_columns = load_encoder_and_columns()
    train_data = load_training_data()
    growth_pivot = load_forecasting_data()

# Check if essential components are loaded
if not area_models:
    st.error("❌ No area models were loaded. Please check your model files.")
    st.stop()

if ohe is None or train_columns is None:
    st.error("❌ Encoder or training columns not loaded properly.")
    st.stop()

# =========================
# 🤖 MODEL INPUT / PREDICTION SECTION
# =========================
    if sidebar_option == "🤖 Model Input / Prediction":
        st.header("🤖 Property Price Prediction")
        st.markdown("Predict property prices for specific area and features")
        
        # =========================
        # USER INPUT FORM
        # =========================
        st.sidebar.subheader("🏠 Property Features")
        
        # Get available areas from the loaded models
        available_areas = list(area_models.keys())
        
        # Area selection
        selected_area = st.sidebar.selectbox(
            "Select Area",
            options=available_areas,
            key="selected_area"
        )
        
        # Property features input
        st.sidebar.subheader("Property Features")
        
        rooms_options = ['1 B/R', 'Studio', '2 B/R', '3 B/R', 'PENTHOUSE', 'More than 3B/R']
        floor_bin_options = ['1-10', '11-20', '41-50', '21-30', 'Below 1st floor', '31-40',
                           '51-60', 'Other', '-9-0', '61-70', 'Top floor', '91-100', '81-90',
                           '71-80', 'Duplex']
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            rooms_en = st.selectbox("Number of Rooms", options=rooms_options, index=2)
            floor_bin = st.selectbox("Floor Level", options=floor_bin_options, index=1)
            swimming_pool = st.selectbox("Swimming Pool", options=[0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
            balcony = st.selectbox("Balcony", options=[0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
        
        with col2:
            elevator = st.selectbox("Elevator", options=[0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
            metro = st.selectbox("Near Metro", options=[0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
            has_parking = st.selectbox("Parking", options=[0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
            procedure_area = st.number_input("Area (sqMt)", min_value=2, max_value=350, value=120, step=1)
        
        # =========================
        # PREPARE INPUT DATA FUNCTION
        # =========================
        def prepare_input_data(area, rooms, floor, pool, balcony_val, elevator_val, metro_val, parking, area_size):
            """Prepare user input for prediction"""
            
            input_data = pd.DataFrame({
                'rooms_en': [rooms],
                'floor_bin': [floor],
                'swimming_pool': [pool],
                'balcony': [balcony_val],
                'elevator': [elevator_val],
                'metro': [metro_val],
                'has_parking': [parking],
                'area_name_en': [area],
                'procedure_area': [area_size]
            })
            
            # Separate area name for later use
            area_name = input_data['area_name_en'].iloc[0]
            input_no_area = input_data.drop(columns=['area_name_en'])
            
            # Apply one-hot encoding to categorical columns
            cat_cols = ['rooms_en', 'floor_bin']
            
            try:
                # Transform using the fitted OHE
                X_cat = ohe.transform(input_no_area[cat_cols])
                X_cat_df = pd.DataFrame(X_cat, columns=ohe.get_feature_names_out(cat_cols))
                
                # Combine with numerical features
                X_numerical = input_no_area.drop(columns=cat_cols)
                X_processed = pd.concat([X_numerical, X_cat_df], axis=1)
                
            except Exception as e:
                st.error(f"Error in encoding: {str(e)}")
                return None, None, None
            
            # Ensure we have all training columns
            for col in train_columns:
                if col not in X_processed.columns:
                    X_processed[col] = 0
            
            # Select only the columns that were used during training
            X_processed = X_processed[train_columns]
            X_processed = X_processed.select_dtypes(include=[np.number])
            
            return X_processed, area_name, input_data
    
        # =========================
        # PREDICTION EXECUTION
        # =========================
        if st.sidebar.button("🚀 Predict Price", type="primary", key="predict_button"):
            with st.spinner("Generating prediction..."):
                # Prepare input data
                X_input, area_name, original_input = prepare_input_data(
                    selected_area, rooms_en, floor_bin, swimming_pool, balcony, 
                    elevator, metro, has_parking, procedure_area
                )
                
                if X_input is None:
                    st.error("❌ Failed to prepare input data")
                    st.stop()
                
                if area_name in area_models:
                    model = area_models[area_name]
                    
                    try:
                        # Make prediction
                        predicted_price = model.predict(X_input)[0]
                        
                        # =========================
                        # FILTER TRAINING DATA BY EXACT SAME FEATURES
                        # =========================
                        selected_features = {
                            'rooms_en': rooms_en,
                            'floor_bin': floor_bin,
                            'swimming_pool': swimming_pool,
                            'balcony': balcony,
                            'elevator': elevator,
                            'metro': metro,
                            'has_parking': has_parking,
                            'procedure_area': procedure_area
                        }
                        
                        exact_features_data = None
                        if train_data is not None:
                            exact_features_data = filter_training_data_by_exact_features(
                                train_data, selected_features, area_name
                            )
                            
                            st.subheader("📊 Historical Data with Exact Same Features")
                            st.write(f"Found {len(exact_features_data)} historical properties with EXACT same features in {area_name}")
                            
                            if len(exact_features_data) > 0:
                                # Show summary of the filtered data
                                st.dataframe(exact_features_data[['instance_date', 'meter_sale_price', 'rooms_en', 'floor_bin', 'procedure_area']].head(10))
                        
                        # =========================
                        # CALCULATE TREND FOR EXACT SAME FEATURES
                        # =========================
                        current_year = datetime.now().year
                        trend_df = None
                        historical_yearly = None
                        
                        if exact_features_data is not None and len(exact_features_data) > 0:
                            trend_df, latest_trend, historical_yearly = calculate_trend_for_exact_features(
                                exact_features_data, current_year
                            )
                        
                        # =========================
                        # PREPARE FORECAST DATA WITH ALL GROWTH FACTORS
                        # =========================
                        forecast_data = prepare_forecast_data(growth_pivot, area_name)
                        
                        # =========================
                        # CREATE COMBINED PLOT WITH CONFIDENCE INTERVALS
                        # =========================
                        st.subheader("📈 Price Timeline: Historical Trend (Exact Features) + Forecast")
                        
                        combined_fig = create_combined_trend_forecast_plot(
                            historical_yearly, 
                            trend_df, 
                            predicted_price, 
                            forecast_data, 
                            area_name,
                            selected_features
                        )
                        
                        st.plotly_chart(combined_fig, use_container_width=True)
                        
                        # =========================
                        # DISPLAY PREDICTION RESULTS
                        # =========================
                        st.success("✅ Prediction Generated!")
                        
                        # Display input summary
                        st.subheader("📋 Selected Property Features")
                        input_display = original_input.copy()
                        input_display = input_display.T.reset_index()
                        input_display.columns = ['Feature', 'Value']
                        
                        feature_display_map = {
                            'rooms_en': 'Number of Rooms',
                            'floor_bin': 'Floor Level',
                            'swimming_pool': 'Swimming Pool',
                            'balcony': 'Balcony',
                            'elevator': 'Elevator',
                            'metro': 'Near Metro',
                            'has_parking': 'Parking',
                            'area_name_en': 'Area',
                            'procedure_area': 'Area (SqMt)'
                        }
                        
                        input_display['Feature'] = input_display['Feature'].map(feature_display_map)
                        input_display['Value'] = input_display['Value'].apply(
                            lambda x: "Yes" if x == 1 else "No" if x == 0 else x
                        )
                        
                        st.table(input_display)
                        
                        # Display prediction
                        st.subheader("💰 Current Price Prediction")
                        st.metric(
                            label="Predicted Property Price",
                            value=f"AED {predicted_price:,.0f}",
                        )
                        
                        # =========================
                        # DISPLAY FORECAST TABLE WITH ALL GROWTH FACTORS
                        # =========================
                        if forecast_data:
                            st.subheader("🔮 Future Price Forecast with Confidence Intervals")
                            st.write("Future prices calculated as: Prediction × Growth Factor")
                            
                            forecast_table_data = []
                            cumulative_price_main = predicted_price
                            cumulative_price_upper = predicted_price
                            cumulative_price_lower = predicted_price
                            
                            # Sort periods chronologically
                            sorted_periods = sorted(forecast_data.keys())
                            
                            for period in sorted_periods:
                                growth_factors = forecast_data[period]
                                
                                cumulative_price_main = cumulative_price_main * growth_factors['main']
                                cumulative_price_upper = cumulative_price_upper * growth_factors['upper']
                                cumulative_price_lower = cumulative_price_lower * growth_factors['lower']
                                
                                forecast_table_data.append({
                                    'Period': period,
                                    'Main Growth Factor': f"{growth_factors['main']:.4f}",
                                    'Upper Growth Factor': f"{growth_factors['upper']:.4f}",
                                    'Lower Growth Factor': f"{growth_factors['lower']:.4f}",
                                    'Forecasted Price (Main)': f"AED {cumulative_price_main:,.0f}",
                                    'Forecasted Price (Upper)': f"AED {cumulative_price_upper:,.0f}",
                                    'Forecasted Price (Lower)': f"AED {cumulative_price_lower:,.0f}"
                                })
                            
                            forecast_df = pd.DataFrame(forecast_table_data)
                            st.table(forecast_df)
                        
                        # =========================
                        # DISPLAY TREND ANALYSIS FOR EXACT FEATURES
                        # =========================
                        if trend_df is not None and latest_trend is not None:
                            st.subheader("📊 Trend Analysis for Exact Features")
                            
                            # Calculate trend direction and percentage difference
                            price_diff = predicted_price - latest_trend
                            price_diff_percent = (price_diff / latest_trend) * 100
                            
                            if price_diff > 0:
                                trend_direction = "increased"
                                trend_color = "green"
                            else:
                                trend_direction = "decreased"
                                trend_color = "red"
                            
                            st.info(f"""
                            **Historical Trend Analysis:**
                            - Based on **{len(exact_features_data)}** properties with **exact same features** in {area_name}
                            - Historical trend shows similar properties were around **AED {latest_trend:,.0f}**
                            - Current prediction shows a **{abs(price_diff_percent):.1f}% {trend_direction}** from historical trend
                            - This indicates the market value for these specific features has **{trend_direction}** over time
                            """)
                        
                        elif exact_features_data is not None and len(exact_features_data) > 0:
                            st.warning(f"⚠️ Found {len(exact_features_data)} properties with similar features, but insufficient data for trend analysis.")
                        else:
                            st.warning("⚠️ No historical data found with exact same features. The prediction is based on the model training.")
                        
                    except Exception as e:
                        st.error(f"❌ Prediction error: {str(e)}")
                    
                else:
                    st.error(f"❌ No model found for area: {area_name}")
        
        else:
            st.info("👆 Enter property features in the sidebar and click 'Predict Price' to generate forecasts")
    
    # =========================
    # DEBUG INFORMATION
    # =========================
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.subheader("Debug Information")
        st.sidebar.write(f"Models loaded: {len(area_models)}")
        st.sidebar.write(f"Available areas: {list(area_models.keys())}")
        st.sidebar.write(f"OHE loaded: {ohe is not None}")
        st.sidebar.write(f"Train columns: {len(train_columns) if train_columns else 0}")
        st.sidebar.write(f"Training data loaded: {train_data is not None}")
        if growth_pivot is not None:
            st.sidebar.write(f"Growth data columns: {list(growth_pivot.columns)}")
    
    
#if page == "related_info":

    #sidebar_option_3 = st.sidebar.radio("Choose Section", [
     #   "FC",
     #   "area_combination"
     # ])
if page  == "FC":
       
        import streamlit as st
        import pandas as pd
        import plotly.graph_objects as go
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
        
        app_choice = st.sidebar.selectbox("tab", ["Auto Arima with Lowess", "Previous models"])
        
        if app_choice ==  "Auto Arima with Lowess":
            # ------------------------------
            # LOAD DATA
            # ------------------------------
            
            
            forecast_df = pd.read_csv("forecast_lowess_all_areas1.csv", parse_dates=["month"])
            metrics_df = pd.read_csv("metrics_lowess_all_areas1.csv")
            summary_df = pd.read_csv("sarima_model_summary_all_areas1.csv")  # contains 'Area' and 'SARIMA_Summary'
            
            # Area selection
            areas = forecast_df['area'].unique()
            selected_area = st.selectbox("Select Area", areas)
            
            # Filter data
            area_forecast = forecast_df[forecast_df['area'] == selected_area].copy()
            # ------------------------------
            # LIMIT FORECAST TILL AUGUST 2025
            # ------------------------------
            cutoff_date = pd.Timestamp("2025-08-31")
            area_forecast = area_forecast[area_forecast["month"] <= cutoff_date]
    
            area_metrics = metrics_df[metrics_df['Area'] == selected_area].copy()
            area_summary = summary_df[summary_df['Area'] == selected_area]["SARIMA_Summary"].values
            summary_text = area_summary[0] if len(area_summary) > 0 else "Model summary not available"
            
            # ------------------------------
            # TABS
            # ------------------------------
            tab1, tab2 = st.tabs(["📈 Forecast & Metrics", "🧠 Model Summary"])
            
            # ------------------------------
            # TAB 1: Forecast & Metrics
            # ------------------------------
            with tab1:
                # ------------------------------
                # FORECAST PLOT (continuous line)
                # ------------------------------
                fig_fc = go.Figure()
                
                # Actual (LOWESS)
                fig_fc.add_trace(go.Scatter(
                    x=area_forecast['month'],
                    y=area_forecast['actual_smoothed'],
                    mode='lines',
                    name='Actual (LOWESS)',
                    line=dict(color='blue', dash='dot')
                ))
                
                # Combine train, test, forecast into continuous line
                area_forecast_sorted = area_forecast.sort_values('month')
                df_predicted = area_forecast_sorted[area_forecast_sorted['phase'].isin(['train', 'test', 'forecast'])]
                
                fig_fc.add_trace(go.Scatter(
                    x=df_predicted['month'],
                    y=df_predicted['predicted'],
                    mode='lines+markers',
                    name='Forecast',
                    line=dict(color='green', width=2)
                ))
                
                # Vertical line marking end of training period
                train_end = area_forecast[area_forecast['phase'] == 'train']['month'].max()
                if pd.notna(train_end):
                    fig_fc.add_shape(
                        type='line',
                        x0=train_end, x1=train_end,
                        y0=area_forecast['predicted'].min(),
                        y1=area_forecast['predicted'].max(),
                        line=dict(color='gray', dash='dash'),
                        xref='x', yref='y'
                    )
                    fig_fc.add_annotation(
                        x=train_end, y=area_forecast['predicted'].max(),
                        text="Train End", showarrow=False, yshift=10, font=dict(size=12, color="gray")
                    )
                
                fig_fc.update_layout(
                    xaxis_title='Month',
                    yaxis_title='Median Price',
                    title=f'{selected_area} - Forecast',
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_fc, use_container_width=True)
                
                # ------------------------------
                # METRICS BAR PLOT
                # ------------------------------
                st.subheader("📊 Train/Test Metrics")
                metrics_plot = area_metrics[['Train_MAE', 'Train_RMSE', 'Train_R2', 'Test_MAE', 'Test_RMSE', 'Test_R2']].T
                metrics_plot.columns = ['Value']
                metrics_plot.index.name = 'Metric'
                metrics_plot.reset_index(inplace=True)
                colors = ['red' if 'Train' in m else 'orange' for m in metrics_plot['Metric']]
                
                fig_metrics = go.Figure(go.Bar(
                    x=metrics_plot['Metric'],
                    y=metrics_plot['Value'],
                    marker_color=colors,
                    text=metrics_plot['Value'].round(3),
                    textposition='auto'
                ))
                
                fig_metrics.update_layout(
                    title=f'{selected_area} - Train/Test Metrics',
                    yaxis_title='Metric Value',
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_metrics, use_container_width=True)
                
                # ------------------------------
                # SCATTER PLOTS WITH LINEAR FIT & R²
                # ------------------------------
                st.subheader("🔍 Actual vs Predicted Scatter Plots")
            
                for phase in ['train', 'test']:
                    df_phase = area_forecast[area_forecast['phase'] == phase].dropna(subset=['actual_smoothed', 'predicted'])
                    
                    if df_phase.empty:
                        st.warning(f"No data available for {phase.capitalize()} phase.")
                        continue
                    
                    X = df_phase['actual_smoothed'].values.reshape(-1, 1)
                    y = df_phase['predicted'].values
            
                    # Linear fit
                    lr = LinearRegression()
                    lr.fit(X, y)
                    y_line = lr.predict(X)
                    r2 = r2_score(y, y_line)
            
                    # Scatter plot
                    fig_scatter = go.Figure()
                    fig_scatter.add_trace(go.Scatter(
                        x=X.flatten(), y=y, mode='markers',
                        name='Data Points',
                        marker=dict(color='blue', size=6, opacity=0.7)
                    ))
                    fig_scatter.add_trace(go.Scatter(
                        x=X.flatten(), y=y_line, mode='lines',
                        name=f'Linear Fit (R²={r2:.3f})',
                        line=dict(color='red', dash='dash', width=2)
                    ))
            
                    # Optional: perfect prediction line y=x
                    min_val, max_val = min(X.min(), y.min()), max(X.max(), y.max())
                    fig_scatter.add_trace(go.Scatter(
                        x=[min_val, max_val], y=[min_val, max_val],
                        mode='lines', name='Perfect Fit (y=x)',
                        line=dict(color='gray', dash='dot')
                    ))
            
                    fig_scatter.update_layout(
                        title=f'{selected_area} - {phase.capitalize()} Scatter Plot',
                        xaxis_title='Actual (LOWESS)',
                        yaxis_title='Predicted',
                        template='plotly_white'
                    )
            
                    st.plotly_chart(fig_scatter, use_container_width=True)
            
            # ------------------------------
            # TAB 2: Model Summary
            # ------------------------------
            with tab2:
                st.subheader(f"SARIMA Model Summary for {selected_area}")
                st.code(summary_text, language='text')  # keeps formatting and scrollable
    
            
        if app_choice == "Previous models":
        
            import streamlit as st
            import pandas as pd
            import numpy as np
            import plotly.graph_objects as go
            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import r2_score
        
            st.title("Model Comparison — Without Macro vs With Macro")
        
            # ============================================================
            # HELPER FUNCTION
            # ============================================================
            def load_and_prepare_data(forecast_file, metrics_file, summary_file):
                scatter_df = pd.read_csv(forecast_file, parse_dates=['Date'])
                metrics_df = pd.read_csv(metrics_file)
                summary_df = pd.read_csv(summary_file)
        
                scatter_df.columns = scatter_df.columns.str.strip()
                metrics_df.columns = metrics_df.columns.str.strip()
                summary_df.columns = summary_df.columns.str.strip()
        
                # Recalculate metrics in case metrics file is not updated
                def calculate_metrics(df):
                    metrics = []
                    for area in df['Area'].unique():
                        area_data = df[df['Area'] == area]
                        for model in area_data['Model'].unique():
                            model_data = area_data[area_data['Model'] == model]
                            for dataset in ['Train', 'Test']:
                                dataset_data = model_data[model_data['Dataset'] == dataset]
                                if len(dataset_data) > 0:
                                    actual = dataset_data['Actual'].values
                                    predicted = dataset_data['Predicted'].values
                                    mae = np.mean(np.abs(actual - predicted))
                                    mse = np.mean((actual - predicted) ** 2)
                                    rmse = np.sqrt(mse)
                                    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
                                    r2 = r2_score(actual, predicted)
                                    metrics.append({
                                        'Area': area,
                                        'Model': model,
                                        'Dataset': dataset,
                                        'MAE': mae,
                                        'MSE': mse,
                                        'RMSE': rmse,
                                        'MAPE': mape,
                                        'R2': r2
                                    })
                    return pd.DataFrame(metrics)
        
                metrics_df = calculate_metrics(scatter_df)
                return scatter_df, metrics_df, summary_df
        
            # ============================================================
            # LOAD BOTH VERSIONS
            # ============================================================
            without_macro_files = (
                "all_areas_actual_vs_predicted.csv",
                "all_areas_metrics.csv",
                "all_model_summaries.csv"
            )
        
            with_macro_files = (
                "combined_model_forecast.csv",
                "combined_metrics.csv",
                "all_model_summaries.csv"  # summaries are same format
            )
        
            scatter_df_wo, metrics_df_wo, summary_df_wo = load_and_prepare_data(*without_macro_files)
            scatter_df_w, metrics_df_w, summary_df_w = load_and_prepare_data(*with_macro_files)
        
            # ============================================================
            # AREA SELECTION
            # ============================================================
            area_list = scatter_df_wo['Area'].unique()
            selected_area = st.sidebar.selectbox("Select Area", area_list)
        
            # ============================================================
            # DEFINE FUNCTION TO DISPLAY ONE SIDE
            # ============================================================
            def display_area_section(title, scatter_df, metrics_df, summary_df):
                st.markdown(f"## {title}")
        
                forecast_df = scatter_df.copy()
                forecast_area = forecast_df[forecast_df['Area'] == selected_area]
                metrics_area = metrics_df[metrics_df['Area'] == selected_area]
                scatter_area = scatter_df[scatter_df['Area'] == selected_area]
        
                if forecast_area.empty:
                    st.warning(f"No data found for area: {selected_area}")
                    return
        
                colors = {'ARIMA': 'green', 'SARIMA': 'orange', 'Prophet': 'blue'}
        
                # ---------------------------------------------------------
                # LINE PLOT: Actual + Fitted + Forecast
                # ---------------------------------------------------------
                st.subheader("Forecast Line Plot")
        
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(
                    x=forecast_area['Date'],
                    y=forecast_area['Actual'],
                    mode='lines+markers',
                    name='Actual',
                    line=dict(color='black', width=2)
                ))
        
                for model in forecast_area['Model'].unique():
                    df_model = forecast_area[forecast_area['Model'] == model]
                    df_train = df_model[df_model['Dataset'] == 'Train']
                    df_test = df_model[df_model['Dataset'] == 'Test']
        
                    if not df_train.empty:
                        fig_line.add_trace(go.Scatter(
                            x=df_train['Date'],
                            y=df_train['Predicted'],
                            mode='lines',
                            name=f'{model} Fitted',
                            line=dict(color=colors.get(model, 'gray'), dash='dash')
                        ))
                    if not df_test.empty:
                        fig_line.add_trace(go.Scatter(
                            x=df_test['Date'],
                            y=df_test['Predicted'],
                            mode='lines',
                            name=f'{model} Forecast',
                            line=dict(color=colors.get(model, 'gray'))
                        ))
        
                fig_line.update_layout(
                    xaxis_title='Date',
                    yaxis_title='Price',
                    template='plotly_white'
                )
                st.plotly_chart(fig_line, use_container_width=True)
        
                # ---------------------------------------------------------
                # METRICS PLOTS
                # ---------------------------------------------------------
                st.subheader("Model Performance Metrics")
        
                if metrics_area.empty:
                    st.info("No metrics data available for this area.")
                else:
                    col1, col2 = st.columns(2)
        
                    # --- MAE ---
                    with col1:
                        fig_mae = go.Figure()
                        for model in metrics_area['Model'].unique():
                            for dataset in ['Train', 'Test']:
                                d = metrics_area[
                                    (metrics_area['Model'] == model) &
                                    (metrics_area['Dataset'] == dataset)
                                ]
                                if not d.empty:
                                    fig_mae.add_trace(go.Bar(
                                        name=f'{model} {dataset}',
                                        x=[f'{model} {dataset}'],
                                        y=[d['MAE'].values[0]],
                                        marker_color=colors.get(model, 'gray')
                                    ))
                        fig_mae.update_layout(title='MAE', template='plotly_white')
                        st.plotly_chart(fig_mae, use_container_width=True)
        
                        # --- RMSE ---
                        fig_rmse = go.Figure()
                        for model in metrics_area['Model'].unique():
                            for dataset in ['Train', 'Test']:
                                d = metrics_area[
                                    (metrics_area['Model'] == model) &
                                    (metrics_area['Dataset'] == dataset)
                                ]
                                if not d.empty:
                                    fig_rmse.add_trace(go.Bar(
                                        name=f'{model} {dataset}',
                                        x=[f'{model} {dataset}'],
                                        y=[d['RMSE'].values[0]],
                                        marker_color=colors.get(model, 'gray')
                                    ))
                        fig_rmse.update_layout(title='RMSE', template='plotly_white')
                        st.plotly_chart(fig_rmse, use_container_width=True)
        
                    # --- MAPE & R2 ---
                    with col2:
                        fig_mape = go.Figure()
                        for model in metrics_area['Model'].unique():
                            for dataset in ['Train', 'Test']:
                                d = metrics_area[
                                    (metrics_area['Model'] == model) &
                                    (metrics_area['Dataset'] == dataset)
                                ]
                                if not d.empty:
                                    fig_mape.add_trace(go.Bar(
                                        name=f'{model} {dataset}',
                                        x=[f'{model} {dataset}'],
                                        y=[d['MAPE'].values[0]],
                                        marker_color=colors.get(model, 'gray')
                                    ))
                        fig_mape.update_layout(title='MAPE (%)', template='plotly_white')
                        st.plotly_chart(fig_mape, use_container_width=True)
        
                        fig_r2 = go.Figure()
                        for model in metrics_area['Model'].unique():
                            for dataset in ['Train', 'Test']:
                                d = metrics_area[
                                    (metrics_area['Model'] == model) &
                                    (metrics_area['Dataset'] == dataset)
                                ]
                                if not d.empty:
                                    fig_r2.add_trace(go.Bar(
                                        name=f'{model} {dataset}',
                                        x=[f'{model} {dataset}'],
                                        y=[d['R2'].values[0]],
                                        marker_color=colors.get(model, 'gray')
                                    ))
                        fig_r2.update_layout(title='R²', template='plotly_white')
                        st.plotly_chart(fig_r2, use_container_width=True)
        
                # ---------------------------------------------------------
                # SCATTER: ACTUAL vs PREDICTED
                # ---------------------------------------------------------
                st.subheader("Actual vs Predicted — Scatter Plot")
        
                for dataset in ['Train', 'Test']:
                    st.markdown(f"**{dataset} Dataset**")
                    fig_scatter = go.Figure()
                    df_dataset = scatter_area[scatter_area['Dataset'] == dataset]
        
                    if df_dataset.empty:
                        st.info(f"No {dataset} data available.")
                        continue
        
                    for model in df_dataset['Model'].unique():
                        df_sc = df_dataset[df_dataset['Model'] == model].dropna(subset=['Actual', 'Predicted'])
                        if df_sc.empty:
                            continue
        
                        x, y = df_sc['Actual'].values, df_sc['Predicted'].values
                        fig_scatter.add_trace(go.Scatter(
                            x=x, y=y, mode='markers', name=model,
                            marker=dict(color=colors.get(model, 'gray'))
                        ))
        
                        if len(x) > 1:
                            lr = LinearRegression()
                            lr.fit(x.reshape(-1, 1), y.reshape(-1, 1))
                            y_fit = lr.predict(x.reshape(-1, 1)).ravel()
                            r2 = r2_score(y, y_fit)
                            fig_scatter.add_trace(go.Scatter(
                                x=x, y=y_fit, mode='lines',
                                name=f"{model} Fit (R²={r2:.3f})",
                                line=dict(color=colors.get(model, 'gray'), dash='dash')
                            ))
        
                    # Add y=x line
                    min_val, max_val = df_dataset[['Actual', 'Predicted']].min().min(), df_dataset[['Actual', 'Predicted']].max().max()
                    fig_scatter.add_trace(go.Scatter(
                        x=[min_val, max_val], y=[min_val, max_val],
                        mode='lines', name='y=x', line=dict(color='black', dash='dot')
                    ))
        
                    fig_scatter.update_layout(template='plotly_white', xaxis_title='Actual', yaxis_title='Predicted')
                    st.plotly_chart(fig_scatter, use_container_width=True)
        
                # ---------------------------------------------------------
                # MODEL SUMMARIES
                # ---------------------------------------------------------
                st.subheader("ARIMA & SARIMA Model Summaries")
        
                area_summaries = summary_df[summary_df['Area'].str.strip() == selected_area]
                if area_summaries.empty:
                    st.info("No summaries available.")
                    return
        
                area_summaries['Model'] = area_summaries['Model'].str.strip().str.upper()
        
                # ARIMA
                arima_row = area_summaries[area_summaries['Model'] == 'ARIMA']
                if not arima_row.empty:
                    st.markdown("### ARIMA Model Summary")
                    st.code(arima_row['Summary'].values[0], language='text')
                else:
                    st.info("ARIMA summary not available.")
        
                # SARIMA
                sarima_row = area_summaries[area_summaries['Model'] == 'SARIMA']
                if not sarima_row.empty:
                    st.markdown("### SARIMA Model Summary")
                    st.code(sarima_row['Summary'].values[0], language='text')
                else:
                    st.info("SARIMA summary not available.")
        
            # ============================================================
            # DISPLAY SIDE BY SIDE
            # ============================================================
            col1, col2 = st.columns(2)
        
            with col1:
                display_area_section("Without Macro", scatter_df_wo, metrics_df_wo, summary_df_wo)
        
            with col2:
                display_area_section("With Macro", scatter_df_w, metrics_df_w, summary_df_w)
    
    #######################################################################################################################################################################################################################
    
    #######################################################################################################################################################################################################################
if page  ==  "area_combination":
        st.subheader("Dubai Area-wise Bubble Map")
        st.sidebar.text(
        """
        Proxy with more than 1 area:
    
        0 Al Merkadh, Al Barsha South Third
        1                             Nadd Hessa
        2     Bukadra, Madinat Dubai Almelaheyah
        3             Burj Khalifa, Business Bay
        4        Jabal Ali First, Me'Aisem First
        5             Palm Jumeirah, Marsa Dubai
        6                        Al Warsan First
        7                             Al Merkadh
        8                           Burj Khalifa
        9                           Business Bay
        10                     Madinat Al Mataar
        """
        )
        # Load your two datasets
        df1 = pd.read_csv("df_plot_p1_og.csv")
        df2 = pd.read_csv("df_plot_p2_og.csv")
        df3 = pd.read_csv("df_plot_p1.csv")
        df4 = pd.read_csv("df_plot_p2.csv")    # or your second file
        df5 = pd.read_csv("df_plot_p.csv")
        df6 = pd.read_csv("df_plot_p1_21.csv")
        df7 = pd.read_csv("df_plot_p2_21.csv")
        df8 = pd.read_csv("df_plot_p_m_21.csv")
        # Step 1: Choose dataset
        dataset_choice = st.radio(
            "Select Dataset",
            ("Proxy_1_original", "Proxy_2_original","Proxy_1", "Proxy_2", "Modified", "Proxy_1_2021", "Proxy_2_21","Proxy_21_modified_proxy")
        )
        
        # Step 2: Assign the selected dataframe
        if dataset_choice == "Proxy_1_original":
            df = df1
        elif dataset_choice == "Proxy_2_original":
            df = df2 
        elif dataset_choice == "Proxy_1":
            df = df3
        elif dataset_choice == "Proxy_2":
            df = df4
        elif dataset_choice == "Modified":
            df = df5 
        elif dataset_choice == "Proxy_1_2021":
            df = df6
        elif dataset_choice == "Proxy_2_2021":
            df = df7
        else:
            df = df8
            
        
        # Step 3: Select Proxy_2 from chosen dataset
        proxy_list = df["Proxy"].dropna().unique()
        selected_proxy = st.selectbox("Select Proxy", proxy_list)
        
        # Step 4: Filter for the selected Proxy_2
        filtered_df = df[df["Proxy"] == selected_proxy]
        
        # Display the map
        tab1, = st.tabs(["Average Meter Sale Price"])
        
        with tab1:
        
            fig = px.scatter_mapbox(
                filtered_df,
                lat='area_lat',
                lon='area_lon',
                size='nRecords',
                color='Average Meter Sale Price',
                hover_name='area_name_en',
                hover_data={
                    'nRecords': True,
                    'Average Meter Sale Price': ':.2f',
                    'area_lat': False,
                    'area_lon': False
                },
                color_continuous_scale='Hot',
                size_max=30,
                zoom=9,
                title=f"{dataset_choice}: Areas Under {selected_proxy}"
            )
        
            fig.update_layout(
                mapbox_style='open-street-map',
                margin={"r": 0, "t": 40, "l": 0, "b": 0}
            )
        
            st.plotly_chart(fig, use_container_width=True)

#######################################################################################################################################################################################################################
if page == "V_2.2":
        st.title("V_2.2: prediction dashboard")
        
        # This will display the external app in a box on your dashboard
        st.link_button("Go to Price Predictor", "https://flipose-re-price-prediction.streamlit.app/")
    
