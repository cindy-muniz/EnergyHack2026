import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import requests
import openai

# Gemini AI key from Render env
openai.api_key = os.environ.get("GEMINI_API_KEY")

# Initialize app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Sample commercial/residential solar data
solar_data = pd.DataFrame({
    "Location": ["Austin", "Houston", "Dallas", "San Antonio"],
    "Commercial Supply": [50, 70, 65, 55],
    "Residential Supply": [40, 60, 55, 45],
    "Commercial Demand": [45, 65, 60, 50],
    "Residential Demand": [35, 50, 50, 40],
    "TOU Price": [0.12, 0.11, 0.13, 0.12]
})

# Homepage disclaimer
disclaimer = "⚠️ Specusol provides data for informational purposes only. Not financial advice."

# Layout
app.layout = dbc.Container([
    html.H1("Specusol - Texas Solar Market Dashboard"),
    html.Img(src="/assets/specusol_icon.png", height="60px"),
    html.P(disclaimer),
    dbc.Tabs([
        dbc.Tab(label="Map & Solar Chart", tab_id="map-chart"),
        dbc.Tab(label="Finances", tab_id="finances")
    ], id="tabs", active_tab="map-chart"),
    html.Div(id="tab-content")
], fluid=True)

# Helper: fetch weather overlay tiles
def get_weather_tile():
    return dl.TileLayer(url="https://tile.openweathermap.org/map/temp_new/{z}/{x}/{y}.png?appid=YOUR_OPENWEATHER_KEY")

# Tab content callback
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab")
)
def render_tab(tab):
    if tab == "map-chart":
        # Map centered on Texas
        map_component = dl.Map(center=[31.0, -100.0], zoom=6, style={"height": "600px"}, children=[
            dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            get_weather_tile(),
            dl.Marker(position=[30.2672, -97.7431], children=dl.Tooltip("Austin")),
            dl.Marker(position=[29.7604, -95.3698], children=dl.Tooltip("Houston")),
            dl.Marker(position=[32.7767, -96.797], children=dl.Tooltip("Dallas")),
            dl.Marker(position=[29.4241, -98.4936], children=dl.Tooltip("San Antonio")),
        ])

        chart_component = dcc.Graph(id="supply-demand-chart")

        return dbc.Row([
            dbc.Col(map_component, width=6),
            dbc.Col(chart_component, width=6)
        ])

    elif tab == "finances":
        # Solar ETF
        etf = yf.Ticker("TAN")  # Example solar ETF
        hist = etf.history(period="1mo")
        fig = go.Figure([go.Scatter(x=hist.index, y=hist["Close"], mode="lines")])
        fig.update_layout(title="TAN ETF - 1 Month")

        # Gemini AI Summary
        try:
            prompt = "Summarize the current trends in solar stocks in Texas."
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=200
            )
            summary = response.choices[0].text
        except Exception as e:
            summary = f"Could not fetch Gemini AI summary: {e}"

        return html.Div([
            dcc.Graph(figure=fig),
            html.H4("Gemini AI Summary"),
            html.P(summary)
        ])

# Callback: update chart when clicking map
@app.callback(
    Output("supply-demand-chart", "figure"),
    Input({"type": "marker", "index": dash.ALL}, "n_clicks")
)
def update_chart(n_clicks_list):
    ctx = dash.callback_context
    if not ctx.triggered or all(v is None for v in n_clicks_list):
        df = solar_data.iloc[0]  # Default
    else:
        # Get clicked location
        idx = ctx.triggered[0]["prop_id"].split(".")[0]
        loc_name = idx.split('"index":')[1].split("}")[0].strip('"')
        df = solar_data[solar_data["Location"] == loc_name].iloc[0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=["Commercial", "Residential"], y=[df["Commercial Supply"], df["Residential Supply"]],
        name="Supply", mode="lines+markers"
    ))
    fig.add_trace(go.Scatter(
        x=["Commercial", "Residential"], y=[df["Commercial Demand"], df["Residential Demand"]],
        name="Demand", mode="lines+markers"
    ))
    fig.add_trace(go.Scatter(
        x=["Commercial", "Residential"], y=[df["TOU Price"], df["TOU Price"]],
        name="TOU Price", mode="lines+markers", yaxis="y2"
    ))
    fig.update_layout(
        title=f"Solar Supply & Demand - {df['Location']}",
        yaxis=dict(title="MW"),
        yaxis2=dict(title="TOU Price ($/kWh)", overlaying="y", side="right")
    )
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
nviron.get("PORT", 10000)))
