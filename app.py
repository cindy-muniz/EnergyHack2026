import os
import pandas as pd
import yfinance as yf
import numpy as np
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, exceptions, ctx
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import random

# Initialize app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server

# Geolocation setup - Still needed for address-to-coords
ua_string = f"specusol_internal_engine_{random.randint(1000, 9999)}"
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
            html.P("Internalized Solar Analytics & Grid Modeling (No-API Build)", className="text-muted small")
        ], width=7),
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="addr-input", placeholder="Search Texas Address...", type="text", className="bg-dark text-white"),
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

    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("7-HOUR LOCALIZED MICRO-CLIMATE FORECAST", className="text-info mb-3 fw-bold"),
                dbc.Row(id="forecast-row", className="text-center g-2")
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("SOLAR TEXAS MUTUAL FUND (TAN) - Market Data", className="text-info mb-3 fw-bold"),
                dcc.Graph(id="solar-etf", style={"height": "350px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),
    
    dcc.Store(id='coords-store', data={'lat': 30.26, 'lon': -97.74})
])

# --- Logic: The Internal Model ---

def get_internal_model_data(lat, lon):
    # Generates 168 hours of data based on Solar Physics models
    now = datetime.now()
    times = [now + timedelta(hours=i) for i in range(168)]
    hours = np.array([t.hour for t in times])
    
    # Solar Output Model: Peak at noon, zero at night
    # We adjust the "peak" slightly based on Latitude
    lat_factor = np.cos(np.radians(lat))
    ghi = np.maximum(0, 1000 * np.sin((hours - 6) / 12 * np.pi) * lat_factor)
    
    # Supply and Demand simulation
    res_supply = ghi * 1.8
    comm_supply = ghi * 6.5
    res_demand = 200 + 100 * np.sin((hours - 16) / 12 * np.pi) # Peaks at 4pm
    comm_demand = 500 + 200 * np.sin((hours - 10) / 12 * np.pi) # Peaks at 10am
    
    # Micro-climate Temperature Model
    # Baselined at 20C + time of day variance + latitudinal cooling
    temps = 20 + 10 * np.sin((hours - 14) / 12 * np.pi) - (lat - 30)
    
    df = pd.DataFrame({
        'time': times,
        'res_supply': res_supply,
        'comm_supply': comm_supply,
        'res_demand': res_demand,
        'comm_demand': comm_demand,
        'temp': temps
    })
    return df

# --- Callbacks ---

@app.callback(
    [Output("map", "viewport"), Output("marker-layer", "children"), Output("coords-store", "data")],
    [Input("addr-btn", "n_clicks"), Input("map", "clickData")],
    State("addr-input", "value"),
    prevent_initial_call=True
)
def update_location(n, clickData, address):
    t_id = ctx.triggered_id
    if t_id == "addr-btn" and address:
        try:
            loc = geolocator.geocode(address, timeout=10)
            if loc:
                return {"center": [loc.latitude, loc.longitude], "zoom": 12}, \
                       [dl.Marker(position=[loc.latitude, loc.longitude])], \
                       {'lat': loc.latitude, 'lon': loc.longitude}
        except: pass
    elif t_id == "map" and clickData:
        lat, lon = clickData["latlng"]["lat"], clickData["latlng"]["lng"]
        return {"center": [lat, lon], "zoom": 10}, \
               [dl.Marker(position=[lat, lon])], \
               {'lat': lat, 'lon': lon}
    raise exceptions.PreventUpdate

@app.callback(
    [Output("supply-demand-chart", "figure"), Output("forecast-row", "children")],
    Input("coords-store", "data")
)
def update_technical_data(coords):
    lat, lon = coords['lat'], coords['lon']
    df = get_internal_model_data(lat, lon)
    
    # 1. Build FTC Graphs
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['time'], y=df['res_supply'], name="Res. Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df['time'], y=df['res_demand'], name="Res. Demand", line=dict(color="red", dash="dash")))
    fig.add_trace(go.Scatter(x=df['time'], y=df['comm_supply'], name="Comm. Supply", line=dict(color="#00CCFF")))
    fig.add_trace(go.Scatter(x=df['time'], y=df['comm_demand'], name="Comm. Demand", line=dict(color="blue", dash="dash")))
    
    fig.update_layout(
        title=f"Technical Grid Model (Synthetic): {lat:.2f}N",
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10,r=10,t=40,b=10), legend=dict(orientation="h", y=1.1)
    )

    # 2. Build Weather Cards from internal model
    forecast_cards = []
    for i in range(7):
        row = df.iloc[i]
        time_str = row['time'].strftime("%I %p")
        temp = round(row['temp'], 1)
        # Dynamic icon selection logic based on solar output
        icon = "fa-sun" if row['res_supply'] > 10 else "fa-moon"
        
        forecast_cards.append(dbc.Col(html.Div([
            html.Small(time_str, className="text-muted"),
            html.H5(f"{temp}°C", className="text-warning mt-1"),
            html.I(className=f"fas {icon} text-info")
        ], className="p-2 border border-secondary rounded"), xs=4, md=True))
        
    return fig, forecast_cards

@app.callback(Output("solar-etf", "figure"), Input("coords-store", "data"))
def update_etf(_):
    try:
        data = yf.download("TAN", period="5d", interval="1h", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        fig = go.Figure(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close']))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=10,b=10))
        return fig
    except: return go.Figure()

if __name__ == "__main__":
    app.run_server(debug=True)
