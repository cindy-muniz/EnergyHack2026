import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import dash_leaflet as dl
import requests
import json

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout for the webpage
app.layout = html.Div([
    dbc.Row([
        # Left column: Map with weather overlay
        dbc.Col([
            dl.Map(
                [dl.TileLayer(), 
                 dl.MarkerClusterGroup(id="markers")],
                id="map", 
                center=[40.7128, -74.0060],  # Default location (New York)
                zoom=5,
                style={'width': '100%', 'height': '500px'}
            )
        ], width=6),

        # Right column: Chart
        dbc.Col([
            dcc.Graph(id="supply-demand-chart"),
            html.Div(id="gemini-summary", style={'margin-top': '20px'}),
        ], width=6)
    ])
])

# Callback to update the chart and weather data based on map click
@app.callback(
    [Output("supply-demand-chart", "figure"),
     Output("gemini-summary", "children"),
     Output("markers", "children")],
    [Input("map", "click_lat_lng")]
)
def update_content(latlng):
    if latlng is None:
        return go.Figure(), "", []

    lat, lng = latlng

    # Example: Fetch data for the clicked location
    chart_data = get_supply_demand_data(lat, lng)
    weather_data = get_weather_data(lat, lng)
    gemini_summary = get_gemini_ai_summary()

    # Create the supply-demand chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chart_data['time'], y=chart_data['residential_demand'], mode='lines', name='Residential Demand'))
    fig.add_trace(go.Scatter(x=chart_data['time'], y=chart_data['commercial_demand'], mode='lines', name='Commercial Demand'))
    fig.add_trace(go.Scatter(x=chart_data['time'], y=chart_data['equilibrium'], mode='lines', name='Equilibrium'))
    fig.update_layout(title="Supply & Demand vs. Equilibrium", xaxis_title="Time", yaxis_title="MW")

    # Update the Gemini AI summary
    gemini_text = f"Gemini AI Analysis: {gemini_summary}"

    # Update weather markers on the map
    markers = [dl.Marker(position=[lat, lng], children=[dl.Popup(f"Weather: {weather_data['description']}")])]

    return fig, gemini_text, markers


# Function to fetch supply & demand data (example)
def get_supply_demand_data(lat, lng):
    # This is a placeholder. Replace with your API or data-fetching logic.
    return {
        "time": [0, 1, 2, 3, 4, 5],
        "residential_demand": [100, 120, 110, 130, 140, 150],
        "commercial_demand": [50, 55, 60, 65, 70, 75],
        "equilibrium": [80, 85, 90, 95, 100, 105]
    }


# Function to fetch weather data (example)
def get_weather_data(lat, lng):
    # Replace with an actual weather API
    weather_response = {
        "description": "Clear sky",
        "temperature": "25°C",
    }
    return weather_response


# Function to fetch Gemini AI summary (example)
def get_gemini_ai_summary():
    # Replace with the actual API call
    summary_response = "Gemini AI predicts an upward trend in solar production with higher demand in the coming months."
    return summary_response


if __name__ == '__main__':
    app.run_server(debug=True)

