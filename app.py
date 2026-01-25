# ------------------------------
# Specusol App (Complete)
# ------------------------------
import dash
from dash import Dash, html, dcc, Input, Output
import dash_leaflet as dl
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import yfinance as yf
import genai

# ------------------------------
# Gemini AI client
# ------------------------------
gemini_client = genai.Client(api_key="AIzaSyBFbTd_exi5T7ezqYitEYPWTZNL_uwBz-C")

# ------------------------------
# Constants
# ------------------------------
SOLAR_API_KEY = "xrKsemxjKJqoObOC1IDEvt4qNFbMQQy79pFqGWKF"

# ERCOT zones polygons (example simplified)
ercot_zones = {
    "North": [[33.7,-98],[36.5,-98],[36.5,-94],[33.7,-94]],
    "South": [[25.8,-106],[29.5,-106],[29.5,-95],[25.8,-95]]
}

# Texas bounding box center
texas_center = [31.0, -99.0]

# ------------------------------
# Dash App Setup
# ------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# ------------------------------
# Price Prediction Algorithm
# ------------------------------
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(period).mean() / loss.rolling(period).mean()
    return 100 - (100 / (1 + rs))

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def macd(series):
    ema12 = ema(series, 12)
    ema26 = ema(series, 26)
    macd_line = ema12 - ema26
    signal = ema(macd_line, 9)
    return macd_line, signal

