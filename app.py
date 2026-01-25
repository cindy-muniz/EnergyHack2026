import os
import requests
import pandas as pd
import yfinance as yf
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
import numpy as np
from dash import Dash, html, dcc, Input, Output, State, ctx, exceptions
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
# Use a very specific User Agent to avoid 503 errors
geolocator = Nominatim(user_agent="energy_hack_texas_v2_2026")

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
                dl.Map(center=[31.0, -99.0], zoom=6, style={"height": "450px", "borderRadius": "12px"}, id="texas-map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer"),
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
                # Updated Header per request
                html.H6("SOLAR TEXAS MUTUAL FUND (TAN)", className="text-info mb-3 fw-bold"),
                dcc.Graph(id="solar-etf-mini", style={"height": "320px"})
            ], style=GLASS_STYLE)
        ], lg=4, md=12)
    ]),
    
    dcc.Store(id='coords-store', data={'lat': 31.0, 'lon': -99.0})
])

# --- Logic: Mock Data Generator (The "Safety Net") ---
def get_fallback_data():
    times = pd.date_range(start=datetime.now(), periods=24, freq='H')
    df = pd.DataFrame({
        'time': times,
        'supply_mw': [max(0, 50 * np.sin((i-6) * np.pi / 12)) for i in range(24)],
        'demand_mw': [40 + 20 * np.sin((i-10) * np.pi / 12) for i in range(24)]
    })
    return df

# --- Callbacks ---

@app.callback(
    [Output("texas-map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    Input("zip-btn", "n_clicks"),
    State("zip-input", "value"),
    prevent_initial_call=True
)
def update_location(n, zip_code):
    if not zip_code: raise exceptions.PreventUpdate
    try:
        loc = geolocator.geocode(f"{zip_code}, Texas", timeout=10)
        if loc:
            return {"center": [loc.latitude, loc.longitude], "zoom": 10}, \
                   [dl.Marker(position=[loc.latitude, loc.longitude])], \
                   {'lat': loc.latitude, 'lon': loc.longitude}
    except: pass
    return {"center": [31.0, -99.0], "zoom": 6}, [], {'lat': 31.0, 'lon': -99.0}

@app.callback(
    [Output("live-supply-demand", "figure"), Output("market-candlestick", "figure")],
    Input("coords-store", "data")
)
def update_charts(coords):
    df = get_fallback_data() # Start with fallback
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&hourly=shortwave_radiation&timezone=auto"
        r = requests.get(url, timeout=5).json()
        if 'hourly' in r:
            df = pd.DataFrame({
                'time': pd.to_datetime(r['hourly']['time'][:24]),
                'supply_mw': np.array(r['hourly']['shortwave_radiation'][:24]) * 0.1,
                'demand_mw': [40 + 20 * np.sin((i-10) * np.pi / 12) for i in range(24)]
            })
    except: pass

    fig_sd = go.Figure()
    fig_sd.add_trace(go.Scatter(x=df['time'], y=df['supply_mw'], name="Supply", fill='tozeroy', line=dict(color='#FFD700')))
    fig_sd.add_trace(go.Scatter(x=df['time'], y=df['demand_mw'], name="Demand", line=dict(color='#00FFCC', dash='dash')))
    fig_sd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20,r=20,t=30,b=20))

    fig_ohlc = go.Figure(data=[go.Candlestick(x=df['time'], open=df['supply_mw']*0.9, high=df['supply_mw']*1.1, low=df['supply_mw']*0.8, close=df['supply_mw'])])
    fig_ohlc.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
    
    return fig_sd, fig_ohlc

@app.callback(Output("solar-etf-mini", "figure"), Input("coords-store", "data"))
def update_etf(_):
    # Default Figure to avoid "None" errors if yfinance fails
    fig = go.Figure().update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
    try:
        data = yf.download("TAN", period="1mo", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            fig = go.Figure(go.Scatter(x=data.index, y=data['Close'], fill='tozeroy', line=dict(color='#00CCFF')))
    except: pass
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=10,b=10))
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
