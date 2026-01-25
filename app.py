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

# Initialize app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_platinum_v10_{random.randint(1000, 9999)}")

# Custom Colors
LOGO_ORANGE = "#FF8C00"
LOGO_BLUE = "#0066FF"
LOGO_YELLOW = "#FFD700"
PURPLE_LIGHT = "rgba(147, 51, 234, 0.2)" # Semi-transparent purple

STOCKS = {
    "TAN": {"name": "Invesco Solar ETF", "loc": "US Index"},
    "ENPH": {"name": "Enphase Energy", "loc": "US Solar Tech"},
    "VLO": {"name": "Valero Energy", "loc": "Texas Energy"},
    "FSLR": {"name": "First Solar", "loc": "US Manufacturer"},
    "WHD": {"name": "Cactus Inc.", "loc": "Texas Equipment"}
}

# ERCOT Boundary Logic (Native Python for Render Stability)
ZONES = {
    "North": {"lat": [33.0, 36.5], "lon": [-103.0, -94.0]},
    "South": {"lat": [25.8, 29.5], "lon": [-101.0, -96.5]},
    "West": {"lat": [29.5, 34.0], "lon": [-106.5, -101.0]},
    "Houston": {"lat": [29.0, 30.5], "lon": [-96.0, -94.5]}
}

GLASS_STYLE = {"background": "rgba(255, 255, 255, 0.03)", "backdropFilter": "blur(12px)", "borderRadius": "15px", "border": "1px solid rgba(255, 255, 255, 0.1)", "padding": "20px", "marginBottom": "20px"}

app.layout = dbc.Container(fluid=True, className="p-4 bg-black text-white", children=[
    # --- HEADER ---
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(src=app.get_asset_url("logo.png"), style={"height": "160px", "marginBottom": "10px"}),
                html.H5("Live Solar Insights for Texas Energy Leaders", style={"color": LOGO_BLUE, "opacity": "0.8"}),
            ], className="text-center py-4")
        ], width=12)
    ]),

    dbc.Row([
        # SIDEBAR
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "300px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer")
                ]),
                html.Div(id="ercot-status", className="mt-2 text-warning fw-bold text-center small")
            ], style=GLASS_STYLE),

            html.Div([
                html.H6("ENVIRONMENTAL & GRID ANALYTICS", style={"color": LOGO_BLUE, "fontWeight": "bold"}, className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Carbon Intensity", className="text-muted small mb-0"),
                        html.H5("0.28 kg/kWh", className="text-success"),
                        html.P("Grid Frequency", className="text-muted small mb-0"),
                        html.H5("59.749 Hz", className="text-warning")
                    ], width=7),
                    dbc.Col([
                        html.Div([
                            html.Small("CI = Base*(1-S/D)", className="text-muted d-block small"),
                            html.Small("f = 60+α(S-D)", className="text-muted d-block mt-2 small"),
                        ])
                    ], width=5)
                ]),
                html.P("Why this matters: High CI indicates reliance on fossil fuels; frequency deviations track real-time supply-demand imbalances causing grid stress.", 
                       className="text-muted mt-3", style={"fontSize": "0.75rem"})
            ], style=GLASS_STYLE)
        ], lg=4),

        # FTC MAIN
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

    # WEATHER ROW (Fahrenheit)
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("7-HOUR LOCALIZED FORECAST (FAHRENHEIT)", style={"color": LOGO_YELLOW}, className="mb-3 fw-bold"),
                dbc.Row(id="forecast-row", className="text-center g-2")
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # FINANCE
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("MARKET RISK & GREEK OVERLAY", style={"color": LOGO_BLUE}, className="mb-3 fw-bold"),
                dbc.Row([
                    dbc.Col([
                        html.P("Option Delta", className="text-muted small mb-0"),
                        html.H5("0.336", className="text-primary"),
                        html.P("Trend Confidence", className="text-muted small mb-0"),
                        html.H5("79.53%", className="text-info")
                    ], width=2),
                    dbc.Col([
                        html.Small("Delta measures the sensitivity of solar asset values relative to market shifts. Essential for hedging portfolios against ERCOT volatility.", 
                                   className="text-muted d-block small mt-2")
                    ], width=4),
                    dbc.Col([
                        dcc.Checklist(id="stock-selector", options=[{"label": f" {k}", "value": k} for k in STOCKS.keys()],
                                      value=["TAN"], className="text-white small", inline=True),
                        dbc.RadioItems(id="horizon", options=[{"label": i, "value": i} for i in ["1W", "1M", "1Y"]], 
                                       value="1M", inline=True, className="text-warning mt-2"),
                        dbc.Checklist(options=[{"label": "Best Fit Trend", "value": "fit"}], value=[], id="toggle-fit", switch=True, className="text-success mt-2")
                    ], width=6)
                ]),
                dcc.Graph(id="market-comparison-graph", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ])
])

