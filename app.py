import os
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, exceptions, ctx
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
from scipy.stats import linregress
import random

# Initialize app with CYBORG foundation
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_leaders_vfinal_{random.randint(1000, 9999)}")

# Custom Color Palette
LOGO_ORANGE = "#FF8C00"
LOGO_BLUE = "#0066FF"
LOGO_YELLOW = "#FFD700"

STOCKS = {
    "TAN": {"name": "Invesco Solar ETF", "loc": "US Index"},
    "ENPH": {"name": "Enphase Energy", "loc": "US Solar Tech"},
    "VLO": {"name": "Valero Energy", "loc": "Texas Energy"},
    "FSLR": {"name": "First Solar", "loc": "US Manufacturer"},
    "WHD": {"name": "Cactus Inc.", "loc": "Texas Equipment"}
}

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.03)", "backdropFilter": "blur(12px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

app.layout = dbc.Container(fluid=True, className="p-4 bg-black text-white", children=[
    # --- HEADER WITH LOGO ---
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(src=app.get_asset_url("logo.png"), 
                         style={"height": "160px", "marginBottom": "10px"}),
                html.H5("Live Solar Insights for Texas Energy Leaders", className="text-info opacity-75 mt-1"),
            ], className="text-center py-4")
        ], width=12)
    ]),

    dbc.Row([
        # SIDEBAR: Map & Environmental Stats
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "300px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer")
                ]),
                html.Div(id="ercot-status", className="mt-2 text-warning fw-bold text-center small")
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
                        html.Small("CI = Base * (1 - S/D)", className="text-muted d-block small"),
                        html.Small("f = 60 + α(S-D)", className="text-muted d-block mt-3 small")
                    ], width=5)
                ])
            ], style=GLASS_STYLE)
        ], lg=4),

        # MAIN: Technical Grid Model (FTC)
        dbc.Col([
            html.Div([
                dbc.InputGroup([
                    dbc.Input(id="addr-input", placeholder="Texas Address...", type="text", className="bg-dark text-white"),
                    dbc.Button("ANALYZE", id="addr-btn", color="warning"),
                ], className="mb-3"),
                dcc.Graph(id="ftc-graph", style={"height": "480px"})
            ], style=GLASS_STYLE)
        ], lg=8)
    ]),

    # --- HORIZONTAL WEATHER ROW ---
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("7-HOUR LOCALIZED FORECAST & IRRADIANCE", className="text-info mb-3 fw-bold"),
                dbc.Row(id="forecast-horizontal-row", className="text-center g-2")
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # --- FINANCE & MARKET ANALYTICS ---
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
                    ], width=2),
                    dbc.Col([
                        html.Label("Compare Overlays", className="text-muted small"),
                        dcc.Checklist(
                            id="stock-check",
                            options=[{"label": f" {k}", "value": k} for k in STOCKS.keys()],
                            value=["TAN"], className="text-white small", inline=True
                        ),
                        dbc.RadioItems(id="horizon", options=[{"label": i, "value": i} for i in ["1W", "1M", "1Y"]], 
                                       value="1M", inline=True, className="text-warning mt-2"),
                    ], width=6),
                    dbc.Col([
                        dbc.Checklist(options=[{"label": "Best Fit Trend", "value": "fit"}], value=[], id="toggle-fit", switch=True, className="text-success")
                    ], width=4)
                ]),
                dcc.Graph(id="finance-graph", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    html.Footer([
        html.P("Specusol is an information service. Any insights are not intended to be investing advice and are for educational purposes only. © 2026", 
               className="text-muted small text-center mt-4")
    ])
])

# --- MATHEMATICAL ENGINE ---

def daylight_math(t):
    return 1000 * np.exp(-0.5 * ((t - 13.25) / 2.5) ** 2)

@app.callback(
    [Output("ftc-graph", "figure"), Output("forecast-horizontal-row", "children")],
    Input("addr-btn", "n_clicks"), State("addr-input", "value")
)
def update_technical_ui(n, addr):
    t = np.linspace(0, 24, 100)
    sun = daylight_math(t)
    
    res_s, comm_s = sun * 0.4, sun * 0.8
    res_d = 250 + 100 * np.sin((t-16)/12*np.pi)
    comm_d = 550 + 150 * np.sin((t-10)/12*np.pi)
    
    fig = go.Figure
