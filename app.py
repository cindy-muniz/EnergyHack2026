import dash
from dash import html, dcc
import dash_leaflet as dl
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
from dash.dependencies import Input, Output

# Initialize app
app = dash.Dash(__name__)
server = app.server  # for Render deployment

# Sample chart data function (updates hourly)
def fetch_stock_data(ticker="AAPL"):
    df = yf.download(ticker, period="7d", interval="1h")
    df.reset_index(inplace=True)
    return df

# Generate initial chart
df = fetch_stock_data()
fig = px.line(df, x="Datetime", y="Close", title="AAPL Hourly Price")

# Homepage layout
app.layout = html.Div([
    html.H1("Specusol Dashboard"),
    html.P("Specusol is an information service. Information is for educational purposes only and is not intended to be used as investment advice."),
    html.P("This website provides hourly updated stock charts and data."),
    
    dcc.Graph(id="stock-chart", figure=fig),

    html.H2("Interactive Map"),
    dl.Map(style={'width': '100%', 'height': '500px'}, center=[37.7749, -122.4194], zoom=10, children=[
        dl.TileLayer()
    ]),

    dcc.Interval(
        id="interval-update",
        interval=3600*1000,  # 1 hour in milliseconds
        n_intervals=0
    )
])

# Callback to update chart every hour
@app.callback(
    Output("stock-chart", "figure"),
    Input("interval-update", "n_intervals")
)
def update_chart(n):
    df = fetch_stock_data()
    fig = px.line(df, x="Datetime", y="Close", title="AAPL Hourly Price")
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
