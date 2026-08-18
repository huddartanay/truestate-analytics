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
    
    
    forecast_df = pd.read_csv("forecast_lowess_all_areas_extended.csv", parse_dates=["Month"])
    metrics_df = pd.read_csv("metrics_lowess_all_areas_extended.csv")
    summary_df = pd.read_csv("sarima_model_summary_all_areas_extended.csv")  # contains 'Area' and 'SARIMA_Summary'
    
    # Area selection
    areas = forecast_df['Area'].unique()
    selected_area = st.selectbox("Select Area", areas)
    
    # Filter data
    area_forecast = forecast_df[forecast_df['Area'] == selected_area].copy()
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
            x=area_forecast['Month'],
            y=area_forecast['Actual_Smoothed'],
            mode='lines',
            name='Actual (LOWESS)',
            line=dict(color='blue', dash='dot')
        ))
        
        # Combine train, test, forecast into continuous line
        area_forecast_sorted = area_forecast.sort_values('Month')
        df_predicted = area_forecast_sorted[area_forecast_sorted['Phase'].isin(['train', 'test', 'forecast'])]
        
        fig_fc.add_trace(go.Scatter(
            x=df_predicted['Month'],
            y=df_predicted['Predicted'],
            mode='lines+markers',
            name='Forecast',
            line=dict(color='green', width=2)
        ))
        
        # Vertical line marking end of training period
        train_end = area_forecast[area_forecast['Phase'] == 'train']['Month'].max()
        if pd.notna(train_end):
            fig_fc.add_shape(
                type='line',
                x0=train_end, x1=train_end,
                y0=area_forecast['Predicted'].min(),
                y1=area_forecast['Predicted'].max(),
                line=dict(color='gray', dash='dash'),
                xref='x', yref='y'
            )
            fig_fc.add_annotation(
                x=train_end, y=area_forecast['Predicted'].max(),
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
            df_phase = area_forecast[area_forecast['Phase'] == phase].dropna(subset=['Actual_Smoothed', 'Predicted'])
            
            if df_phase.empty:
                st.warning(f"No data available for {phase.capitalize()} phase.")
                continue
            
            X = df_phase['Actual_Smoothed'].values.reshape(-1, 1)
            y = df_phase['Predicted'].values
    
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




    
    # ------------------------------
    # TAB 2: Model Summary
    # ------------------------------
    with tab2:
        st.subheader(f"SARIMA Model Summary for {selected_area}")
        st.code(summary_text, language='text')  # keeps formatting and scrollable

if app_choice ==  "Previous models":
    import streamlit as st
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    import streamlit as st
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    
    # -----------------------------
    # Read data from uploaded file
    # -----------------------------
    
    # -----------------------------
    # Load data
    # -----------------------------
    #forecast_df = pd.read_csv("all_areas_forecast.csv", parse_dates=['Date'])
    metrics_df = pd.read_csv("all_areas_metrics.csv")
    scatter_df = pd.read_csv("all_areas_actual_vs_predicted.csv", parse_dates=['Date'])
    summary_df1 = pd.read_csv("all_model_summaries.csv")
    # Strip column names to remove any extra spaces
    #forecast_df.columns = forecast_df.columns.str.strip()
    metrics_df.columns = metrics_df.columns.str.strip()
    scatter_df.columns = scatter_df.columns.str.strip()

    # -----------------------------
    # Read data from uploaded file
    # -----------------------------
    @st.cache_data
    def load_data():
        # Read the uploaded CSV file
        df = pd.read_csv("all_areas_actual_vs_predicted.csv", parse_dates=['Date'])
        df.columns = df.columns.str.strip()
        return df
    
    # Load the data
    scatter_df = load_data()
    
    # -----------------------------
    # Create forecast_df and metrics_df from scatter_df
    # -----------------------------
    # forecast_df is essentially the same as scatter_df for our purposes
    forecast_df = scatter_df.copy()
    
    # Create metrics_df by calculating metrics from scatter_df
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
                        
                        # Calculate metrics
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
    
    # -----------------------------
    # Sidebar selection
    # -----------------------------
    area_list = forecast_df['Area'].unique()
    selected_area = st.sidebar.selectbox("Select Area", area_list)
    
    # Filter for selected area
    forecast_area = forecast_df[forecast_df['Area'] == selected_area]
    metrics_area = metrics_df[metrics_df['Area'] == selected_area]
    scatter_area = scatter_df[scatter_df['Area'] == selected_area]
    #area_summary = summary_df[summary_df['Area'] == selected_area]["Summary"].values

    #summary_text = area_summary[0] if len(area_summary) > 0 else "Model summary not available"
    # Check if area data exists
    if forecast_area.empty:
        st.warning(f"No forecast data found for area: {selected_area}")
    else:
        # -----------------------------
        # Line plot: Actual + Fitted + Forecast
        # -----------------------------
        st.subheader(f"Forecast Line Plot — {selected_area}")
    
        fig_line = go.Figure()
    
        # Actual values
        fig_line.add_trace(go.Scatter(
            x=forecast_area['Date'],
            y=forecast_area['Actual'],
            mode='lines+markers',
            name='Actual',
            line=dict(color='black', width=2)
        ))
    
        models = forecast_area['Model'].unique()
        colors = {'ARIMA': 'green', 'SARIMA': 'orange', 'Prophet': 'blue'}
    
        for model in models:
            df_model = forecast_area[forecast_area['Model'] == model]
            
            # Fitted (Train)
            df_train = df_model[df_model['Dataset'] == 'Train']
            if not df_train.empty:
                fig_line.add_trace(go.Scatter(
                    x=df_train['Date'],
                    y=df_train['Predicted'],
                    mode='lines',
                    name=f'{model} Fitted',
                    line=dict(color=colors.get(model, 'gray'), dash='dash')
                ))
            
            # Forecast (Test)
            df_test = df_model[df_model['Dataset'] == 'Test']
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
            legend_title='Legend',
            template='plotly_white'
        )
    
        st.plotly_chart(fig_line, use_container_width=True)
    
        # -----------------------------
        # Metrics Plots (replaced table with plots)
        # -----------------------------
        st.subheader("Model Performance Metrics")
    
        if metrics_area.empty:
            st.info("No metrics data available for this area.")
        else:
            # Create separate plots for each metric
            metrics_to_plot = ['MAE', 'RMSE', 'MAPE', 'R2']
            metric_titles = {
                'MAE': 'Mean Absolute Error (MAE)',
                'RMSE': 'Root Mean Square Error (RMSE)', 
                'MAPE': 'Mean Absolute Percentage Error (MAPE)',
                'R2': 'R-squared (R²)'
            }
            
            # Create 2x2 grid of metrics
            col1, col2 = st.columns(2)
            
            with col1:
                # MAE Plot
                fig_mae = go.Figure()
                for model in metrics_area['Model'].unique():
                    model_data = metrics_area[metrics_area['Model'] == model]
                    for dataset in ['Train', 'Test']:
                        dataset_data = model_data[model_data['Dataset'] == dataset]
                        if not dataset_data.empty:
                            fig_mae.add_trace(go.Bar(
                                name=f'{model} {dataset}',
                                x=[f'{model} {dataset}'],
                                y=[dataset_data['MAE'].values[0]],
                                marker_color=colors.get(model, 'gray'),
                                showlegend=True
                            ))
                fig_mae.update_layout(
                    title='Mean Absolute Error (MAE)',
                    yaxis_title='MAE',
                    template='plotly_white',
                    showlegend=True
                )
                st.plotly_chart(fig_mae, use_container_width=True)
                
                # RMSE Plot
                fig_rmse = go.Figure()
                for model in metrics_area['Model'].unique():
                    model_data = metrics_area[metrics_area['Model'] == model]
                    for dataset in ['Train', 'Test']:
                        dataset_data = model_data[model_data['Dataset'] == dataset]
                        if not dataset_data.empty:
                            fig_rmse.add_trace(go.Bar(
                                name=f'{model} {dataset}',
                                x=[f'{model} {dataset}'],
                                y=[dataset_data['RMSE'].values[0]],
                                marker_color=colors.get(model, 'gray'),
                                showlegend=False
                            ))
                fig_rmse.update_layout(
                    title='Root Mean Square Error (RMSE)',
                    yaxis_title='RMSE',
                    template='plotly_white',
                    showlegend=False
                )
                st.plotly_chart(fig_rmse, use_container_width=True)
            
            with col2:
                # MAPE Plot
                fig_mape = go.Figure()
                for model in metrics_area['Model'].unique():
                    model_data = metrics_area[metrics_area['Model'] == model]
                    for dataset in ['Train', 'Test']:
                        dataset_data = model_data[model_data['Dataset'] == dataset]
                        if not dataset_data.empty:
                            fig_mape.add_trace(go.Bar(
                                name=f'{model} {dataset}',
                                x=[f'{model} {dataset}'],
                                y=[dataset_data['MAPE'].values[0]],
                                marker_color=colors.get(model, 'gray'),
                                showlegend=False
                            ))
                fig_mape.update_layout(
                    title='Mean Absolute Percentage Error (MAPE)',
                    yaxis_title='MAPE (%)',
                    template='plotly_white',
                    showlegend=False
                )
                st.plotly_chart(fig_mape, use_container_width=True)
                
                # R2 Plot
                fig_r2 = go.Figure()
                for model in metrics_area['Model'].unique():
                    model_data = metrics_area[metrics_area['Model'] == model]
                    for dataset in ['Train', 'Test']:
                        dataset_data = model_data[model_data['Dataset'] == dataset]
                        if not dataset_data.empty:
                            fig_r2.add_trace(go.Bar(
                                name=f'{model} {dataset}',
                                x=[f'{model} {dataset}'],
                                y=[dataset_data['R2'].values[0]],
                                marker_color=colors.get(model, 'gray'),
                                showlegend=False
                            ))
                fig_r2.update_layout(
                    title='R-squared (R²)',
                    yaxis_title='R²',
                    template='plotly_white',
                    showlegend=False
                )
                st.plotly_chart(fig_r2, use_container_width=True)
    
        # -----------------------------
        # Scatter plots: Actual vs Predicted
        # -----------------------------
        st.subheader("Actual vs Predicted — Scatter Plots with Linear Fit")
    
        for dataset in ['Train', 'Test']:
            st.markdown(f"**{dataset} Dataset**")
            fig_scatter = go.Figure()
            
            df_dataset = scatter_area[scatter_area['Dataset'] == dataset]
            if df_dataset.empty:
                st.info(f"No {dataset} data available for this area.")
                continue
                
            for model in models:
                df_sc = df_dataset[df_dataset['Model'] == model]
                if len(df_sc) == 0:
                    continue
                    
                # Remove any NaN values
                df_sc = df_sc.dropna(subset=['Actual', 'Predicted'])
                if len(df_sc) == 0:
                    continue
                    
                x = df_sc['Actual'].values
                y = df_sc['Predicted'].values
                
                # Scatter points
                fig_scatter.add_trace(go.Scatter(
                    x=x, y=y, mode='markers', name=model, 
                    marker=dict(color=colors.get(model, 'gray'))
                ))
                
                # Linear regression line
                if len(x) > 1:  # Need at least 2 points for regression
                    lr = LinearRegression()
                    lr.fit(x.reshape(-1, 1), y.reshape(-1, 1))
                    y_fit = lr.predict(x.reshape(-1, 1)).ravel()
                    r2 = r2_score(y, y_fit)
                    fig_scatter.add_trace(go.Scatter(
                        x=x, y=y_fit, mode='lines', 
                        name=f"{model} Fit (R²={r2:.3f})",
                        line=dict(color=colors.get(model, 'gray'), dash='dash'),
                        showlegend=True
                    ))
            
            # y=x reference line
            if not df_dataset.empty:
                all_actual = df_dataset['Actual'].dropna()
                all_predicted = df_dataset['Predicted'].dropna()
                if len(all_actual) > 0 and len(all_predicted) > 0:
                    min_val = min(all_actual.min(), all_predicted.min())
                    max_val = max(all_actual.max(), all_predicted.max())
                    fig_scatter.add_trace(go.Scatter(
                        x=[min_val, max_val], y=[min_val, max_val], mode='lines',
                        name='y=x', line=dict(color='black', dash='dot')
                    ))
            
            fig_scatter.update_layout(
                xaxis_title='Actual',
                yaxis_title='Predicted',
                legend_title='Legend',
                template='plotly_white'
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
            

    # -----------------------------
    # MODEL SUMMARIES — ARIMA and SARIMA (for selected area)
    # -----------------------------
    # -----------------------------
    # MODEL SUMMARIES — ARIMA and SARIMA (for selected area)
    # -----------------------------
    st.subheader(f"ARIMA & SARIMA Model Summaries — {selected_area}")
    
    # Filter only the selected area
    area_summaries = summary_df1[summary_df1['Area'].str.strip() == selected_area]
    
    if area_summaries.empty:
        st.info(f"No model summaries available for {selected_area}.")
    else:
        # Ensure consistent capitalization for matching
        area_summaries['Model'] = area_summaries['Model'].str.strip().str.upper()
    
        # --- ARIMA ---
        arima_row = area_summaries[area_summaries['Model'] == 'ARIMA']
        if not arima_row.empty:
            st.markdown("### ARIMA Model Summary")
            st.code(arima_row['Summary'].values[0], language='text')
        else:
            st.info("ARIMA summary not available for this area.")
    
        # --- SARIMA ---
        sarima_row = area_summaries[area_summaries['Model'] == 'SARIMA']
        if not sarima_row.empty:
            st.markdown("### SARIMA Model Summary")
            st.code(sarima_row['Summary'].values[0], language='text')
        else:
            st.info("SARIMA summary not available for this area.")



