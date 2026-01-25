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

# Initialize app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_leaders_final_{random.randint(1000, 9999)}")

# ERCOT GeoJSON Data
ercot_zones = {"type": "FeatureCollection", "features": [
    {"type":"Feature","properties":{"zone":"North"}, "geometry":{"type":"Polygon","coordinates":[[[-103,36],[-94,36],[-94,33],[-103,33],[-103,36]]]}},
    {"type":"Feature","properties":{"zone":"South"}, "geometry":{"type":"Polygon","coordinates":[[[-102,29],[-96,29],[-96,26],[-102,26],[-102,29]]]}},
    {"type":"Feature","properties":{"zone":"West"}, "geometry":{"type":"Polygon","coordinates":[[[-106,33],[-102,33],[-102,29],[-106,29],[-106,33]]]}},
    {"type":"Feature","properties":{"zone":"Houston"}, "geometry":{"type":"Polygon","coordinates":[[[-96,31],[-94,31],[-94,29],[-96,29],[-96,31]]]}}
]}

ENERGY_STOCKS = {
    "TAN": {"name": "Invesco Solar ETF", "loc": "US-Mutual"},
    "ENPH": {"name": "Enphase Energy", "loc": "US-Solar"},
    "VLO": {"name": "Valero Energy", "loc": "Texas-Oil"},
    "FSLR": {"name": "First Solar", "loc": "US-Solar"},
    "WHD": {"name": "Cactus Inc.", "loc": "Texas-Equip"}
}

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.03)", "backdropFilter": "blur(12px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

app.layout = dbc.Container(fluid=True, className="p-4 bg-black text-white", children=[
    # Header Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0 display-4"),
                html.H5("Live Solar Insights for Texas Energy Leaders", className="text-info opacity-75"),
            ], className="text-center mb-4")
        ], width=12)
    ]),

    dbc.Row([
        # Sidebar: Map and Weather/Environmental
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "300px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.GeoJSON(data=ercot_zones, id="ercot-layer", style={"fillColor": "#00CCFF", "color": "white", "weight": 1, "fillOpacity": 0.1}),
                    dl.LayerGroup(id="marker-layer")
                ]),
                html.Div(id="ercot-notif", className="mt-2 text-warning fw-bold text-center small")
            ], style=GLASS_STYLE),

            html.Div([
                html.H6("ENVIRONMENTAL SIDEBAR", className="text-info fw-bold mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Carbon Intensity", className="text-muted small mb-0"),
                        html.H5("0.28 kg/kWh", className="text-success"),
                        html.P("Grid Frequency", className="text-muted small mb-0"),
                        html.H5("59.749 Hz", className="text-warning")
                    ], width=7),
                    dbc.Col([
                        html.Small("CI = Base*(1-S/D)", className="text-muted"),
                        html.Small("f = 60+α(S-D)", className="text-muted mt-3 d-block")
                    ], width=5)
                ]),
                html.Hr(className="border-secondary"),
                html.Label("7-HOUR WEATHER & IRRADIANCE", className="text-info small fw-bold"),
                html.Div(id="forecast-sidebar-content") # RESTORED FEATURE
            ], style=GLASS_STYLE)
        ], lg=4),

        # Center Column: FTC Supply/Demand
        dbc.Col([
            html.Div([
                dbc.InputGroup([
                    dbc.Input(id="addr-input", placeholder="Texas Address...", type="text", className="bg-dark text-white"),
                    dbc.Button("ANALYZE", id="addr-btn", color="warning"),
                ], className="mb-3"),
                dcc.Graph(id="supply-demand-chart", style={"height": "500px"}),
                html.Div(id="equilibrium-label", className="text-success text-center fw-bold mt-2")
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
                        html.H5("0.336", className="text-primary"),
                        html.P("Market Confidence", className="text-muted small mb-0"),
                        html.H5("79.53%", className="text-info")
                    ], width=3),
                    dbc.Col([
                        html.Label("Compare Energy Overlays", className="text-muted small"),
                        dcc.Checklist(
                            id="stock-selector",
                            options=[{"label": f" {k} ({v['loc']})", "value": k} for k, v in ENERGY_STOCKS.items()],
                            value=["TAN"], className="text-white small", labelStyle={'display': 'block'}
                        )
                    ], width=5),
                    dbc.Col([
                        dbc.RadioItems(id="horizon", options=[{"label": i, "value": i} for i in ["1W", "1M", "1Y"]], value="1M", className="text-warning mb-2"),
                        dbc.Checklist(options=[{"label": "Best Fit Trend", "value": "fit"}], value=[], id="toggle-fit", switch=True, className="text-success")
                    ], width=4)
                ]),
                dcc.Graph(id="market-comparison-graph", style={"height": "400px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    html.Footer([
        html.P("Specusol is an information service. Any insights are not intended to be investing advice and are for educational purposes only. © 2026", 
               className="text-muted small text-center mt-4")
    ])
])

