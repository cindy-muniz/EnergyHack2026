import dash
from dash import html, dcc, Output, Input, State
import dash_leaflet as dl
import dash_leaflet.express as dlx
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime

# ------------------------------
# App Setup
# ------------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# ------------------------------
# Constants
# ------------------------------
TEXAS_CENTER = [31.0, -100.0]
ERCOT_ZONES = [...]  # your ERCOT GeoJSON / polygon data
WEATHER_URL = "https://developer.nrel.gov/api/solar/solar_resource/v1.json"
WEATHER_API_KEY = "xrKsemxjKJqoObOC1IDEvt4qNFbMQQy79pFqGWKF"
ETF_SYMBOL = "TAN"  # Example Solar ETF

# ------------------------------
# Layouts
# ------------------------------

home_layout = html.Div([
    html.H1("Specusol"),
    html.Img(src="https://image2url.com/r2/default/images/1769310659997-df25a758-c435-4795-bd4a-314cd27bf886.png",
             style={"height": "100px"}),
    html.P("Specusol is an information service. Information is for educational purposes only and is not intended to be used as investment advice."),
    html.P("This simulator demonstrates solar market conditions in Texas including ERCOT zones, weather, solar supply & demand, and solar stock ETFs.")
])

dashboard_layout = html.Div([
    html.Div([
        dcc.Graph(id="solar-chart"),
        dcc.Interval(id="update-interval-chart", interval=60*60*1000, n_intervals=0)  # hourly
    ], style={"width": "60%", "display": "inline-block", "vertical-align": "top"}),

    html.Div([
        dl.Map(center=TEXAS_CENTER, zoom=6, id="texas-map", children=[
            dl.TileLayer(),
            dl.LayerGroup(id="weather-layer"),
            dl.LayerGroup(id="ercot-layer")
        ], style={'width': '100%', 'height': '600px'}),
        dcc.Interval(id="update-interval-map", interval=60*60*1000, n_intervals=0)  # hourly
    ], style={"width": "38%", "display": "inline-block"})
])

finance_layout = html.Div([
    html.H2("Solar Stock ETF"),
    dcc.Input(id="finance-loc-input", type="text", placeholder="Enter City or ZIP"),
    html.Button("Update", id="finance-update-btn"),
    html.Div(id="finance-summary"),
    dcc.Graph(id="etf-chart"),
    dcc.Interval(id="update-interval-etf", interval=60*60*1000, n_intervals=0)  # hourly
])

# ------------------------------
# Navigation
# ------------------------------
app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div([
        dcc.Link("Home | ", href="/"),
        dcc.Link("Dashboard | ", href="/dashboard"),
        dcc.Link("Finance", href="/finance")
    ]),
    html.Div(id="page-content")
])

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/dashboard":
        return dashboard_layout
    elif pathname == "/finance":
        return finance_layout
    else:
        return home_layout

# ------------------------------
# Helper Functions
# ------------------------------

def get_weather(lat, lon):
    params = {"api_key": WEATHER_API_KEY, "lat": lat, "lon": lon}
    r = requests.get(WEATHER_URL, params=params)
    return r.json()

def build_figure(lat, lon):
    # Placeholder: Replace with your real solar dataset
    df = pd.DataFrame({
        "timestamp": pd.date_range(datetime.now(), periods=24, freq='H'),
        "res_supply": np.random.rand(24) * 100,
        "ind_supply": np.random.rand(24) * 200
    })
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply, name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.ind_supply, name="Industrial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply + df.ind_supply, name="Equilibrium Curve", line=dict(color="green", dash="dash")))
    fig.update_layout(title="Solar Supply & Demand", xaxis_title="Time", yaxis_title="MW")
    return fig

def get_etf_data(symbol):
    df = yf.download(symbol, period="7d", interval="1h")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name=f"{symbol} Price"))
    fig.update_layout(title=f"{symbol} Price Over Last 7 Days", xaxis_title="Time", yaxis_title="Price ($)")
    return fig

def generate_ai_summary(locale):
    import genai
    client = genai.Client(api_key="AIzaSyBFbTd_exi5T7ezqYitEYPWTZNL_uwBz-C")
    prompt = f"""Act as: A Senior ERCOT Market Analyst and Energy Broker Advisor.
Task: Provide a concise market outlook for solar energy in a specific Texas locale.
Locale: {locale}
Analysis Framework: Use 4 solar indicators...
Output Format: Market Sentiment, Broker Summary, Key Risk Factor, Pro Tip"""
    response = client.models.generate_content(model="gemini-flash-lite-latest", contents=prompt)
    return response.text

# ------------------------------
# Callbacks
# ------------------------------

@app.callback(
    Output("solar-chart", "figure"),
    Input("texas-map", "click_lat_lng"),
    Input("update-interval-chart", "n_intervals")
)
def update_solar_chart(click_lat_lng, n_intervals):
    if click_lat_lng:
        lat, lon = click_lat_lng
    else:
        lat, lon = TEXAS_CENTER
    return build_figure(lat, lon)

@app.callback(
    Output("weather-layer", "children"),
    Input("update-interval-map", "n_intervals")
)
def update_weather(n_intervals):
    # Example: adding one weather marker per city
    cities = [(30.26, -97.74, "Austin"), (32.77, -96.79, "Dallas")]
    markers = [dl.Marker(position=[lat, lon], children=dl.Tooltip(name)) for lat, lon, name in cities]
    return markers

@app.callback(
    Output("etf-chart", "figure"),
    Output("finance-summary", "children"),
    Input("finance-update-btn", "n_clicks"),
    Input("update-interval-etf", "n_intervals"),
    State("finance-loc-input", "value")
)
def update_finance(n_clicks, n_intervals, locale):
    fig = get_etf_data(ETF_SYMBOL)
    summary = generate_ai_summary(locale if locale else "Austin, TX")
    return fig, summary

# ------------------------------
# Run
# ------------------------------
if __name__ == "__main__":
    app.run_server(debug=True)

