# app.py

import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_leaflet as dl
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.express as px
from datetime import datetime

# -------------------------
# Initialize Dash app
# -------------------------
app = dash.Dash(__name__)
server = app.server

# -------------------------
# Data fetching & processing
# -------------------------
def get_stock_data(ticker="AAPL", period="1d", interval="1h"):
    """Fetch hourly stock data using yfinance."""
    df = yf.download(ticker, period=period, interval=interval)
    df.reset_index(inplace=True)
    return df

def get_geojson_points():
    """Example Leaflet points; replace with your API if needed."""
    return [
        {"lat": 37.7749, "lon": -122.4194, "label": "San Francisco"},
        {"lat": 34.0522, "lon": -118.2437, "label": "Los Angeles"},
    ]

# -------------------------
# Layout
# -------------------------
app.layout = html.Div([
    html.H1("Dashboard Example"),
    
    html.Div([
        html.Label("Select Stock:"),
        dcc.Dropdown(
            id="stock-dropdown",
            options=[
                {"label": "Apple (AAPL)", "value": "AAPL"},
                {"label": "Tesla (TSLA)", "value": "TSLA"},
                {"label": "Amazon (AMZN)", "value": "AMZN"},
            ],
            value="AAPL"
        ),
        dcc.Graph(id="stock-chart")
    ]),
    
    html.Div([
        html.H3("Map Example"),
        dl.Map(
            children=[
                dl.TileLayer(),
                dl.LayerGroup(id="points-layer")
            ],
            center=[36, -119],
            zoom=5,
            style={"width": "100%", "height": "500px"}
        )
    ]),

    dcc.Interval(
        id="interval-component",
        interval=3600*1000,  # 1 hour in milliseconds
        n_intervals=0
    )
])

# -------------------------
# Callbacks
# -------------------------
@app.callback(
    Output("stock-chart", "figure"),
    Input("stock-dropdown", "value"),
    Input("interval-component", "n_intervals")
)
def update_stock_chart(ticker, n):
    df = get_stock_data(ticker)
    fig = px.line(df, x="Datetime", y="Close", title=f"{ticker} Hourly Prices")
    return fig

@app.callback(
    Output("points-layer", "children"),
    Input("interval-component", "n_intervals")
)
def update_map_points(n):
    points = get_geojson_points()
    return [
        dl.Marker(position=[p["lat"], p["lon"]], children=dl.Popup(p["label"]))
        for p in points
    ]

# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    app.run_server(debug=True)

