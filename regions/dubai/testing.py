import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
    
st.title("🔍 FlipOse-RE-Analytics-V2.1")

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
            "fore_cast_raw_data": "forcast_model_16_25.csv",
            "Actual_data": "over_all_dataset_og.csv",
            "Areas with 6000": "df_trained_dataset_6000.csv"
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
