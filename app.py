import os
import pandas as pd
import yfinance as yf
import requests
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objs as go
import openai

# Gemini AI key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")

# Initialize Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # For Render deployment

# ---- Sample Data ----
# Texas solar zones (simplified coordinates)
TEXAS_ZONES = {
    "Houston": {"lat": 29.7604, "lon": -95.3698},
    "Dallas": {"lat": 32.7767, "lon": -96.7970},
    "Austin": {"lat": 30.2672, "lon": -97.7431},
    "San Antonio": {"lat": 29.4241, "lon": -98.4936},
}

# Dummy supply-demand data
def get_supply_demand(zone):
    # In real scenario, fetch real data per zone
    df = pd.DataFrame({
        "Type": ["Commercial", "Residential"],
        "Supply": [100 + hash(zone) % 50, 80 + hash(zone) % 30],
        "Demand": [90 + hash(zone) % 40, 70 + hash(zone) % 20]
    })
    df["Equilibrium"] = (df["Supply"] + df["Demand"]) / 2
    df["TOU_Price"] = df["Equilibrium"] * 0.12
    return df

# ---- Layout ----
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Specusol Solar Dashboard", className="text-center"), width=12),
        dbc.Col(html.P("Disclaimer: This website is for informational purposes only. "
                       "It does not constitute financial advice."), width=12)
    ]),
    dbc.Row([
        dbc.Col([
            html.H4("Texas Solar Map"),
            dl.Map(center=[31.0, -99.0], zoom=6, children=[
                dl.TileLayer(),
                dl.LayerGroup(id="weather-layer"),
                dl.MarkerClusterGroup(id="markers")
            ], style={'height': '600px', 'width': '100%'}, id="texas-map")
        ], width=6),
        dbc.Col([
            html.H4("Solar Supply-Demand Chart"),
            dcc.Graph(id="supply-demand-chart")
        ], width=6)
    ]),
    dbc.Row([
        dbc.Col([
            html.H4("Finances & Gemini AI Summary"),
            html.Div(id="finance-summary")
        ], width=12)
    ])
], fluid=True)

# ---- Callbacks ----

# Populate map markers for Texas zones
@app.callback(
    Output("markers", "children"),
    Input("texas-map", "id")  # Dummy input to trigger once
)
def add_markers(_):
    markers = []
    for zone, coords in TEXAS_ZONES.items():
        markers.append(dl.Marker(
            position=[coords["lat"], coords["lon"]],
            children=dl.Popup(html.Div(zone)),
            id=f"marker-{zone}"
        ))
    return markers

# Update chart and weather on map click
@app.callback(
    Output("supply-demand-chart", "figure"),
    Output("weather-layer", "children"),
    Input({"type": "marker", "index": ALL}, "n_clicks")
)
def update_chart(n_clicks_list):
    ctx = dash.callback_context
    if not ctx.triggered:
        zone = "Austin"
    else:
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        zone = triggered_id.replace("marker-", "")
    df = get_supply_demand(zone)

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Type"], y=df["Supply"], name="Supply"))
    fig.add_trace(go.Bar(x=df["Type"], y=df["Demand"], name="Demand"))
    fig.add_trace(go.Scatter(x=df["Type"], y=df["Equilibrium"], mode="lines+markers", name="Equilibrium"))
    fig.add_trace(go.Scatter(x=df["Type"], y=df["TOU_Price"], mode="lines+markers", name="TOU Price"))

    # Weather overlay
    coords = TEXAS_ZONES[zone]
    weather_layer = []
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={OPENWEATHER_KEY}&units=imperial"
        r = requests.get(url).json()
        temp = r["main"]["temp"]
        weather_layer.append(dl.Tooltip(f"{zone} Weather: {temp}°F", permanent=True, direction="right", offset=[20,0]))
    except:
        pass

    return fig, weather_layer

# Fetch Gemini AI summary and solar ETF price
@app.callback(
    Output("finance-summary", "children"),
    Input("supply-demand-chart", "figure")
)
def update_finances(_):
    summary = "Gemini AI not available"
    try:
        if GEMINI_API_KEY:
            openai.api_key = GEMINI_API_KEY
            prompt = "Summarize the current trends in the solar energy market."
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            summary = response.choices[0].message.content
    except:
        pass

    # Solar ETF price (example: TAN)
    try:
        tan = yf.Ticker("TAN")
        price = tan.history(period="1d")["Close"].iloc[-1]
    except:
        price = "N/A"

    return html.Div([
        html.P(f"Solar ETF (TAN) Price: ${price}"),
        html.P(f"Gemini AI Summary: {summary}")
    ])

# ---- Run Server ----
if __name__ == "__main__":
    app.run_server(debug=True)

