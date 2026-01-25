import os
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from dash import Dash, html, dcc, Input, Output
import dash_leaflet as dl
import plotly.graph_objs as go
import genai

# -----------------------------
# DASH APP INIT
# -----------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # for Render

# -----------------------------
# ICON
# -----------------------------
ICON_URL = "https://image2url.com/r2/default/images/1769310659997-df25a758-c435-4795-bd4a-314cd27bf886.png"

# -----------------------------
# PAGES
# -----------------------------

# Homepage layout
home_layout = html.Div([
    html.Img(src=ICON_URL, style={'height': '100px'}),
    html.H1("Specusol: Texas Solar Market Simulator"),
    html.P("Specusol is an information service. Information is for educational purposes only and is not intended to be used as investment advice."),
    html.H3("About This Website"),
    html.P("This simulator allows users to view Texas solar market data, weather, ERCOT zones, and perform paper trading on a Solar Stocks ETF with AI-driven insights and price predictions."),
    html.Br(),
    html.A("Go to Charts", href="/charts"),
    html.Br(),
    html.A("Go to Finance Simulator", href="/finance")
])

# Charts + Map page layout
charts_layout = html.Div([
    html.H2("Texas Solar Market Overview"),
    html.Div([
        dcc.Graph(id="solar-chart"),
        dl.Map(style={'width': '60vw', 'height': '60vh'}, center=[31.0, -100.0], zoom=5, children=[
            dl.TileLayer(),
            # ERCOT zone polygons or markers can be added here
        ])
    ]),
    html.Br(),
    html.A("Go Home", href="/"),
    html.Br(),
    html.A("Go to Finance Simulator", href="/finance")
])

# Finance page layout
finance_layout = html.Div([
    html.H2("Solar Stocks ETF Simulator"),
    html.Div(id="finance-summary"),
    html.Br(),
    html.A("Go Home", href="/"),
    html.Br(),
    html.A("Go to Charts", href="/charts")
])

# -----------------------------
# PRICE PREDICTION FUNCTIONS
# -----------------------------
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
    upper = sma + 2 * std
    lower = sma - 2 * std
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
        score += 1
        reasons.append("RSI oversold")
    elif latest.rsi > 70:
        score -= 1
        reasons.append("RSI overbought")
    # Bollinger Bands
    if latest.close < latest.bb_lower:
        score += 1
        reasons.append("Below lower Bollinger band")
    elif latest.close > latest.bb_upper:
        score -= 1
        reasons.append("Above upper Bollinger band")
    # MACD
    if latest.macd > latest.macd_signal:
        score += 1
        reasons.append("MACD bullish crossover")
    else:
        score -= 1
        reasons.append("MACD bearish crossover")
    # EMA Trend
    if latest.ema_fast > latest.ema_slow:
        score += 1
        reasons.append("Short-term uptrend")
    else:
        score -= 1
        reasons.append("Short-term downtrend")
    # Price velocity
    velocity = close.diff().iloc[-1]
    if velocity > 0:
        score += 0.5
        reasons.append("Positive price velocity")
    else:
        score -= 0.5
        reasons.append("Negative price velocity")
    # Volatility
    volatility = close.pct_change().rolling(10).std().iloc[-1]
    if volatility > 0.15:
        score *= 0.7
        reasons.append("High volatility → reduced confidence")
    # Final
    if score >= 2:
        direction = "Up"
    elif score <= -2:
        direction = "Down"
    else:
        direction = "Flat"
    confidence = min(abs(score) / 6, 1.0)
    return {"direction": direction, "confidence": round(confidence, 2), "score": round(score, 2), "reasons": reasons}

# -----------------------------
# GEMINI AI CLIENT
# -----------------------------
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_KEY)

def get_gemini_summary(locale="Austin, TX"):
    prompt = f"""
    Act as: A Senior ERCOT Market Analyst and Energy Broker Advisor.
    Task: Provide a concise market outlook for solar energy in a specific Texas locale.
    Locale: {locale}
    Analysis Framework: Use the following 4 solar indicators to evaluate the outlook for 2026:
    Resource Potential, Grid Congestion & Basis Risk, Load Growth Drivers, Ancillary Services & Storage.
    Output Format:
    Market Sentiment, Broker Summary (3 sentences), Key Risk Factor, Pro Tip.
    """
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )
    return response.text

# -----------------------------
# CALLBACKS
# -----------------------------
@app.callback(
    Output("finance-summary", "children"),
    Input("finance-summary", "id")  # trigger once page loads
)
def update_finance_summary(_):
    try:
        summary = get_gemini_summary()
    except Exception:
        summary = "AI summary not available."
    # Get Solar ETF price prediction
    etf = yf.download("TAN", period="1mo", interval="1h")  # Hourly data
    etf.reset_index(inplace=True)
    etf.rename(columns={"Close": "close"}, inplace=True)
    prediction = predict_price_direction(etf)
    return html.Div([
        html.P(summary),
        html.H4("Price Prediction for Solar ETF (TAN)"),
        html.P(f"Direction: {prediction['direction']}"),
        html.P(f"Confidence: {prediction['confidence']}"),
        html.P("Reasons: " + ", ".join(prediction["reasons"]))
    ])

# -----------------------------
# URL ROUTING
# -----------------------------
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/charts":
        return charts_layout
    elif pathname == "/finance":
        return finance_layout
    else:
        return home_layout

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run_server(debug=True)

