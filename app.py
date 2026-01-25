import os
import requests
import pandas as pd
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import Dash, html, dcc, Input, Output, State, exceptions
from geopy.geocoders import Nominatim
from datetime import datetime
import random

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server

ua_string = f"specusol_address_engine_{random.randint(1000, 9999)}"
geolocator = Nominatim(user_agent=ua_string)

GLASS_STYLE = {
    "background": "rgba(255, 255, 255, 0.05)",
    "backdropFilter": "blur(10px)",
    "borderRadius": "15px",
    "border": "1px solid rgba(255, 255, 255, 0.1)",
    "padding": "20px",
    "marginBottom": "20px"
}

app.layout = dbc.Container(fluid=True, className="p-4", children=[
    dbc.Row([
        dbc.Col([
            html.H1(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0"),
            html.P("Texas Solar & Environmental Intelligence", className="text-muted small")
        ], width=7),
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="addr-input", placeholder="Enter full address...", type="text", className="bg-dark text-white"),
                dbc.Button("LOCATE", id="addr-btn", color="warning", className="fw-bold"),
            ])
        ], width=5, className="align-self-center")
    ], className="mb-4"),

    # Map Section
    dbc.Row([
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -99.0], zoom=6, style={"height": "500px", "borderRadius": "12px"}, id="texas-map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer")
                ])
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # Weather App Style Forecast Row
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("7-HOUR LOCALIZED FORECAST", className="text-info mb-3 fw-bold"),
                dbc.Row(id="forecast-row", className="text-center g-2")
            ], style=GLASS_STYLE)
        ], width=12)
    ]),
    
    dcc.Store(id='coords-store', data={'lat': 31.0, 'lon': -99.0})
])

# --- Callbacks ---

@app.callback(
    [Output("texas-map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    Input("addr-btn", "n_clicks"),
    State("addr-input", "value"),
    prevent_initial_call=True
)
def geocode_address(n, address):
    if not address:
        raise exceptions.PreventUpdate
    try:
        # Improved search logic for full addresses
        loc = geolocator.geocode(address, timeout=10)
        if loc:
            viewport = {"center": [loc.latitude, loc.longitude], "zoom": 14, "transition": "flyTo"}
            marker = [dl.Marker(position=[loc.latitude, loc.longitude], children=dl.Tooltip(address))]
            return viewport, marker, {'lat': loc.latitude, 'lon': loc.longitude}
    except Exception as e:
        print(f"Geocoding Error: {e}")
    return {"center": [31.0, -99.0], "zoom": 6}, [], {'lat': 31.0, 'lon': -99.0}

@app.callback(
    Output("forecast-row", "children"),
    Input("coords-store", "data")
)
def update_forecast(coords):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&hourly=temperature_2m,weathercode&timezone=auto"
        r = requests.get(url, timeout=5).json()
        
        forecast_cards = []
        # Get the next 7 hours
        for i in range(7):
            temp = r['hourly']['temperature_2m'][i]
            time_raw = r['hourly']['time'][i]
            time_obj = datetime.strptime(time_raw, "%Y-%m-%dT%H:%M")
            time_str = time_obj.strftime("%I %p")
            
            card = dbc.Col([
                html.Div([
                    html.Small(time_str, className="text-muted d-block"),
                    html.H4(f"{temp}°C", className="text-warning my-2"),
                    html.I(className="fas fa-cloud text-info") # Simple placeholder icon
                ], className="p-3 border border-secondary rounded")
            ], xs=4, md=True)
            forecast_cards.append(card)
        
        return forecast_cards
    except Exception as e:
        print(f"Forecast Error: {e}")
        return [html.P("Forecast data unavailable for this location.", className="text-muted")]

if __name__ == "__main__":
    app.run_server(debug=True)
