import os
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, exceptions, ctx
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from scipy.stats import norm, linregress
from shapely.geometry import shape, Point
import random

# Initialize app with CYBORG foundation and Custom Logo Colors
# LOGO COLORS: Yellow (#FFD700), Blue (#00CCFF), Green (#00FF66)
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_leaders_v5_{random.randint(1000, 9999)}")

# --- Technical Data Assets ---
ENERGY_STOCKS = {
    "TAN": {"name": "Invesco Solar ETF", "loc": "US Index / Mutual Fund"},
    "ENPH": {"name": "Enphase Energy", "loc": "US Solar Tech"},
    "VLO": {"name": "Valero Energy", "loc": "Texas Energy Giant"},
    "FSLR": {"name": "First Solar", "loc": "US Manufacturer"},
    "WHD": {"name": "Cactus Inc.", "loc": "Texas Equipment"}
}

ercot_zones = {"type": "FeatureCollection", "features": [
    {"type":"Feature","properties":{"zone":"North"}, "geometry":{"type":"Polygon","coordinates":[[[-103,36],[-94,36],[-94,33],[-103,33],[-103,36]]]}},
    {"type":"Feature","properties":{"zone":"South"}, "geometry":{"type":"Polygon","coordinates":[[[-102,29],[-96,29],[-96,26],[-102,26],[-102,29]]]}},
    {"type":"Feature","properties":{"zone":"West"}, "geometry":{"type":"Polygon","coordinates":[[[-106,33],[-102,33],[-102,29],[-106,29],[-106,33]]]}},
    {"type":"Feature","properties":{"zone":"Houston"}, "geometry":{"type":"Polygon","coordinates":[[[-96,31],[-94,31],[-94,29],[-96,29],[-96,31]]]}}
]}

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.03)", "backdropFilter": "blur(12px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

# --- Layout ---
app.layout = dbc.Container(fluid=True, className="p-4 bg-black text-white", children=[
    # Header Section with Logo and Mission
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0 display-4"),
                html.H5("Live Solar Insights for Texas Energy Leaders", className="text-info opacity-75"),
            ], className="text-center mb-4")
        ], width=12)
    ]),

    dbc.Row([
        # Left Side: Map and Sidebar
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "350px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.GeoJSON(data=ercot_zones, id="ercot-layer", style={"fillColor": "#00CCFF", "color": "white", "weight": 1, "fillOpacity": 0.1}),
                    dl.LayerGroup(id="marker-layer")
                ]),
                html.Div(id="ercot-notif", className="mt-2 text-warning fw-bold text-center")
            ], style=GLASS_STYLE),

            # ENVIRONMENTAL SIDEBAR
            html.Div([
                html.H6("ENVIRONMENTAL SIDEBAR", className="text-info fw-bold mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Carbon Intensity", className="text-muted small mb-0"),
                        html.H5("0.28 kg/kWh", className="text-success"),
                        html.P("Grid Frequency", className="text-muted small mb-0"),
                        html.H5("59.749 Hz", className="text-warning")
                    ], width=6),
                    dbc.Col([
                        html.Small("CI = Base * (1 - S/D)", className="text-muted d-block mt-2"),
                        html.Small("f = 60 + alpha(S-D)", className="text-muted d-block mt-3")
                    ], width=6)
                ]),
                html.Div(id="forecast-mini-cards", className="mt-3")
            ], style=GLASS_STYLE)
        ], lg=4),

        # Right Side: Supply/Demand FTC
        dbc.Col([
            html.Div([
                dbc.InputGroup([
                    dbc.Input(id="addr-input", placeholder="Texas Address...", type="text", className="bg-dark text-white"),
                    dbc.Button("ANALYZE", id="addr-btn", color="warning"),
                ], className="mb-3"),
                dcc.Graph(id="supply-demand-chart", style={"height": "550px"})
            ], style=GLASS_STYLE)
        ], lg=8)
    ]),

    # Market Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("FINANCIAL RISK & MARKET OVERLAY", className="text-info fw-bold mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Option Delta", className="text-muted small mb-0"),
                        html.H4("0.336", className="text-primary"),
                        html.P("Trend Confidence", className="text-muted small mb-0"),
                        html.H4("79.53%", className="text-info")
                    ], width=3),
                    dbc.Col([
                        html.Label("Compare Solar Indexes & Stocks", className="text-muted small"),
                        dcc.Checklist(
                            id="stock-selector",
                            options=[{"label": f" {k} ({v['loc']})", "value": k} for k, v in ENERGY_STOCKS.items()],
                            value=["TAN"], className="text-white small", labelStyle={'display': 'block'}
                        )
                    ], width=5),
                    dbc.Col([
                        html.Label("Technical Controls", className="text-muted small"),
                        dbc.RadioItems(id="horizon", options=[{"label": i, "value": i} for i in ["1W", "1M", "1Y"]], value="1M", className="text-warning"),
                        dbc.Checklist(options=[{"label": "Best Fit Line", "value": "fit"}], value=[], id="toggle-fit", switch=True, className="text-success mt-2")
                    ], width=4)
                ]),
                dcc.Graph(id="market-comparison-graph", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # Footer
    html.Footer([
        html.Hr(className="border-secondary"),
        html.P("Specusol is an information service. Any insights are not intended to be investing advice and are for educational purposes only.", className="text-muted small text-center"),
        html.P("© 2026 Specusol Intelligence | Texas Energy Leaders Edition", className="text-center text-muted small")
    ], className="pb-4")
])

