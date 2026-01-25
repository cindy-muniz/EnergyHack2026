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
import random

# Initialize app with CYBORG foundation
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_final_reliability_{random.randint(1000, 9999)}")

# Custom Color Palette from Logo
LOGO_ORANGE = "#FF8C00"
LOGO_BLUE = "#0066FF"
LOGO_YELLOW = "#FFD700"

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.03)", "backdropFilter": "blur(12px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

app.layout = dbc.Container(fluid=True, className="p-4 bg-black text-white", children=[
    # --- HEADER WITH INTEGRATED LOGO ---
    dbc.Row([
        dbc.Col([
            html.Div([
                # This looks for assets/logo.png
                html.Img(src=app.get_asset_url("logo.png"), 
                         style={"height": "140px", "marginBottom": "10px"}),
                html.H2(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0"),
                html.H5("Live Solar Insights for Texas Energy Leaders", style={"color": LOGO_BLUE, "opacity": "0.8"}),
            ], className="text-center mb-4")
        ], width=12)
    ]),

    dbc.Row([
        # SIDEBAR: Map & Weather
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "300px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer")
                ]),
                html.Div(id="ercot-notif", className="mt-2 text-warning fw-bold text-center small")
            ], style=GLASS_STYLE),

            html.Div([
                html.H6("ENVIRONMENTAL SIDEBAR", style={"color": LOGO_BLUE, "fontWeight": "bold"}, className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Carbon Intensity", className="text-muted small mb-0"),
                        html.H5("0.28 kg/kWh", className="text-success"),
                        html.P("Grid Frequency", className="text-muted small mb-0"),
                        html.H5("59.749 Hz", className="text-warning")
                    ], width=7),
                    dbc.Col([
                        html.Small("CI = Base*(1-S/D)", className="text-muted small"),
                        html.Small("f = 60+α(S-D)", className="text-muted mt-3 d-block small")
                    ], width=5)
                ]),
                html.Hr(className="border-secondary"),
                html.Label("7-HOUR WEATHER & IRRADIANCE", style={"color": LOGO_YELLOW, "fontSize": "0.8rem", "fontWeight": "bold"}),
                html.Div(id="forecast-content")
            ], style=GLASS_STYLE)
        ], lg=4),

        # MAIN: Technical Grid Model
        dbc.Col([
            html.Div([
                dbc.InputGroup([
                    dbc.Input(id="addr-input", placeholder="Enter Texas Address...", type="text", className="bg-dark text-white"),
                    dbc.Button("ANALYZE", id="addr-btn", color="warning"),
                ], className="mb-3"),
                dcc.Graph(id="supply-demand-chart", style={"height": "500px"})
            ], style=GLASS_STYLE)
        ], lg=8)
    ]),

    # FOOTER
    html.Footer([
        html.P("Specusol is an information service. Any insights are not intended to be investing advice and are for educational purposes only. © 2026", 
               className="text-muted small text-center mt-4")
    ])
])

# --- MATHEMATICAL ENGINES ---

def get_daylight_math(t):
    # Simulated Solar Intensity Bell Curve
    return 1000 * np.exp(-0.5 * ((t - 13.25) / 2.5) ** 2)

@app.callback(
    [Output("supply-demand-chart", "figure"), Output("forecast-content", "children")],
    Input("addr-btn", "n_clicks"),
    State("addr-input", "value")
)
def update_leader_metrics(n, addr):
    t = np.linspace(0, 24, 100)
    daylight = get_daylight_math(t)
    
    # Model Logic
    res_supply, comm_supply = daylight * 0.4, daylight * 0.8
    res_demand = 220 + 110 * np.sin((t-16)/12*np.pi)
    comm_demand = 580 + 190 * np.sin((t-10)/12*np.pi)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=res_supply, name="Res. Supply", line=dict(color=LOGO_YELLOW)))
    fig.add_trace(go.Scatter(x=t, y=comm_supply, name="Comm. Supply", line=dict(color=LOGO_ORANGE)))
    fig.add_trace(go.Scatter(x=t, y=res_demand, name="Res. Demand", line=dict(color=LOGO_BLUE, dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=comm_demand, name="Comm. Demand", line=dict(color="#003399", dash="dash")))
    
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', title="FTC Model: Residential vs Commercial Grid")

    # Forecast Cards
    forecast = []
    for i in range(7):
        hr = (datetime.now().hour + i) % 24
        irr = int(get_daylight_math(hr))
        temp = round(21 + 6 * np.sin((hr-14)/12*np.pi), 1)
        forecast.append(html.Div([
            html.Span(f"{hr}:00", className="text-muted small"),
            html.Span(f"  {temp}°C", style={"color": LOGO_ORANGE, "fontWeight": "bold"}, className="px-2"),
            html.Span(f"{irr} W/m²", style={"color": LOGO_BLUE}, className="small")
        ], className="border-bottom border-secondary py-1"))

    return fig, forecast

if __name__ == "__main__":
    app.run_server(debug=True)
