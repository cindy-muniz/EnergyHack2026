import os
import requests
import pandas as pd
import yfinance as yf
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, ctx
from geopy.geocoders import Nominatim
from datetime import datetime

# Initialize
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME])
server = app.server
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
geolocator = Nominatim(user_agent="specusol_v2")

# --- CUSTOM STYLING ---
CARD_STYLE = {"padding": "20px", "borderRadius": "15px", "backgroundColor": "#111", "border": "1px solid #333"}

app.layout = dbc.Container(fluid=True, className="p-4", children=[
    # Header Section
    dbc.Row([
        dbc.Col([
            html.H1([html.I(className="fas fa-sun me-2", style={"color": "#FFD700"}), "SPECUSOL 2.0"], className="display-4 fw-bold"),
            html.P("Texas ERCOT Market Intelligence & Solar Forecasting", className="text-muted")
        ], width=8),
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="zip-input", placeholder="Enter Zip Code (e.g. 78701)", type="text"),
                dbc.Button("ANALYZE", id="zip-btn", color="warning", className="fw-bold"),
            ])
        ], width=4, className="align-self-center")
    ], className="mb-4"),

    # Main Grid
    dbc.Row([
        # Left: Map & Search
        dbc.Col([
            html.Div(id="map-container", children=[
                dl.Map(center=[31.0, -99.0], zoom=6, style={"height": "450px", "borderRadius": "15px"}, id="texas-map", children=[
                    dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
                    dl.LayerGroup(id="marker-layer")
                ])
            ], style=CARD_STYLE)
        ], width=5),

        # Right: Live Supply Forecast
        dbc.Col([
            html.Div(dcc.Graph(id="live-supply-curve"), style=CARD_STYLE)
        ], width=7)
    ], className="mb-4"),

    dbc.Row([
        # Market Candlestick
        dbc.Col([
            html.Div([
                html.H5("ERCOT Solar Market Volatility (Hourly)", className="text-warning mb-3"),
                dcc.Graph(id="market-candlestick")
            ], style=CARD_STYLE)
        ], width=8),

        # ETF & AI Insights
        dbc.Col([
            html.Div([
                html.H5("Solar ETF (TAN)", className="text-info"),
                dcc.Graph(id="solar-etf-mini", style={"height": "200px"}),
                html.Hr(style={"borderColor": "#444"}),
                html.H6("AI Market Outlook", className="text-warning"),
                dcc.Loading(html.Div(id="gemini-summary", className="small text-muted"))
            ], style=CARD_STYLE)
        ], width=4)
    ])
])

# --- CALLBACKS ---

@app.callback(
    [Output("texas-map", "center"), Output("texas-map", "zoom"), Output("marker-layer", "children")],
    Input("zip-btn", "n_clicks"),
    State("zip-input", "value"),
    prevent_initial_call=True
)
def handle_zip(n, zip_code):
    if not zip_code: return [31.0, -99.0], 6, []
    try:
        loc = geolocator.geocode(f"{zip_code}, Texas")
        if loc:
            marker = dl.Marker(position=[loc.latitude, loc.longitude], children=dl.Tooltip(f"Zip: {zip_code}"))
            return [loc.latitude, loc.longitude], 11, [marker]
    except: pass
    return [31.0, -99.0], 6, []

@app.callback(
    [Output("live-supply-curve", "figure"), Output("market-candlestick", "figure")],
    Input("texas-map", "center")
)
def update_charts(center):
    lat, lon = center
    # 1. Supply Curve Logic
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=shortwave_radiation&timezone=auto"
    r = requests.get(url).json()
    df = pd.DataFrame({'time': pd.to_datetime(r['hourly']['time']), 'ghi': r['hourly']['shortwave_radiation']})
    df['supply'] = (df['ghi'] * 60000 * 0.18) / 1000 # kW Conversion

    fig_supply = go.Figure(go.Scatter(x=df['time'], y=df['supply'], fill='tozeroy', line=dict(color='#FFD700', width=3)))
    fig_supply.update_layout(title="Predicted Solar Supply (kW)", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=40, b=10))

    # 2. Candlestick logic (Simulated Market Movement)
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df['time'][:24],
        open=df['supply'][:24]*1.1, high=df['supply'][:24]*1.3,
        low=df['supply'][:24]*0.8, close=df['supply'][:24],
        increasing_line_color='#00ff9d', decreasing_line_color='#ff3d3d'
    )])
    fig_candle.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    
    return fig_supply, fig_candle

@app.callback(Output("solar-etf-mini", "figure"), Input("zip-btn", "n_clicks"))
def update_etf(_):
    data = yf.download("TAN", period="1mo")
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    fig = go.Figure(go.Scatter(x=data.index, y=data['Close'], line=dict(color='#00d4ff')))
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0))
    return fig

@app.callback(Output("gemini-summary", "children"), Input("texas-map", "center"))
def ai_report(center):
    if not GEMINI_API_KEY: return "Key missing."
    prompt = f"Summarize solar market at {center} for 2026. 2 sentences."
    try:
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}", 
                          json={"contents": [{"parts": [{"text": prompt}]}]})
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "AI currently busy."

if __name__ == "__main__":
    app.run_server(debug=True)