# --- Logic: Technical Engine ---

def get_daylight_curve(t_range):
    # Daylight Hours: 7:30 (7.5) to 19:00 (19)
    mu = 13.25 # Solar Noon
    std = 2.5
    bell = 1000 * np.exp(-0.5 * ((t_range - mu) / std) ** 2)
    return bell

@app.callback(
    [Output("supply-demand-chart", "figure"), Output("ercot-notif", "children")],
    Input("coords-store", "data")
)
def update_ftc_chart(coords):
    t = np.linspace(0, 24, 100)
    daylight = get_daylight_curve(t)
    
    # Residential vs Commercial Separated
    res_supply = daylight * 0.4
    comm_supply = daylight * 0.8
    res_demand = 200 + 100 * np.sin((t-16)/12*np.pi)
    comm_demand = 500 + 150 * np.sin((t-10)/12*np.pi)
    
    total_supply = res_supply + comm_supply
    total_demand = res_demand + comm_demand
    
    # Equilibrium Calculation (Finding where S approx D)
    idx = np.argwhere(np.diff(np.sign(total_supply - total_demand))).flatten()
    eq_text = ""
    eq_pt = None
    if len(idx) > 0:
        eq_pt = t[idx[0]]
        eq_val = total_supply[idx[0]]
        eq_text = f"Equilibrium: {round(eq_val, 1)}kW @ {int(eq_pt)}:00"

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=res_supply, name="Res. Solar Supply", line=dict(color="#FFD700")))
    fig.add_trace(go.Scatter(x=t, y=comm_supply, name="Comm. Solar Supply", line=dict(color="#FF8C00")))
    fig.add_trace(go.Scatter(x=t, y=res_demand, name="Res. Grid Demand", line=dict(color="#00CCFF", dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=comm_demand, name="Comm. Grid Demand", line=dict(color="#0066FF", dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=daylight, name="Daylight Intensity (7:30-7)", line=dict(color="rgba(255,255,255,0.2)"), fill='tozeroy'))

    if eq_pt:
        fig.add_annotation(x=eq_pt, y=total_supply[idx[0]], text=f"EQ POINT: {round(total_supply[idx[0]],0)}kW", showarrow=True, arrowhead=1, bgcolor="green")

    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=30,b=0), title="FTC: Residential vs Commercial Grid Model")
    
    # ERCOT Check
    notif = "⚠️ Outside Primary ERCOT Reliability Zone"
    p = Point(coords['lon'], coords['lat'])
    for feat in ercot_zones['features']:
        if shape(feat['geometry']).contains(p):
            notif = f"✅ Verified ERCOT {feat['properties']['zone']} Zone"
            break
            
    return fig, notif

@app.callback(
    Output("market-comparison-graph", "figure"),
    [Input("stock-selector", "value"), Input("horizon", "value"), Input("toggle-fit", "value")]
)
def update_market_overlay(stocks, horizon, fit):
    fig = go.Figure()
    points = {"1W": 168, "1M": 30, "1Y": 52}[horizon]
    
    for symbol in stocks:
        base = {"TAN": 50, "ENPH": 120, "VLO": 140, "FSLR": 160, "WHD": 50}[symbol]
        y = base * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, points)))
        x = np.arange(points)
        
        fig.add_trace(go.Scatter(x=x, y=y, name=symbol, mode='lines'))
        
        if "fit" in fit and symbol == stocks[0]:
            slope, intercept, r, p, std = linregress(x, y)
            eq_label = f"y = {slope:.2f}x + {intercept:.2f}"
            fig.add_trace(go.Scatter(x=x, y=slope*x + intercept, name=f"Fit: {symbol}", line=dict(dash='dot', color="green")))
            fig.add_annotation(x=points//2, y=slope*(points//2)+intercept, text=eq_label, showarrow=False, font=dict(color="green"))

    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', title="Comparative Energy Equity Analysis")
    return fig

@app.callback(
    [Output("map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    [Input("addr-btn", "n_clicks"), Input("map", "clickData")],
    State("addr-input", "value"), prevent_initial_call=True
)
def handle_geo(n, click, addr):
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
