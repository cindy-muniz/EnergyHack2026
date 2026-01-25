import dash
from dash import html, dcc
import dash_leaflet as dl
import pandas as pd
import yfinance as yf
from dash.dependencies import Output, Input
import datetime

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # for Render deployment

# Function to get data (example: Yahoo Finance)
def get_data(ticker="AAPL"):
    df = yf.download(ticker, period="1d", interval="1h")
    df.reset_index(inplace=True)
    return df

# Layout
app.layout = html.Div([
    html.H1("Hourly Stock Dashboard"),
    dcc.Dropdown(
        id="ticker-dropdown",
        options=[
            {"label": "Apple", "value": "AAPL"},
            {"label": "Microsoft", "value": "MSFT"},
            {"label": "Tesla", "value": "TSLA"}
        ],
        value="AAPL"
    ),
    dcc.Graph(id="stock-chart"),
    html.Div(id="last-updated"),
    dl.Map(
        center=[37.7749, -122.4194],  # example center (San Francisco)
        zoom=10,
        children=[dl.TileLayer()]
    ),
    # Interval for hourly updates
    dcc.Interval(
        id="interval-component",
        interval=3600*1000,  # 1 hour in milliseconds
        n_intervals=0
    )
])

# Callback to update chart and timestamp
@app.callback(
    Output("stock-chart", "figure"),
    Output("last-updated", "children"),
    Input("ticker-dropdown", "value"),
    Input("interval-component", "n_intervals")
)
def update_chart(ticker, n):
    df = get_data(ticker)
    fig = {
        "data": [{"x": df["Datetime"], "y": df["Close"], "type": "line", "name": ticker}],
        "layout": {"title": f"{ticker} Hourly Prices"}
    }
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return fig, f"Last updated: {timestamp}"

# Run locally
if __name__ == "__main__":
    app.run_server(debug=True)

