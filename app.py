import os
import pandas as pd
import yfinance as yf
import requests
from dash import Dash, dcc, html, Output, Input
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
import openai

# --------------------------
# Setup
# --------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Load environment variable for Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
openai.api_key = GEMINI_API_KEY

# Example placeholder data for commercial/residential solar supply-demand
# You would replace this with your real dataset
data = pd.DataFrame({
    "location": ["Austin", "Dallas", "Houston", "San Antonio"],
    "commercial_supply": [200, 180, 220, 150],
    "residential_supply": [120, 110, 150, 100],
    "demand": [250, 210, 300, 180],
    "TOU_price": [0.12, 0.11, 0.13, 0.10]
})

# Texas Map center
texas_center = [31.0, -99.0]

# --------------------------
# Layout
# --------------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Specusol 🌞 Solar Analytics", className="text-center"), width=12)
    ]),
    dbc.Row([
        dbc.Col([
            html.H5("Texas Solar Map"),
            dl.Map(center=texas_center, zoom=6, id="map", style={'width': '100%', 'height': '600px'},
                   children=[
                       dl.TileLayer(),
                       dl.LayerGroup(id="marker-layer")
                   ])
        ], width=6),
        dbc.Col([
            html.H5("Dynamic Supply-Demand Chart"),
            dcc.Graph(id="supply-demand-chart")
        ], width=6)
    ]),
    dbc.Row([
        dbc.Col([
            html.H5("Finances"),
            dcc.Graph(id="solar-etf-chart"),
            html.Div(id="gemini-summary", className="mt-3")
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col([
            html.P("Disclaimer: This website is for informational purposes only. Not financial advice.", 
                   className="text-muted mt-4")
        ], width=12)
    ])
], fluid=True)

# --------------------------
# Callbacks
# --------------------------
@app.callback(
    Output("supply-demand-chart", "figure"),
    Input("map", "click_lat_lng")
)
def update_chart(click_lat_lng):
    # Default to Austin if no click
    location = "Austin"
    if click_lat_lng:
        # Simple nearest-location matching
        lat, lng = click_lat_lng
        distances = ((data["location"].map(lambda x: x.lower()) - location.lower())**2).fillna(0)
        # Fallback to first location
        location = data["location"].iloc[0]

    row = data[data["location"] == location].iloc[0]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Commercial Supply", x=["Supply"], y=[row["commercial_supply"]]))
    fig.add_trace(go.Bar(name="Residential Supply", x=["Supply"], y=[row["residential_supply"]]))
    fig.add_trace(go.Scatter(name="Demand", x=["Supply"], y=[row["demand"]], mode="lines+markers"))
    fig.update_layout(title=f"{location} Solar Supply & Demand", barmode='group', yaxis_title="MW")
    return fig

@app.callback(
    Output("solar-etf-chart", "figure"),
    Input("solar-etf-chart", "id")
)
def update_etf_chart(_):
    etf = yf.Ticker("TAN")  # Example Solar ETF
    hist = etf.history(period="1y")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="TAN ETF"))
    fig.update_layout(title="Solar ETF (TAN) Price", yaxis_title="USD")
    return fig

@app.callback(
    Output("gemini-summary", "children"),
    Input("gemini-summary", "id")
)
def fetch_gemini_summary(_):
    if not GEMINI_API_KEY:
        return "Gemini AI key not set."
    try:
        prompt = "Summarize the Texas solar market and recent trends in 3 bullet points."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        summary = response.choices[0].message.content
        return html.Ul([html.Li(line) for line in summary.split("\n") if line.strip()])
    except Exception as e:
        return f"Error fetching Gemini summary: {e}"

# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    app.run_server(debug=True)


