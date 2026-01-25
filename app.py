import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import dash_daq as daq
import dash_leaflet as dl
from dash.dependencies import Input, Output
import pandas as pd
import yfinance as yf
import openai
import os

# Load environment variables (ensure you set them on Render)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Data for the zones (simplified example, replace with real data)
data = {
    'ERCOT Zone 1': {
        'commercial_supply': [100, 150, 200, 250, 300, 350],
        'residential_supply': [80, 130, 170, 220, 270, 300],
        'commercial_demand': [110, 160, 210, 260, 310, 360],
        'residential_demand': [90, 140, 180, 230, 280, 310],
        'equilibrium': [105, 145, 185, 235, 285, 325],
        'tou_pricing': [0.12, 0.15, 0.18, 0.20, 0.22, 0.24],
    },
    'ERCOT Zone 2': {
        'commercial_supply': [120, 160, 210, 250, 300, 350],
        'residential_supply': [90, 140, 180, 230, 280, 320],
        'commercial_demand': [115, 165, 215, 255, 305, 355],
        'residential_demand': [95, 145, 185, 235, 285, 325],
        'equilibrium': [110, 150, 190, 240, 290, 330],
        'tou_pricing': [0.14, 0.17, 0.19, 0.21, 0.23, 0.25],
    }
}

app = dash.Dash(__name__)

app.layout = html.Div([
    # Header Section with Title and Disclaimer
    html.Header([
        html.H1("Specusol - Texas Solar Energy Hub", style={'text-align': 'center'}),
        html.P("All content is for informational purposes only. Specusol is not a financial advisor and does not provide investment advice.", style={'text-align': 'center', 'font-size': '12px', 'color': 'gray'}),
    ]),

    # Main Layout Section with Map on the left and Chart on the right
    html.Div([
        # Left column: Interactive Map (with Texas-focused view)
        html.Div([
            dl.Map([
                dl.TileLayer(),
                dl.LayerGroup(id="weather-layer"),
                dl.MarkerCluster([
                    dl.Marker(position=(31.0, -99.0), children=[
                        dl.Tooltip("ERCOT Zone 1")
                    ]),
                    dl.Marker(position=(30.0, -98.0), children=[
                        dl.Tooltip("ERCOT Zone 2")
                    ])
                ])
            ], id="map", center=(31.0, -99.0), zoom=6, style={'height': '500px'}),
        ], style={'display': 'inline-block', 'width': '50%'}),

        # Right column: Dynamic Chart with Supply & Demand Data
        html.Div([
            dcc.Graph(id='dynamic-chart'),
        ], style={'display': 'inline-block', 'width': '50%'}),
    ], style={'display': 'flex'}),

    # Footer Section with Financial Data (Stock and Gemini AI)
    html.Footer([
        html.Div([
            html.H3("Financial Insights", style={'text-align': 'center'}),
            dcc.Dropdown(id='stock-dropdown', options=[
                {'label': 'SPWR - SunPower Corp', 'value': 'SPWR'},
                {'label': 'FSLR - First Solar', 'value': 'FSLR'},
                {'label': 'SEDG - SolarEdge Technologies', 'value': 'SEDG'}
            ], value='SPWR', style={'width': '100%', 'margin-bottom': '20px'}),
            html.Div(id='stock-info', style={'text-align': 'center'}),
            html.Div(id='gemini-summary', style={'text-align': 'center', 'margin-top': '20px'}),
        ])
    ], style={'margin-top': '20px'})
])

# Update the chart when a map location is clicked
@app.callback(
    Output('dynamic-chart', 'figure'),
    [Input('map', 'click_feature')]
)
def update_chart(selected_zone):
    if not selected_zone:
        return go.Figure()

    zone = selected_zone['properties']['name']  # Get the zone name from map click

    # Get the zone data
    zone_data = data.get(zone)
    
    if zone_data:
        fig = go.Figure()

        # Add commercial supply and demand traces
        fig.add_trace(go.Scatter(x=list(range(len(zone_data['commercial_supply']))),
                                 y=zone_data['commercial_supply'], mode='lines', name='Commercial Supply'))
        fig.add_trace(go.Scatter(x=list(range(len(zone_data['commercial_demand']))),
                                 y=zone_data['commercial_demand'], mode='lines', name='Commercial Demand'))

        # Add residential supply and demand traces
        fig.add_trace(go.Scatter(x=list(range(len(zone_data['residential_supply']))),
                                 y=zone_data['residential_supply'], mode='lines', name='Residential Supply'))
        fig.add_trace(go.Scatter(x=list(range(len(zone_data['residential_demand']))),
                                 y=zone_data['residential_demand'], mode='lines', name='Residential Demand'))

        # Add equilibrium line
        fig.add_trace(go.Scatter(x=list(range(len(zone_data['equilibrium']))),
                                 y=zone_data['equilibrium'], mode='lines', name='Equilibrium'))

        # Add TOU pricing
        fig.add_trace(go.Scatter(x=list(range(len(zone_data['tou_pricing']))),
                                 y=zone_data['tou_pricing'], mode='lines', name='TOU Pricing', line=dict(color='orange')))

        fig.update_layout(
            title=f"Energy Supply & Demand for {zone}",
            xaxis_title="Time of Day",
            yaxis_title="kW / $/kWh"
        )

        return fig

    return go.Figure()


# Fetch the financial data when stock is selected
@app.callback(
    Output('stock-info', 'children'),
    [Input('stock-dropdown', 'value')]
)
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    stock_info = stock.history(period="5d")
    return html.Div([
        html.P(f"Latest Closing Price: ${stock_info['Close'].iloc[-1]:.2f}"),
        html.P(f"5-Day Price Change: ${stock_info['Close'].iloc[-1] - stock_info['Close'].iloc[0]:.2f}")
    ])

# Fetch the Gemini AI summary when requested
@app.callback(
    Output('gemini-summary', 'children'),
    [Input('stock-dropdown', 'value')]
)
def fetch_gemini_summary(ticker):
    prompt = f"Provide a detailed summary of the {ticker} stock, including its solar energy market impact."
    response = openai.Completion.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=200
    )
    return html.P(response['choices'][0]['text'].strip())


if __name__ == "__main__":
    app.run_server(debug=True)

