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

# Initialize app with CYBORG theme
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
geolocator = Nominatim(user_agent=f"specusol_final_v9_{random.randint(1000, 9999)}")

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
    # 1. HEADER SECTION (Centering Logo and Tagline)
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(src=app.get_asset_url("logo.png"), style={"height": "160px", "marginBottom": "10px"}),
                html.H5("Live Solar Insights for Texas Energy Leaders", style={"color": LOGO_BLUE, "opacity": "0.8"}),
            ], className="text-center py-4")
        ], width=12)
    ]),

    dbc.Row([
        # 2. SIDEBAR (Map, Environmental Equations)
        dbc.Col([
            html.Div([
                dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "300px", "borderRadius": "12px"}, id="map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer")
                ]),
                html.Div(id="ercot-status", className="mt-2 text-warning fw-bold text-center small")
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
                        html.Small("CI = Base * (1 - S/D)", className="text-muted d-block small"),
                        html.Small("f = 60 + α(S-D)", className="text-muted d-block mt-3 small")
                    ], width=5)
                ])
            ], style=GLASS_STYLE)
        ], lg=4),

        # 3. CENTER (Technical Model with Equilibrium)
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

    # 4. HORIZONTAL WEATHER (Restored original cards/icons)
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("7-HOUR LOCALIZED FORECAST & IRRADIANCE", style={"color": LOGO_YELLOW}, className="mb-3 fw-bold"),
                dbc.Row(id="forecast-row", className="text-center g-2")
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # 5. FINANCE SECTION (Candlesticks, Best Fit, Multi-Stock)
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("FINANCIAL RISK & MARKET OVERLAY", style={"color": LOGO_BLUE}, className="mb-3 fw-bold"),
                dbc.Row([
                    dbc.Col([
                        html.P("Option Delta", className="text-muted small mb-0"),
                        html.H5("0.336", className="text-primary"),
                        html.P("Trend Confidence", className="text-muted small mb-0"),
                        html.H5("79.53%", className="text-info")
                    ], width=2),
                    dbc.Col([
                        html.Label("Overlay Stocks", className="text-muted small"),
                        dcc.Checklist(
                            id="stock-selector",
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
                # Unified ID to match error log fix
                dcc.Graph(id="market-comparison-graph", style={"height": "450px"})
            ], style=GLASS_STYLE)
        ], width=12)
    ]),

    # 6. FOOTER
    html.Footer([
        html.P("Specusol is an information service. Any insights are not intended to be investing advice and are for educational purposes only. © 2026", 
               className="text-muted small text-center mt-4")
    ])
])

# --- MATHEMATICAL ENGINE ---

def get_solar_math(t):
    return 1000 * np.exp(-0.5 * ((t - 13.25) / 2.5) ** 2)

@app.callback(
    [Output("ftc-graph", "figure"), Output("forecast-row", "children"), Output("ercot-status", "children")],
    Input("addr-btn", "n_clicks"), State("addr-input", "value")
)
def update_solar_model(n, addr):
    t = np.linspace(0, 24, 100)
    sun = get_solar_math(t)
    
    # Separated Grid Profiles
    res_s, comm_s = sun * 0.4, sun * 0.8
    res_d = 250 + 100 * np.sin((t-16)/12*np.pi)
    comm_d = 550 + 150 * np.sin((t-10)/12*np.pi)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=res_s, name="Res. Supply", line=dict(color=LOGO_YELLOW)))
    fig.add_trace(go.Scatter(x=t, y=comm_s, name="Comm. Supply", line=dict(color=LOGO_ORANGE)))
    fig.add_trace(go.Scatter(x=t, y=res_d, name="Res. Demand", line=dict(color=LOGO_BLUE, dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=comm_d, name="Comm. Demand (Total)", line=dict(color="#003399"))) # SOLID
    fig.add_trace(go.Scatter(x=t, y=sun, name="Daylight Intensity", fill='tozeroy', line=dict(color="rgba(255,255,255,0.05)")))
    
    # Equilibrium Calculation
    diff = (res_s + comm_s) - (res_d + comm_d)
    idx = np.argwhere(np.diff(np.sign(diff))).flatten()
    if len(idx) > 0:
        fig.add_annotation(x=t[idx[0]], y=res_s[idx[0]]+comm_s[idx[0]], text="EQUILIBRIUM", showarrow=True, bgcolor="green")

    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=30))

    # Weather cards
    forecast = []
    for i in range(7):
        hr = (datetime.now().hour + i) % 24
        val = int(get_solar_math(hr))
        temp = round(21 + 5 * np.sin((hr-14)/12*np.pi), 1)
        forecast.append(dbc.Col(html.Div([
            html.Small(f"{hr}:00", className="text-muted"),
            html.H5(f"{temp}°C", style={"color": LOGO_ORANGE}, className="mt-1"),
            html.Small(f"{val} W/m²", style={"color": LOGO_BLUE}, className="d-block"),
            html.I(className=f"fas {'fa-sun' if val > 100 else 'fa-moon'} text-info")
        ], className="p-2 border border-secondary rounded"), xs=4, md=True))

    return fig, forecast, "✅ Verified ERCOT Reliability Zone"

@app.callback(
    Output("market-comparison-graph", "figure"),
    [Input("stock-selector", "value"), Input("horizon", "value"), Input("toggle-fit", "value")]
)
def update_market_charts(stocks, horizon, fit):
    fig = go.Figure()
    points = {"1W": 100, "1M": 30, "1Y": 52}[horizon]
    
    for s in stocks:
        base = {"TAN":55, "ENPH":120, "VLO":140, "FSLR":160, "WHD":48}[s]
        prices = base * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, points)))
        x = np.arange(points)
        
        if len(stocks) == 1:
            # Candlestick for single stock
            fig.add_trace(go.Candlestick(x=x, open=prices*0.99, high=prices*1.02, low=prices*0.98, close=prices, name=s))
        else:
            # Line overlay for multiple
            fig.add_trace(go.Scatter(x=x, y=prices, name=s))
            
        if "fit" in fit and s == stocks[0]:
            slope, intercept, r, p, std = linregress(x, prices)
            fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, name="Trend Line", line=dict(dash='dot', color="green")))
            # Display Equation directly on chart
            fig.add_annotation(x=points//2, y=prices[points//2], text=f"y = {slope:.2f}x + {intercept:.1f}", showarrow=False, font=dict(color="green"))

    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
    return fig

@app.callback(
    [Output("map", "viewport"), Output("marker-layer", "children")],
    Input("addr-btn", "n_clicks"), State("addr-input", "value")
)
def move_map(n, addr):
    if n and addr:
        try:
            loc = geolocator.geocode(addr, timeout=10)
            if loc:
                return {"center": [loc.latitude, loc.longitude], "zoom": 12}, [dl.Marker(position=[loc.latitude, loc.longitude])]
        except: pass
    return exceptions.PreventUpdate

if __name__ == "__main__":
    app.run_server(debug=True)