def bollinger(series, period=20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + 2*std
    lower = sma - 2*std
    return upper, sma, lower

def predict_price_direction(df):
    close = df["close"]
    df["rsi"] = rsi(close)
    df["ema_fast"] = ema(close, 5)
    df["ema_slow"] = ema(close, 15)
    df["macd"], df["macd_signal"] = macd(close)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger(close)
    latest = df.iloc[-1]
    score = 0
    reasons = []
    # RSI
    if latest.rsi < 30:
        score += 1; reasons.append("RSI oversold")
    elif latest.rsi > 70:
        score -= 1; reasons.append("RSI overbought")
    # Bollinger Bands
    if latest.close < latest.bb_lower:
        score += 1; reasons.append("Below lower Bollinger band")
    elif latest.close > latest.bb_upper:
        score -= 1; reasons.append("Above upper Bollinger band")
    # MACD
    if latest.macd > latest.macd_signal:
        score +=1; reasons.append("MACD bullish crossover")
    else:
        score -=1; reasons.append("MACD bearish crossover")
    # EMA Trend
    if latest.ema_fast > latest.ema_slow:
        score +=1; reasons.append("Short-term uptrend")
    else:
        score -=1; reasons.append("Short-term downtrend")
    # Velocity
    velocity = close.diff().iloc[-1]
    score += 0.5 if velocity>0 else -0.5
    # Volatility
    volatility = close.pct_change().rolling(10).std().iloc[-1]
    if volatility>0.15: score *=0.7; reasons.append("High volatility → reduced confidence")
    # Decision
    direction = "Up" if score>=2 else "Down" if score<=-2 else "Flat"
    confidence = min(abs(score)/6,1.0)
    return {"direction":direction,"confidence":round(confidence,2),"score":round(score,2),"reasons":reasons}

# ------------------------------
# Helper: Solar Supply + Demand
# ------------------------------
def get_solar_supply(lat, lon):
    timestamps = pd.date_range(datetime.now(), periods=24, freq='h')
    ghi = np.random.uniform(0,800,len(timestamps))
    cloudcover = np.random.uniform(0,100,len(timestamps))
    temp = np.random.uniform(10,40,len(timestamps))
    df = pd.DataFrame({
        "timestamp": timestamps,
        "ghi": ghi,
        "cloudcover": cloudcover,
        "temp": temp
    })
    cloud_factor = 1 - df.cloudcover/100
    temp_factor = 1 - 0.004*(df.temp - 25)
    res_area = 10000; comm_area=50000; eff=0.18; pr=0.75
    df["res_supply"] = df.ghi*cloud_factor*temp_factor*(res_area*eff/1000)
    df["comm_supply"] = df.ghi*cloud_factor*temp_factor*(comm_area*eff*pr/1000)
    df["demand"] = df.res_supply + df.comm_supply + np.random.uniform(-50,50,len(df))
    df["equilibrium"] = (df.res_supply + df.comm_supply + df.demand)/3
    return df

# ------------------------------
# Build Figure
# ------------------------------
def build_figure(lat, lon):
    df = get_solar_supply(lat, lon)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply, name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_supply, name="Commercial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.demand, name="Demand", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.equilibrium, name="Equilibrium", line=dict(color="green", dash="dash")))
    fig.update_layout(title="Texas Solar Supply & Demand", xaxis_title="Time", yaxis_title="kW")
    return fig

# ------------------------------
# Layout: Map + Chart Page
# ------------------------------
chart_map_page = html.Div([
    html.H3("Texas Solar Supply & Demand Simulator"),
    html.Div([
        dcc.Graph(id="solar-chart", figure=build_figure(31.0,-99.0), style={"width":"65%","display":"inline-block"}),
        dl.Map(center=texas_center, zoom=5, children=[
            dl.TileLayer(),
            dl.LayerGroup(id="zone-layer")
        ], id="texas-map", style={"width":"33%","height":"600px","display":"inline-block"})
    ]),
    html.Br(),
    dcc.Link("Home", href="/"),
    html.Br(),
    dcc.Link("Finance/Trading", href="/finance")
])

# ------------------------------
# Finance Page
# ------------------------------
finance_page = html.Div([
    html.H3("Solar ETF Paper Trading & AI Market Outlook"),
    html.Div(id="ai-analysis", style={"marginBottom":"20px"}),
    html.Div(id="etf-chart"),
    dcc.Input(id="finance-location", type="text", placeholder="Enter TX City/ZIP", value="Austin, TX"),
    html.Br(),
    dcc.Link("Home", href="/"),
    html.Br(),
    dcc.Link("Chart & Map", href="/chart-map")
])

# ------------------------------
# Homepage
# ------------------------------
homepage = html.Div([
    html.H2("Welcome to Specusol"),
    html.Div(id="homepage-summary"),
    html.Br(),
    html.P("Disclaimer: Specusol is an information service. Information is for educational purposes only and is not intended to be used as investment advice."),
    html.Br(),
    dcc.Link("Chart & Map", href="/chart-map"),
    html.Br(),
    dcc.Link("Finance & Trading", href="/finance")
])

# ------------------------------
# App Layout: Multi-Page
# ------------------------------
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# ------------------------------
# Callbacks
# ------------------------------
@app.callback(Output("page-content", "children"),
              Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/chart-map":
        return chart_map_page
    elif pathname == "/finance":
        return finance_page
    else:
        return homepage

# Homepage AI summary
@app.callback(Output("homepage-summary","children"),
              Input("url","pathname"))
def homepage_summary(pathname):
    if pathname=="/":
        prompt = """
Act as: A Senior Solar Energy Analyst.
Task: Generate a concise 3-sentence summary explaining what the Specusol simulator demonstrates on the website.
Focus on: Texas solar market, supply & demand charts, ERCOT zones, weather overlays, and solar ETF finance page.
"""
        response = gemini_client.models.generate_content(model="gemini-flash-lite-latest", contents=prompt)
        return html.P(response.text)
    return ""

# Finance AI + ETF callback
@app.callback([Output("ai-analysis","children"), Output("etf-chart","children")],
              Input("finance-location","value"))
def update_finance(location):
    # --- Gemini AI Market Outlook ---
    prompt = f"""
Act as: A Senior ERCOT Market Analyst and Energy Broker Advisor.
Task: Provide a concise market outlook for solar energy in a specific Texas locale.
Locale: {location}
Analysis Framework: Use 4 solar indicators for 2026 (Resource Potential, Grid Congestion & Basis Risk, Load Growth Drivers, Ancillary Services & Storage)
Output Format:
Market Sentiment: (Bullish / Neutral / Bearish)
Broker Summary: 3-sentence elevator pitch
Key Risk Factor: The #1 thing that could kill ROI
Pro Tip: 1 piece of advice regarding 30% ITC phaseout or ERCOT ECRS
"""
    ai_response = gemini_client.models.generate_content(model="gemini-flash-lite-latest", contents=prompt)
    # --- Yahoo Finance ETF ---
    etf = yf.download("TAN", period="1mo", interval="1d")  # Example solar ETF
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=etf.index, y=etf["Close"], name="TAN ETF", line=dict(color="purple")))
    fig.update_layout(title=f"{location} Solar ETF Price", xaxis_title="Date", yaxis_title="Price USD")
    return html.Div([html.H4("AI Market Outlook"), html.P(ai_response.text)]), dcc.Graph(figure=fig)

# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

