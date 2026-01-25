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
from scipy import stats
import time
import random

# Initialize app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server

FINNHUB_KEY = "KEY"
geolocator = Nominatim(user_agent=f"specusol_market_v4_{random.randint(1000, 9999)}")

# Stock Directory
ENERGY_STOCKS = {
    "TAN": {"name": "Invesco Solar ETF", "type": "Solar Index / Mutual Fund", "loc": "US-Based"},
    "ENPH": {"name": "Enphase Energy", "type": "Solar Tech", "loc": "US-Based"},
    "VLO": {"name": "Valero Energy", "type": "Energy / Refining", "loc": "Texas-Based"},
    "FSLR": {"name": "First Solar", "type": "Solar Manufacturer", "loc": "US-Based"},
    "WHD": {"name": "Cactus Inc.", "type": "Energy Equipment", "loc": "Texas-Based"},
    "RUN": {"name": "Sunrun Inc.", "type": "Residential Solar", "loc": "US-Based"}
}

app.layout = dbc.Container(fluid=True, className="p-4", children=[
    dbc.Row([
        dbc.Col([
            html.H1(["SPECUSOL ", html.Span("PRO", className="text-warning")], className="fw-bold mb-0"),
            html.P("Texas & US Energy Equity Intelligence", className="text-muted small")
        ], width=12),
    ], className="mb-4"),

    # Control Panel
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Select Primary Stock", className="text-info small"),
                dcc.Dropdown(
                    id="primary-stock",
                    options=[{"label": f"{s} - {v['name']} ({v['loc']})", "value": s} for s, v in ENERGY_STOCKS.items()],
                    value="TAN", className="mb-3 text-dark"
                ),
                html.Label("Compare / Overlay Stocks", className="text-info small"),
                dcc.Dropdown(
                    id="compare-stocks",
                    options=[{"label": s, "value": s} for s in ENERGY_STOCKS.keys()],
                    multi=True, className="mb-3 text-dark"
                ),
            ], style={"background": "rgba(255,255,255,0.05)", "padding": "15px", "borderRadius": "10px"})
        ], lg=4),
        
        dbc.Col([
            html.Div([
                html.Label("Time Horizon", className="text-info small"),
                dbc.RadioItems(
                    id="time-horizon",
                    options=[
                        {"label": "1D", "value": "1D"},
                        {"label": "1W", "value": "1W"},
                        {"label": "1M", "value": "1M"},
                        {"label": "6M", "value": "6M"},
                        {"label": "1Y", "value": "1Y"}
                    ],
                    value="1M", inline=True, className="mb-3 text-warning"
                ),
                dbc.Checklist(
                    options=[{"label": "Show Best Fit Line (Trend)", "value": "trend"}],
                    value=[], id="indicators-toggle", switch=True, className="text-success"
                ),
            ], style={"background": "rgba(255,255,255,0.05)", "padding": "15px", "borderRadius": "10px"})
        ], lg=8)
    ], className="mb-4"),

    # Main Market Graph
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="main-market-graph", style={"height": "600px"})
            ], style={"background": "rgba(0,0,0,0.2)", "borderRadius": "15px", "padding": "10px"})
        ], width=12)
    ])
])

# --- Helper Logic ---

def fetch_finnhub_data(symbol, horizon):
    end = int(time.time())
    resolutions = {"1D": "5", "1W": "60", "1M": "D", "6M": "D", "1Y": "W"}
    offsets = {"1D": 1, "1W": 7, "1M": 30, "6M": 180, "1Y": 365}
    
    start = end - (offsets[horizon] * 24 * 60 * 60)
    res = resolutions[horizon]
    
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={res}&from={start}&to={end}&token={FINNHUB_KEY}"
    r = requests.get(url, timeout=10).json()
    
    if r.get('s') == 'ok':
        return pd.DataFrame({
            't': [datetime.fromtimestamp(t) for t in r['t']],
            'o': r['o'], 'h': r['h'], 'l': r['l'], 'c': r['c']
        })
    return pd.DataFrame()

# --- Callbacks ---

@app.callback(
    Output("main-market-graph", "figure"),
    [Input("primary-stock", "value"),
     Input("compare-stocks", "value"),
     Input("time-horizon", "value"),
     Input("indicators-toggle", "value")]
)
def update_comparison_graph(primary, comparisons, horizon, indicators):
    fig = go.Figure()
    
    # 1. Fetch Primary Data
    df_p = fetch_finnhub_data(primary, horizon)
    if df_p.empty:
        return fig.update_layout(title="Data unavailable for selected horizon")

    # Add Primary as Candlestick if no overlays, otherwise Line for clarity
    if not comparisons:
        fig.add_trace(go.Candlestick(
            x=df_p['t'], open=df_p['o'], high=df_p['h'], low=df_p['l'], close=df_p['c'],
            name=f"{primary} (Primary)"
        ))
    else:
        fig.add_trace(go.Scatter(x=df_p['t'], y=df_p['c'], name=f"{primary} (Primary)", line=dict(width=3)))

    # 2. Add Comparison Overlays
    if comparisons:
        for symbol in comparisons:
            if symbol == primary: continue
            df_c = fetch_finnhub_data(symbol, horizon)
            if not df_c.empty:
                # Normalize data for comparison if needed (Price % Change)
                # For this build, we show raw USD price.
                fig.add_trace(go.Scatter(x=df_c['t'], y=df_c['c'], name=symbol, opacity=0.7))

    # 3. Best Fit Line (Linear Regression)
    if "trend" in indicators and not df_p.empty:
        # Convert time to numeric for regression
        x_numeric = np.arange(len(df_p))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_numeric, df_p['c'])
        line = slope * x_numeric + intercept
        fig.add_trace(go.Scatter(
            x=df_p['t'], y=line, name="Trend Line",
            line=dict(color="rgba(0, 255, 0, 0.5)", dash="dot")
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=1.05),
        hovermode="x unified"
    )
    
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
