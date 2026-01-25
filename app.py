import os
import requests
import yfinance as yf
from dash import Dash, html, dcc, Input, Output, ctx, ALL
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Add as many locations as you want here; the UI will update automatically
SOLAR_DATA = {
    "Austin": {"lat": 30.27, "lon": -97.74, "commercial": 220, "residential": 160, "demand": 300, "tou": 0.14},
    "Dallas": {"lat": 32.77, "lon": -96.79, "commercial": 200, "residential": 140, "demand": 280, "tou": 0.13},
    "Houston": {"lat": 29.76, "lon": -95.37, "commercial": 260, "residential": 180, "demand": 340, "tou": 0.15},
    "San Antonio": {"lat": 29.42, "lon": -98.49, "commercial": 210, "residential": 150, "demand": 310, "tou": 0.12},
    "El Paso": {"lat": 31.76, "lon": -106.48, "commercial": 300, "residential": 200, "demand": 250, "tou": 0.11}
}

app.layout = dbc.Container(fluid=True, children=[
    html.H1("Specusol ☀️ Texas Solar Market Simulator", className="text-center my-3"),
    dbc.Row([
        dbc.Col([
            dl.Map(center=[31.0, -99.0], zoom=6, style={"height": "600px"}, children=[
                dl.TileLayer(),
                dl.LayerGroup([
                    dl.Marker(
                        position=[v["lat"], v["lon"]],
                        children=dl.Tooltip(k),
                        # Use 'index' for pattern matching
                        id={"type": "city-marker", "index": k} 
                    ) for k, v in SOLAR_DATA.items()
                ])
            ])
        ], width=6),
        dbc.Col([dcc.Graph(id="supply-demand-chart")], width=6)
    ]),
    html.Hr(),
    dbc.Row([dbc.Col([dcc.Graph(id="solar-etf")], width=12)]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H4("Gemini AI – ERCOT Market Outlook"),
            dcc.Loading(html.Div(id="gemini-summary", className="p-3 border"))
        ])
    ])
])

# FIX 3: Pattern-Matching Callback for dynamic locations
@app.callback(
    Output("supply-demand-chart", "figure"),
    Input({"type": "city-marker", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def update_chart(n_clicks):
    # Use dash.ctx to find exactly which marker was clicked
    triggered_id = ctx.triggered_id
    if not triggered_id:
        return go.Figure()

    city_name = triggered_id['index']
    d = SOLAR_DATA[city_name]

    fig = go.Figure()
    fig.add_bar(name="Commercial Supply", x=["Solar Metrics"], y=[d["commercial"]])
    fig.add_bar(name="Residential Supply", x=["Solar Metrics"], y=[d["residential"]])
    fig.add_scatter(name="Demand", x=["Solar Metrics"], y=[d["demand"]], mode="lines+markers")

    fig.update_layout(
        title=f"{city_name} Solar Market (TOU ${d['tou']}/kWh)",
        barmode="group", yaxis_title="MW"
    )
    return fig

# FIX 2: Handling yfinance MultiIndex
@app.callback(Output("solar-etf", "figure"), Input("solar-etf", "id"))
def load_etf(_):
    data = yf.download("TAN", period="1y")
    if data.empty:
        return go.Figure().update_layout(title="Data Unavailable")
    
    # Flatten MultiIndex if it exists (Price/Ticker levels)
    if isinstance(data.columns, dcc.pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    fig = go.Figure()
    fig.add_scatter(x=data.index, y=data["Close"], mode="lines")
    fig.update_layout(title="Solar ETF (TAN) - Last 12 Months", xaxis_title="Date", yaxis_title="Price (USD)")
    return fig

# FIX 1: Robust Gemini JSON parsing
@app.callback(Output("gemini-summary", "children"), Input("gemini-summary", "id"))
def gemini_summary(_):
    if not GEMINI_API_KEY:
        return "Gemini API key not found in environment variables."

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    payload = {"contents": [{"parts": [{"text": "Provide a concise Texas solar market outlook for 2026."}]}]}

    try:
        r = requests.post(f"{url}?key={GEMINI_API_KEY}", json=payload, timeout=15)
        r.raise_for_status()
        res_json = r.json()
        # Correct path for the 1.5 Flash API response
        text = res_json['candidates'][0]['content']['parts'][0]['text']
        return dcc.Markdown(text) # Markdown looks better than html.Pre
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

if __name__ == "__main__":
    app.run_server(debug=True)
