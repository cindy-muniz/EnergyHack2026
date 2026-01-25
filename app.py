import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objs as go
import pandas as pd
import requests
import openai
import yfinance as yf
from dash.dependencies import Input, Output
import json

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Your OpenAI API Key (use environment variables for better security)
openai.api_key = 'your-openai-api-key-here'

# Sample map data (replace with your actual data and coordinates)
map_data = [
    {"name": "ERCOT Zone 1", "lat": 30.0, "lon": -97.0},
    {"name": "ERCOT Zone 2", "lat": 31.0, "lon": -98.0},
    {"name": "ERCOT Zone 3", "lat": 32.0, "lon": -99.0}
]

# Sample weather data (replace with your actual weather API call)
weather_data = [
    {"name": "ERCOT Zone 1", "temperature": 22.5, "wind_speed": 10, "lat": 30.0, "lon": -97.0},
    {"name": "ERCOT Zone 2", "temperature": 23.1, "wind_speed": 12, "lat": 31.0, "lon": -98.0},
    {"name": "ERCOT Zone 3", "temperature": 21.8, "wind_speed": 8, "lat": 32.0, "lon": -99.0}
]

# Placeholder for solar data (replace with actual supply/demand data)
supply_demand_data = pd.DataFrame({
    'time': pd.date_range(start='2023-01-01', periods=24, freq='H'),
    'residential_demand': [200 + i * 2 for i in range(24)],
    'commercial_demand': [500 + i * 3 for i in range(24)],
    'solar_supply': [300 + i * 4 for i in range(24)],
    'equilibrium': [350 + i * 2 for i in range(24)],
    'TOU_pricing': [0.12 + i * 0.001 for i in range(24)]
})

# Layout with map on the left, chart on the right
app.layout = html.Div([
    dbc.Row([
        # Map section (Left side)
        dbc.Col([
            dl.Map([
                dl.TileLayer(),
                dl.LayerGroup(id="weather-layer"),
                dl.MarkerCluster([
                    dl.Marker(position=(zone["lat"], zone["lon"]), children=[
                        dl.Tooltip(zone["name"])
                    ]) for zone in map_data
                ])
            ], id="map", style={'height': '500px'}),
        ], width=6),

        # Chart section (Right side)
        dbc.Col([
            dcc.Graph(id='supply-demand-chart'),
            html.Div(id='gemini-summary')
        ], width=6)
    ])
])

# Callback to overlay weather data on the map
@app.callback(
    Output('weather-layer', 'children'),
    Input('map', 'click_lat_lng')
)
def update_weather_on_map(click_lat_lng):
    weather_markers = []
    
    # Filter weather data based on the clicked coordinates
    if click_lat_lng:
        clicked_lat, clicked_lon = click_lat_lng
        for data in weather_data:
            if abs(data['lat'] - clicked_lat) < 1 and abs(data['lon'] - clicked_lon) < 1:
                weather_markers.append(
                    dl.Marker(position=(data['lat'], data['lon']), children=[
                        dl.Tooltip(f"Temp: {data['temperature']}°C, Wind: {data['wind_speed']} km/h")
                    ])
                )
    return weather_markers

# Callback to update chart when clicking on the map
@app.callback(
    Output('supply-demand-chart', 'figure'),
    Input('map', 'click_lat_lng')
)
def update_chart(click_lat_lng):
    # If a map location is clicked, filter supply and demand data accordingly
    if click_lat_lng:
        clicked_lat, clicked_lon = click_lat_lng
        zone = next((zone for zone in map_data if abs(zone['lat'] - clicked_lat) < 1 and abs(zone['lon'] - clicked_lon) < 1), None)
        if zone:
            # Filter supply/demand data (this is a simple placeholder, adapt it as needed)
            supply_demand_data_filtered = supply_demand_data
            figure = {
                'data': [
                    go.Scatter(x=supply_demand_data_filtered['time'], y=supply_demand_data_filtered['residential_demand'], mode='lines', name='Residential Demand'),
                    go.Scatter(x=supply_demand_data_filtered['time'], y=supply_demand_data_filtered['commercial_demand'], mode='lines', name='Commercial Demand'),
                    go.Scatter(x=supply_demand_data_filtered['time'], y=supply_demand_data_filtered['solar_supply'], mode='lines', name='Solar Supply'),
                    go.Scatter(x=supply_demand_data_filtered['time'], y=supply_demand_data_filtered['equilibrium'], mode='lines', name='Equilibrium'),
                    go.Scatter(x=supply_demand_data_filtered['time'], y=supply_demand_data_filtered['TOU_pricing'], mode='lines', name='TOU Pricing'),
                ],
                'layout': go.Layout(title=f"Supply and Demand for {zone['name']}", xaxis={'title': 'Time'}, yaxis={'title': 'MW / Pricing'}),
            }
            return figure
    return {}

# Callback to fetch Gemini AI summary
@app.callback(
    Output('gemini-summary', 'children'),
    Input('map', 'click_lat_lng')
)
def fetch_gemini_summary(click_lat_lng):
    if click_lat_lng:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt="Summarize the latest data on the solar energy market and trends for investment.",
            temperature=0.5,
            max_tokens=100
        )
        return html.Div([
            html.H5("Gemini AI Summary:"),
            html.P(response.choices[0].text.strip())
        ])
    return "Select a location on the map to get the summary."

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)


