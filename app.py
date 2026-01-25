import os
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, State, exceptions, ctx
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from scipy.stats import norm, linregress
import random

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_full_twin_{random.randint(1000, 9999)}")

# --- Data Assets ---
ENERGY_STOCKS = {
    "TAN": {"name": "Invesco Solar ETF", "loc": "US-Mutual"},
    "ENPH": {"name": "Enphase Energy", "loc": "US-Solar"},
    "VLO": {"name": "Valero Energy", "loc": "Texas-Oil"},
    "FSLR": {"name": "First Solar", "loc": "US-Solar"},
    "WHD": {"name": "Cactus Inc.", "loc": "Texas-Equip"}
}

ercot_zones = {"type": "FeatureCollection", "features": [
    {"type":"Feature","properties":{"zone":"North"}, "geometry":{"type":"Polygon","coordinates":[[[-103,36],[-94,36],[-94,33],[-103,33],[-103,36]]]}},
    {"type":"Feature","properties":{"zone":"South"}, "geometry":{"type":"Polygon","coordinates":[[[-102,29],[-96,29],[-96,26],[-102,26],[-102,29]]]}}
]}

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.05)", "backdropFilter": "blur(10px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

# --- Layout ---
app.layout = dbc.Container(fluid=True, className="p-4", children=[
    dbc.Row([
        dbc.Col([
            html.H1(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0"),
            html.P("Environmental & Financial Risk Intelligence", className="text-muted small")
        ], width=7),
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="addr-input", placeholder="Enter Texas Address...", type="text", className="bg-dark text-white"),
                dbc.Button("ANALYZE", id="addr-btn", color="warning"),
            ])
        ], width=5, className="align-self-center")
    ], className="mb-4"),

    dbc.Row([
        # Main Column: Map and Technical Chart
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "400px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.GeoJSON(data=ercot_zones, style={"fillColor": "#1f77b4", "color": "white", "weight": 1, "fillOpacity": 0.15}),
                    dl.LayerGroup(id="marker-layer")
                ])
            ], style=GLASS_STYLE),
            html.Div([dcc.Graph(id="supply-demand-chart", style={"height": "400px"})], style=GLASS_STYLE)
        ], lg=8),

        # Sidebar: Environmental & Grid Risk
        dbc.Col([
            html.Div([
                html.H6("ENVIRONMENTAL SIDEBAR", className="text-info fw-bold mb-3"),
                html.Div([
                    html.P("Carbon Intensity", className="text-muted small mb-0"),
                    html.H4(id="carbon-intensity", className="text-success"),
                    html.P("Grid Frequency", className="text-muted small mb-0"),
                    html.H4(id="grid-freq", className="text-warning"),
                    html.Hr(className="border-secondary"),
                    html.Div(id="forecast-mini-cards")
                ])
            ], style=GLASS_STYLE),
            
            html.Div([
                html.H6("FINANCIAL RISK (GREEKS)", className="text-info fw-bold mb-3"),
                html.P("Option Delta (Hedge Ratio)", className="text-muted small mb-0"),
                html.H4(id="option-delta", className="text-primary"),
                html.P("Market Trend Confidence", className="text-muted small mb-0"),
                html.H4(id="trend-confidence", className="text-info")
            ], style=GLASS_STYLE)
        ], lg=4)
    ]),

    # Lower Row: Multi-Stock Analytics
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(id="primary-stock", 
                                     options=[{"label": f"{k} ({v['loc']})", "value": k} for k,v in ENERGY_STOCKS.items()], 
                                     value="TAN", className="text-dark")
                    ], width=4),
                    dbc.Col([
                        dbc.RadioItems(id="horizon", options=[{"label": i, "value": i} for i in ["1W", "1M", "1Y"]], 
                                       value="1M", inline=True, className="text-warning")
                    ], width=4),
                    dbc.Col([
                        dbc.Checklist(options=[{"label": "Best Fit Line", "value": "fit"}], value=[], id="toggle-fit", switch=True, className="text-success")
                    ], width=4)
                ], className="mb-3"),
                dcc.Graph(id="market-comparison-graph", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),
    dcc.Store(id='coords-store', data={'lat': 30.26, 'lon': -97.74})
])

