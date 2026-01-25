import os
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime
import plotly.graph_objs as go

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import dash_leaflet.express as dlx
import openai

# ----------------------------
# ENVIRONMENT
# ----------------------------
openai.api_key = os.environ.get("OPENAI_API_KEY")
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")

# ----------------------------
# SAMPLE TEXAS SOLAR DATA
# ----------------------------
# Replace this with actual data source if available
texas_solar_zones = {
    "Austin": {"lat": 30.2672, "lon": -97.7431},
    "Dallas": {"lat": 32.7767, "lon": -96.7970},
    "Houston": {"lat": 29.7604, "lon": -95.3698},
}

# Dummy supply-demand data
def get_supply_demand(city):
    x = np.linspace(0, 10, 50)
    commercial = np.sin(x) + 5 + np.random.rand(50)
    residential = np.cos(x) + 5 + np.random.rand(50)
    equilibrium = (commercial + residential) / 2
    tou_price = np.linspace(0.1, 0.3, 50)
    return pd.DataFrame({
        "x": x,
        "Commercial": commercial,
        "Residential": residential,
        "Equilibrium": equilibrium,
        "TOU Price": tou_price
    })

# ----------------------------
# GEMINI AI SUMMARY
# ----------------------------
def get_gemini_summary(prompt):
    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=200
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error fetching Gemini AI summary: {e}"

# ----------------------------
# DASH APP SETUP
# ----------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# ----------------------------
# LAYOUT
# ----------------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("SpecuSol Solar Map", className="text-center"),
            html.P("Disclaimer: The information provided is for educational purposes only."),
            dl.Map(
                id="solar-map",
                center=[31.0, -97.0],
                zoom=6,
                children=[
                    dl.TileLayer(),
                    dl.LayerGroup(id="weather-layer"),
                    dl.MarkerClusterGroup(
                        id="markers",
                        children=[
                            dl.Marker(position=[v["lat"], v["lon"]], children=dl.Popup(k))
                            for k, v in texas_solar_zones.items()
                        ]
                    )
                ],
                style={'width': '100%', 'height': '500px'}
            )
        ], width=6),

        dbc.Col([
            html.H4("Supply & Demand Chart"),
            dcc.Graph(id="supply-demand-chart")
        ], width=6)
    ]),

    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H4("Finances & AI Summary"),
            dcc.Dropdown(
                id="stock-dropdown",
                options=[
                    {"label": "TAN (Solar ETF)", "value": "TAN"},
                    {"label": "TSLA", "value": "TSLA"},
                    {"label": "ENPH", "value": "ENPH"}
                ],
                value="TAN"
            ),
            dcc.Graph(id="stock-chart"),
            html.Div(id="gemini-summary", style={"marginTop": "20px"})
        ])
    ])
], fluid=True)

# ----------------------------
# CALLBACKS
# ----------------------------
@app.callback(
    Output("supply-demand-chart", "figure"),
    Input("solar-map", "click_lat_lng")
)
def update_chart(click_lat_lng):
    # Default city if none clicked
    city = "Austin"
    if click_lat_lng:
        lat, lon = click_lat_lng
        # Simple nearest city logic
        city = min(texas_solar_zones.keys(), key=lambda k: (texas_solar_zones[k]["lat"]-lat)**2 + (texas_solar_zones[k]["lon"]-lon)**2)
    df = get_supply_demand(city)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["x"], y=df["Commercial"], name="Commercial Supply"))
    fig.add_trace(go.Scatter(x=df["x"], y=df["Residential"], name="Residential Demand"))
    fig.add_trace(go.Scatter(x=df["x"], y=df["Equilibrium"], name="Equilibrium", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=df["x"], y=df["TOU Price"], name="TOU Price", yaxis="y2"))
    fig.update_layout(
        title=f"Solar Supply & Demand for {city}",
        yaxis=dict(title="Supply/Demand"),
        yaxis2=dict(title="TOU Price ($/kWh)", overlaying="y", side="right")
    )
    return fig

@app.callback(
    Output("stock-chart", "figure"),
    Output("gemini-summary", "children"),
    Input("stock-dropdown", "value")
)
def update_finances(stock_symbol):
    # Stock chart
    df = yf.download(stock_symbol, period="6mo", interval="1d")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name=stock_symbol))
    fig.update_layout(title=f"{stock_symbol} Closing Prices (6 months)")

    # Gemini AI summary
    prompt = f"Summarize recent trends and insights for {stock_symbol} in the solar energy sector."
    summary = get_gemini_summary(prompt)

    return fig, summary

# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
