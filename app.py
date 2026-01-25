import os
import requests
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, exceptions, ctx
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import time
import random

# Initialize app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server

# Finnhub Config
FINNHUB_KEY = "KEY"

# Geolocation setup
ua_string = f"specusol_ftc_final_{random.randint(1000, 9999)}"
geolocator = Nominatim(user_agent=ua_string)

# ERCOT GeoJSON Data
ercot_zones = {
    "type": "FeatureCollection",
    "features": [
        {"type":"Feature","properties":{"zone":"North"}, "geometry":{"type":"Polygon","coordinates":[[[-103,36],[-94,36],[-94,33],[-103,33],[-103,36]]]}},
        {"type":"Feature","properties":{"zone":"South"}, "geometry":{"type":"Polygon","coordinates":[[[-102,29],[-96,29],[-96,26],[-102,26],[-102,29]]]}},
        {"type":"Feature","properties":{"zone":"West"}, "geometry":{"type":"Polygon","coordinates":[[[-106,33],[-102,33],[-102,29],[-106,29],[-106,33]]]}},
        {"type":"Feature","properties":{"zone":"Houston"}, "geometry":{"type":"Polygon","coordinates":[[[-96,31],[-94,31],[-94,29],[-96,29],[-96,31]]]}},
        {"type":"Feature","properties":{"zone":"Coastal"}, "geometry":{"type":"Polygon","coordinates":[[[-98,29],[-94,29],[-94,26],[-98,26],[-98,29]]]}}
    ]
}

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.05)", "backdropFilter": "blur(10px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

app.layout = dbc.Container(fluid=True, className="p-4", children=[
    dbc.Row([
        dbc.Col([
            html.H1(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0"),
            html.P("Texas Solar Technical Model (FTC) & Finnhub Market Data", className="text-muted small")
        ], width=7),
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="addr-input", placeholder="Enter Address...", type="text", className="bg-dark text-white"),
                dbc.Button("ANALYZE", id="addr-btn", color="warning", className="fw-bold"),
            ])
        ], width=5, className="align-self-center")
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "450px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.GeoJSON(data=ercot_zones, style={"fillColor": "#1f77b4", "color": "white", "weight": 1, "fillOpacity": 0.15}),
                    dl.LayerGroup(id="marker-layer")
                ])
            ], style=GLASS_STYLE)
        ], lg=5, md=12),
        dbc.Col([
            html.Div([
                dcc.Graph(id="supply-demand-chart", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], lg=7, md=12)
    ]),

    # Forecast Row
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("7-HOUR LOCALIZED FORECAST & SOLAR IRRADIANCE", className="text-info mb-3 fw-bold"),
                dbc.Row(id="forecast-row", className="text-center g-2"),
                html.Div(id="efficiency-text", className="text-success fw-bold mt-3 text-center", style={"fontSize": "1.1rem"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # Finnhub Candlestick Row
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("SOLAR TEXAS MUTUAL FUND (TAN) - Finnhub 5D Candles", className="text-info mb-3 fw-bold"),
                dcc.Graph(id="solar-etf", style={"height": "350px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),
    dcc.Store(id='coords-store', data={'lat': 30.26, 'lon': -97.74})
])

# --- Logic: Model Data ---

def get_internal_model_data(lat, lon):
    now = datetime.now()
    times = [now + timedelta(hours=i) for i in range(168)]
    hours = np.array([t.hour for t in times])
    lat_factor = np.cos(np.radians(lat))
    
    ghi = np.maximum(0, 1000 * np.sin((hours - 6) / 12 * np.pi) * lat_factor)
    temp_sim = 20 + 10 * np.sin((hours - 14) / 12 * np.pi) - (lat - 30)
    
    eff_base = 0.225
    thermal_derating = np.where(temp_sim > 25, (temp_sim - 25) * 0.003, 0)
    actual_eff = eff_base - thermal_derating
    
    df = pd.DataFrame({
        'time': times, 'ghi': ghi, 'temp': temp_sim, 'eff': actual_eff,
        'res_supply': ghi * 2.5 * actual_eff, 'comm_supply': ghi * 8.0 * actual_eff,
        'res_demand': 300 + 150 * np.sin((hours - 17) / 12 * np.pi),
        'comm_demand': 700 + 300 * np.sin((hours - 11) / 12 * np.pi)
    })
    return df

# --- Callbacks ---

@app.callback(
    [Output("map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    [Input("addr-btn", "n_clicks"), Input("map", "clickData")],
    State("addr-input", "value"), prevent_initial_call=True
)
def update_location(n, clickData, address):
    t_id = ctx.triggered_id
    if t_id == "addr-btn" and address:
        try:
            loc = geolocator.geocode(address, timeout=10)
            if loc:
                return {"center": [loc.latitude, loc.longitude], "zoom": 12}, [dl.Marker(position=[loc.latitude, loc.longitude])], {'lat': loc.latitude, 'lon': loc.longitude}
        except: pass
    elif t_id == "map" and clickData:
        lat, lon = clickData["latlng"]["lat"], clickData["latlng"]["lng"]
        return {"center": [lat, lon], "zoom": 10}, [dl.Marker(position=[lat, lon])], {'lat': lat, 'lon': lon}
    raise exceptions.PreventUpdate

@app.callback(
    [Output("supply-demand-chart", "figure"), Output("forecast-row", "children"), Output("efficiency-text", "children")],
    Input("coords-store", "data")
)
def update_technical_data(coords):
    df = get_internal_model_data(coords['lat'], coords['lon'])
    
    fig_sd = go.Figure()
    fig_sd.add_trace(go.Scatter(x=df['time'][:48], y=df['res_supply'][:48], name="Res. Supply", line=dict(color="orange", width=2)))
    fig_sd.add_trace(go.Scatter(x=df['time'][:48], y=df['res_demand'][:48], name="Res. Demand", line=dict(color="red", dash="dash")))
    fig_sd.add_trace(go.Scatter(x=df['time'][:48], y=df['comm_supply'][:48], name="Comm. Supply", line=dict(color="#00CCFF", width=2)))
    fig_sd.add_trace(go.Scatter(x=df['time'][:48], y=df['comm_demand'][:48], name="Comm. Demand", line=dict(color="blue", dash="dash")))
    
    fig_sd.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", y=1.1))

    forecast_cards = []
    for i in range(7):
        row = df.iloc[i]
        icon = "fa-sun" if row['ghi'] > 10 else "fa-moon"
        forecast_cards.append(dbc.Col(html.Div([
            html.Small(row['time'].strftime("%I %p"), className="text-muted"),
            html.H5(f"{round(row['temp'], 1)}°C", className="text-warning mt-1"),
            html.Small(f"{int(row['ghi'])} W/m²", className="text-info d-block fw-bold"),
            html.I(className=f"fas {icon} text-info")
        ], className="p-2 border border-secondary rounded"), xs=4, md=True))
    
    current_eff = df.iloc[0]['eff'] * 100
    eff_msg = f"Standard Panel Conversion Efficiency: {current_eff:.2f}% (Real-Time Thermal Adjustment)"
    
    return fig_sd, forecast_cards, eff_msg

@app.callback(Output("solar-etf", "figure"), Input("coords-store", "data"))
def update_etf(_):
    try:
        # Finnhub API requires UNIX timestamps
        end = int(time.time())
        start = end - (5 * 24 * 60 * 60) # 5 days ago
        
        url = f"https://finnhub.io/api/v1/stock/candle?symbol=TAN&resolution=60&from={start}&to={end}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10).json()
        
        if r['s'] == 'ok':
            fig = go.Figure(go.Candlestick(
                x=[datetime.fromtimestamp(t) for t in r['t']],
                open=r['o'], high=r['h'], low=r['l'], close=r['c']
            ))
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=10,b=10))
            return fig
    except Exception as e:
        print(f"Finnhub Error: {e}")
    return go.Figure().update_layout(title="Market Data Error", template="plotly_dark")

if __name__ == "__main__":
    app.run_server(debug=True)