# --- Mathematical Engines ---

def get_daylight_model(t):
    return 1000 * np.exp(-0.5 * ((t - 13.25) / 2.5) ** 2)

@app.callback(
    [Output("supply-demand-chart", "figure"), Output("ercot-notif", "children"), Output("forecast-sidebar-content", "children")],
    Input("coords-store", "data")
)
def update_technical_analytics(coords):
    t = np.linspace(0, 24, 100)
    daylight = get_daylight_model(t)
    
    # Grid Model
    res_supply, comm_supply = daylight * 0.4, daylight * 0.8
    res_demand = 250 + 120 * np.sin((t-16)/12*np.pi)
    comm_demand = 550 + 180 * np.sin((t-10)/12*np.pi)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=res_supply, name="Res. Supply", line=dict(color="#FFD700")))
    fig.add_trace(go.Scatter(x=t, y=comm_supply, name="Comm. Supply", line=dict(color="#FF8C00")))
    fig.add_trace(go.Scatter(x=t, y=res_demand, name="Res. Demand", line=dict(color="#00CCFF", dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=comm_demand, name="Comm. Demand", line=dict(color="#0066FF", dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=daylight, name="Daylight Curve", fill='tozeroy', line=dict(color="rgba(255,255,255,0.1)")))
    
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))

    # ERCOT Logic
    notif = "⚠️ Outside ERCOT Zone"
    p = Point(coords['lon'], coords['lat'])
    for feat in ercot_zones['features']:
        if shape(feat['geometry']).contains(p):
            notif = f"✅ Verified ERCOT {feat['properties']['zone']} Zone"
            break

    # RESTORED Weather Forecast content
    forecast_rows = []
    for i in range(7):
        hr = (datetime.now().hour + i) % 24
        val = get_daylight_model(hr)
        temp = round(22 + 5 * np.sin((hr-14)/12*np.pi), 1)
        forecast_rows.append(html.Div([
            html.Span(f"{hr}:00", className="text-muted small"),
            html.Span(f"  {temp}°C", className="text-warning fw-bold px-2"),
            html.Span(f"{int(val)} W/m²", className="text-info small")
        ], className="border-bottom border-secondary py-1"))

    return fig, notif, forecast_rows

@app.callback(
    Output("market-comparison-graph", "figure"),
    [Input("stock-selector", "value"), Input("horizon", "value"), Input("toggle-fit", "value")]
)
def update_market_comparison(stocks, horizon, fit):
    fig = go.Figure()
    points = {"1W": 100, "1M": 30, "1Y": 52}[horizon]
    for symbol in stocks:
        base = {"TAN":55, "ENPH":115, "VLO":135, "FSLR":155, "WHD":45}[symbol]
        y = base * np.exp(np.cumsum(np.random.normal(0.0006, 0.018, points)))
        x = np.arange(points)
        fig.add_trace(go.Scatter(x=x, y=y, name=symbol))
        if "fit" in fit:
            slope, intercept, r, p, std = linregress(x, y)
            fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, name=f"Fit {symbol}", line=dict(dash='dot')))
            fig.add_annotation(x=points-5, y=y[-1], text=f"y={slope:.2f}x+{intercept:.1f}", showarrow=False, font=dict(color="green"))
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
    return fig

@app.callback(
    [Output("map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    [Input("addr-btn", "n_clicks"), Input("map", "clickData")],
    State("addr-input", "value"), prevent_initial_call=True
)
def handle_location(n, click, addr):
    if ctx.triggered_id == "addr-btn" and addr:
        try:
            loc = geolocator.geocode(addr, timeout=10)
            if loc: return {"center":[loc.latitude, loc.longitude], "zoom":12}, [dl.Marker(position=[loc.latitude, loc.longitude])], {'lat':loc.latitude, 'lon':loc.longitude}
        except: pass
    elif click:
        lat, lon = click["latlng"]["lat"], click["latlng"]["lng"]
        return {"center":[lat, lon], "zoom":10}, [dl.Marker(position=[lat, lon])], {'lat':lat, 'lon':lon}
    return exceptions.PreventUpdate

if __name__ == "__main__":
    app.run_server(debug=True)
