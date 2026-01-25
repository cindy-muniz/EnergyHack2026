import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

import dash
from dash import html, dcc, Input, Output, State
import dash_leaflet as dl
import plotly.graph_objects as go
import genai

# ------------------------------
# Gemini AI Client
# ------------------------------
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=gemini_api_key)

def get_gemini_summary(city_or_zip):
    prompt = f"""
    Act as: A Senior ERCOT Market Analyst and Energy Broker Advisor.
    Task: Provide a concise market outlook for solar energy in a specific Texas locale.
    Locale: {city_or_zip}
    Analysis Framework: Use 4 solar indicators: Resource Potential, Grid Congestion & Basis Risk, Load Growth Drivers, Ancillary Services & Storage.
    Output Format:
    Market Sentiment, Broker Summary, Key Risk Factor, Pro Tip.
    """
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )
    return response.text

# ------------------------------
# Solar Supply/Demand Simulation
# ------------------------------
def get_solar_supply(lat, lon):
    timestamps = pd.date_range(datetime.now(), periods=48, freq='h')
    ghi = np.random.uniform(0, 1000, size=len(timestamps))
    temp = np.random.uniform(20, 35, size=len(timestamps))

    cloud_factor = 1 - np.random.uniform(0, 1, size=len(timestamps)) * 0.5
    temp_factor = 1 - 0.004 * (temp - 25)

    res_area, comm_area = 10000, 50000
    eff, pr = 0.18, 0.75

    df = pd.DataFrame({
        'timestamp': timestamps,
        'res_supply': ghi * cloud_factor * temp_factor * (res_area * eff / 1000),
        'comm_supply': ghi * cloud_factor * temp_factor * (comm_area * eff * pr / 1000)
    })
    df['demand'] = df['res_supply'] + df['comm_supply'] * np.random.uniform(0.8,1.2)
    df['equilibrium'] = (df['res_supply'] + df['comm_supply']) / 2
    return df

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
    signal = ema(ema12 - ema26, 9)
    return ema12 - ema26, signal

def bollinger(series, period=20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return upper, sma, lower

def predict_price_direction(df):
    close = df['close']
    df["rsi"] = rsi(close)
    df["ema_fast"] = ema(close, 5)
    df["ema_slow"] = ema(close, 15)
    df["macd"], df["macd_signal"] = macd(close)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger(close)
    latest = df.iloc[-1]
    score, reasons = 0, []
    if latest.rsi < 30: score+=1; reasons.append("RSI oversold")
    elif latest.rsi > 70: score-=1; reasons.append("RSI overbought")
    if latest.close < latest.bb_lower: score+=1; reasons.append("Below lower Bollinger band")
    elif latest.close > latest.bb_upper: score-=1; reasons.append("Above upper Bollinger band")
    if latest.macd > latest.macd_signal: score+=1; reasons.append("MACD bullish crossover")
    else: score-=1; reasons.append("MACD bearish crossover")
    if latest.ema_fast > latest.ema_slow: score+=1; reasons.append("Short-term uptrend")
    else: score-=1; reasons.append("Short-term downtrend")
    velocity = close.diff().iloc[-1]
    score += 0.5 if velocity>0 else -0.5
    reasons.append("Positive price velocity" if velocity>0 else "Negative price velocity")
    volatility = close.pct_change().rolling(10).std().iloc[-1]
    if volatility > 0.15: score *= 0.7; reasons.append("High volatility → reduced confidence")
    direction = "Up" if score>=2 else ("Down" if score<=-2 else "Flat")
    confidence = min(abs(score)/6, 1.0)
    return {"direction": direction, "confidence": round(confidence,2), "score": round(score,2), "reasons": reasons}

# ------------------------------
# Dash App
# ------------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# ------------------------------
# Layout
# ------------------------------
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# ------------------------------
# Homepage
# ------------------------------
home_layout = html.Div([
    html.H1("Specusol - Texas Solar Market Simulator"),
    html.Img(src="https://image2url.com/r2/default/images/1769310659997-df25a758-c435-4795-bd4a-314cd27bf886.png",
             style={'width':'150px'}),
    html.P("Specusol is an information service. Information is for educational purposes only and is not intended to be used as investment advice."),
    html.P("This simulator demonstrates solar supply, demand, weather, ERCOT zones, and Texas solar market outlook with solar ETF paper trading."),
    html.Br(),
    html.A("Go to Chart & Map", href="/chart"),
    html.Br(),
    html.A("Go to Finance Simulator", href="/finance")
])

# ------------------------------
# Chart + Map Page
# ------------------------------
chart_layout = html.Div([
    html.Div([
        dcc.Graph(id='solar-chart')
    ], style={'width':'65%', 'display':'inline-block'}),
    html.Div([
        dl.Map(id="map", center=[31.0,-99.0], zoom=6, children=[
            dl.TileLayer(),
        ], style={'width':'100%', 'height':'500px'})
    ], style={'width':'34%', 'display':'inline-block'}),
    dcc.Store(id='coords', data={"lat": 30.26, "lon": -97.74})
])

# ------------------------------
# Finance Page
# ------------------------------
finance_layout = html.Div([
    html.H2("Solar ETF Paper Trading & Market Analysis"),
    html.Div(id='gemini-summary'),
    dcc.Graph(id='etf-chart')
])

# ------------------------------
# Callbacks
# ------------------------------
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == "/chart":
        return chart_layout
    elif pathname == "/finance":
        return finance_layout
    return home_layout

@app.callback(
    Output('solar-chart', 'figure'),
    Output('coords', 'data'),
    Input('map', 'click_lat_lng'),
    State('coords', 'data')
)
def update_chart(latlng, coords):
    if latlng:
        lat, lon = latlng
    else:
        lat, lon = coords['lat'], coords['lon']
    df = get_solar_supply(lat, lon)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply, name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_supply, name="Commercial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.demand, name="Demand", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.equilibrium, name="Equilibrium", line=dict(color="green", dash='dash')))
    fig.update_layout(title=f"Solar Supply & Demand at {lat:.2f},{lon:.2f}", xaxis_title="Time", yaxis_title="kW", template="plotly_white")
    return fig, {"lat": lat, "lon": lon}

@app.callback(
    Output('etf-chart', 'figure'),
    Output('gemini-summary', 'children'),
    Input('coords', 'data')
)
def update_finance(coords):
    # Fetch ETF data
    ticker = "TAN"  # Example solar ETF
    etf = yf.Ticker(ticker)
    hist = etf.history(period="1mo", interval="1h")
    hist.reset_index(inplace=True)
    prediction = predict_price_direction(pd.DataFrame({"close": hist["Close"]}))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist['Datetime'], y=hist['Close'], name=ticker, line=dict(color="blue")))
    gemini_text = get_gemini_summary(f"{coords['lat']},{coords['lon']}")
    return fig, gemini_text

# ------------------------------
# Run server
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