# --- Mathematical Engine ---

def black_scholes_delta(S, K, T, r, sigma):
    # Theoretical Hedge Ratio
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1)

def get_simulated_market_data(symbol, horizon):
    # Replaces unstable APIs with a stochastic geometric brownian motion model
    points = {"1W": 168, "1M": 30, "1Y": 52}[horizon]
    base_price = {"TAN": 50, "ENPH": 120, "VLO": 140, "FSLR": 160, "WHD": 50}[symbol]
    
    returns = np.random.normal(0.001, 0.02, points)
    price_path = base_price * np.exp(np.cumsum(returns))
    times = [datetime.now() - timedelta(hours=i if horizon=="1W" else i*24) for i in range(points)][::-1]
    
    return pd.DataFrame({'time': times, 'price': price_path})

# --- Callbacks ---

@app.callback(
    [Output("supply-demand-chart", "figure"), 
     Output("carbon-intensity", "children"),
     Output("grid-freq", "children")],
    Input("coords-store", "data")
)
def update_environmental_twin(coords):
    # Simulated Grid Model
    t = np.linspace(0, 24, 24)
    supply = 500 * np.maximum(0, np.sin((t-6)/12*np.pi))
    demand = 400 + 100 * np.sin((t-16)/12*np.pi)
    
    # 1. Carbon Calculation: CO2 avoided per kWh
    ci_val = 0.45 * (1 - (np.mean(supply)/np.mean(demand)))
    ci_text = f"{max(0, ci_val):.2f} kg/kWh"
    
    # 2. Grid Frequency Simulation: Deviation from 60Hz
    freq_dev = (np.mean(supply) - np.mean(demand)) / 1000
    freq_text = f"{60.0 + freq_dev:.3f} Hz"
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=supply, name="Solar Supply", fill='tozeroy', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=t, y=demand, name="Grid Demand", line=dict(color='red', dash='dash')))
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=30,b=0))
    
    return fig, ci_text, freq_text

@app.callback(
    [Output("market-comparison-graph", "figure"),
     Output("option-delta", "children"),
     Output("trend-confidence", "children")],
    [Input("primary-stock", "value"), Input("horizon", "value"), Input("toggle-fit", "value")]
)
def update_financial_twin(symbol, horizon, toggle):
    df = get_simulated_market_data(symbol, horizon)
    S = df['price'].iloc[-1] # Current Price
    
    # Calculate Risk Analytics
    delta = black_scholes_delta(S, S*1.05, 0.1, 0.04, 0.3)
    
    # Best Fit Line
    x = np.arange(len(df))
    slope, intercept, r_val, p_val, std_err = linregress(x, df['price'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'], y=df['price'], name=symbol, line=dict(color='#00CCFF', width=3)))
    
    if "fit" in toggle:
        fig.add_trace(go.Scatter(x=df['time'], y=slope*x + intercept, name="Trend", line=dict(color='green', dash='dot')))
        
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    
    return fig, f"{delta:.3f}", f"{r_val**2:.2%}"

@app.callback(
    [Output("map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    [Input("addr-btn", "n_clicks"), Input("map", "clickData")],
    State("addr-input", "value"), prevent_initial_call=True
)
def sync_location(n, click, addr):
    # (Same robust geocoding logic as before)
    if ctx.triggered_id == "addr-btn" and addr:
        try:
            loc = geolocator.geocode(addr, timeout=10)
            if loc: return {"center":[loc.latitude, loc.longitude], "zoom":12}, [dl.Marker(position=[loc.latitude, loc.longitude])], {'lat':loc.latitude, 'lon':loc.longitude}
        except: pass
    elif click:
        lat, lon = click["latlng"]["lat"], click["latlng"]["lng"]
        return {"center":[lat, lon], "zoom":10}, [dl.Marker(position=[lat, lon])], {'lat':lat, 'lon':lon}
    raise exceptions.PreventUpdate

if __name__ == "__main__":
    app.run_server(debug=True)
