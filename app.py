import os
import requests
import pandas as pd
import yfinance as yf
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
import numpy as np
from dash import Dash, html, dcc, Input, Output, State, exceptions
from geopy.geocoders import Nominatim
from datetime import datetime

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent="energy_hack_texas_final_v3")

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
            html.P("Texas Solar Supply & Weather Analytics", className="text-muted small")
        ], width=8),
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="zip-input", placeholder="Texas Zip...", type="text", className="bg-dark text-white"),
                dbc.Button("ANALYZE", id="zip-btn", color="warning", className="fw-bold"),
            ])
        ], width=4, className="align-self-center")
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.Div([
                # Weather Radar Toggle now in BLUE
                dbc.Checklist(
                    options=[{"label": "Show Weather Radar", "value": 1}],
                    value=[], id="weather-toggle", switch=True,
                    className="mb-2 text-info fw-bold" 
                ),
                dl.Map(center=[31.0, -99.0], zoom=6, style={"height": "450px", "borderRadius": "12px"}, id="texas-map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer"),
                    dl.LayerGroup(id="weather-radar-layer")
                ])
            ], style=GLASS_STYLE)
        ], lg=5, md=12),

        dbc.Col([
            html.Div([
                dcc.Graph(id="live-supply-demand", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], lg=7, md=12)
    ]),

    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("MARKET VOLATILITY (HOURLY OHLC)", className="text-warning mb-3 fw-bold"),
                dcc.Graph(id="market-candlestick")
            ], style=GLASS_STYLE)
        ], lg=8, md=12),
        
        dbc.Col([
            html.Div([
                # ETF Header now in BLUE
                html.H6("SOLAR TEXAS MUTUAL FUND (TAN)", className="text-info mb-3 fw-bold"),
                dcc.Graph(id="solar-etf-mini", style={"height": "320px"})
            ], style=GLASS_STYLE)
        ], lg=4, md=12)
    ]),
    
    dcc.Store(id='coords-store', data={'lat': 31.0, 'lon': -99.0})
])

# --- Logic: Fallback Mock Data ---
def get_mock_data():
    times = pd.date_range(start=datetime.now(), periods=24, freq='H')
    return pd.DataFrame({
        'time': times,
        'supply_mw': [max(0, 40 * np.sin((i-6) * np.pi / 12)) for i in range(24)],
        'demand_mw': [45 + 15 * np.sin((i-10) * np.pi / 12) for i in range(24)]
    })

# --- Callbacks ---

@app.callback(
    [Output("texas-map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    Input("zip-btn", "n_clicks"),
    State("zip-input", "value"),
    prevent_initial_call=True
)
def update_map(n, zip_code):
    if not zip_code: raise exceptions.PreventUpdate
    try:
        loc = geolocator.geocode(f"{zip_code}, Texas", timeout=10)
        if loc:
            return {"center": [loc.latitude, loc.longitude], "zoom": 10, "transition": "flyTo"}, \
                   [dl.Marker(position=[loc.latitude, loc.longitude])], \
                   {'lat': loc.latitude, 'lon': loc.longitude}
    except: pass
    return {"center": [31.0, -99.0], "zoom": 6}, [], {'lat': 31.0, 'lon': -99.0}

@app.callback(
    Output("weather-radar-layer", "children"),
    Input("weather-toggle", "value")
)
def toggle_radar(checked):
    if checked:
        # RainViewer tiles often require the "nowcast" timestamp. 
        # For simplicity, we use the "latest" endpoint which is more reliable.
        return [dl.TileLayer(
            url="https://tilecache.rainviewer.com/v2/radar/nowcast_5m/256/{z}/{x}/{y}/2/1_1.png",
            opacity=0.5,
            id="radar-tiles"
        )]
    return []

@app.callback(
    [Output("live-supply-demand", "figure"), Output("market-candlestick", "figure")],
    Input("coords-store", "data")
)
def update_main_graphs(coords):
    df = get_mock_data()
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&hourly=shortwave_radiation&timezone=auto"
        r = requests.get(url, timeout=5).json()
        if 'hourly' in r:
            df = pd.DataFrame({
                'time': pd.to_datetime(r['hourly']['time'][:24]),
                'supply_mw': np.array(r['hourly']['shortwave_radiation'][:24]) * 0.12,
                'demand_mw': [45 + 15 * np.sin((i-10) * np.pi / 12) for i in range(24)]
            })
    except: pass

    fig_sd = go.Figure()
    fig_sd.add_trace(go.Scatter(x=df['time'], y=df['supply_mw'], name="Supply (MW)", fill='tozeroy', line=dict(color='#FFD700')))
    fig_sd.add_trace(go.Scatter(x=df['time'], y=df['demand_mw'], name="Demand (MW)", line=dict(color='#00FFCC', dash='dash')))
    fig_sd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20,r=20,t=30,b=20))

    fig_ohlc = go.Figure(data=[go.Candlestick(x=df['time'], open=df['supply_mw']*0.95, high=df['supply_mw']