# --- LOGIC ---

def get_solar_math(t):
    return 1000 * np.exp(-0.5 * ((t - 13.25) / 2.5) ** 2)

@app.callback(
    [Output("ftc-graph", "figure"), Output("forecast-row", "children"), Output("ercot-status", "children"), Output("map", "viewport"), Output("marker-layer", "children")],
    Input("addr-btn", "n_clicks"), State("addr-input", "value")
)
def update_all_technical(n, addr):
    t = np.linspace(0, 24, 100)
    sun = get_solar_math(t)
    res_s, comm_s = sun * 0.4, sun * 0.8
    res_d = 250 + 100 * np.sin((t-16)/12*np.pi)
    comm_d = 550 + 150 * np.sin((t-10)/12*np.pi)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=res_s, name="Res. Supply", line=dict(color=LOGO_YELLOW)))
    fig.add_trace(go.Scatter(x=t, y=comm_s, name="Comm. Supply", line=dict(color=LOGO_ORANGE)))
    fig.add_trace(go.Scatter(x=t, y=res_d, name="Res. Demand", line=dict(color="#00CCFF", dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=comm_d, name="Comm. Demand", line=dict(color="#003399")))
    fig.add_trace(go.Scatter(x=t, y=sun, name="Daylight Model", fill='tozeroy', fillcolor=PURPLE_LIGHT, line=dict(color="rgba(147, 51, 234, 0.4)")))
    
    # Equilibrium Marker (Green)
    diff = (res_s + comm_s) - (res_d + comm_d)
    idx = np.argwhere(np.diff(np.sign(diff))).flatten()
    if len(idx) > 0:
        fig.add_annotation(x=t[idx[0]], y=res_s[idx[0]]+comm_s[idx[0]], text="EQUILIBRIUM", showarrow=True, arrowhead=2, bgcolor="green", font=dict(color="white"))

    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=30))

    # Weather (Fahrenheit)
    forecast = []
    for i in range(7):
        hr = (datetime.now().hour + i) % 24
        val = int(get_solar_math(hr))
        temp_c = 21 + 5 * np.sin((hr-14)/12*np.pi)
        temp_f = round((temp_c * 9/5) + 32, 1) # Fahrenheit Conversion
        forecast.append(dbc.Col(html.Div([
            html.Small(f"{hr}:00", className="text-muted"),
            html.H5(f"{temp_f}°F", style={"color": LOGO_ORANGE}, className="mt-1"),
            html.Small(f"{val} W/m²", style={"color": LOGO_BLUE}, className="d-block"),
            html.I(className=f"fas {'fa-sun' if val > 100 else 'fa-moon'} text-info")
        ], className="p-2 border border-secondary rounded"), xs=4, md=True))

    # ERCOT Logic & Map
    status = "⚠️ Outside ERCOT Domain"
    viewport = {"center": [31.0, -100.0], "zoom": 6}
    markers = []
    if n and addr:
        try:
            loc = geolocator.geocode(addr, timeout=10)
            if loc:
                viewport = {"center": [loc.latitude, loc.longitude], "zoom": 12}
                markers = [dl.Marker(position=[loc.latitude, loc.longitude])]
                for zone, bounds in ZONES.items():
                    if bounds['lat'][0] <= loc.latitude <= bounds['lat'][1] and bounds['lon'][0] <= loc.longitude <= bounds['lon'][1]:
                        status = f"✅ Verified ERCOT {zone} Zone"
                        break
        except: pass

    return fig, forecast, status, viewport, markers

@app.callback(
    Output("market-comparison-graph", "figure"),
    [Input("stock-selector", "value"), Input("horizon", "value"), Input("toggle-fit", "value")]
)
def update_market_visuals(stocks, horizon, fit):
    fig = go.Figure()
    points = {"1W": 100, "1M": 30, "1Y": 52}[horizon]
    for s in stocks:
        base = {"TAN":55, "ENPH":120, "VLO":140, "FSLR":160, "WHD":48}[s]
        prices = base * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, points)))
        x = np.arange(points)
        if len(stocks) == 1:
            fig.add_trace(go.Candlestick(x=x, open=prices*0.99, high=prices*1.02, low=prices*0.98, close=prices, name=s))
        else:
            fig.add_trace(go.Scatter(x=x, y=prices, name=s))
        if "fit" in fit and s == stocks[0]:
            slope, intercept, r, p, std = linregress(x, prices)
            fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, name="Trend Line", line=dict(dash='dot', color="green")))
            fig.add_annotation(x=points//2, y=prices[points//2], text=f"y = {slope:.2f}x + {intercept:.1f}", showarrow=False, font=dict(color="green"))
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
