import os
import requests
import yfinance as yf
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go

# ===============================
# App setup
# ===============================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ===============================
# Static Texas solar data (safe)
# ===============================
SOLAR_DATA = {
    "Austin": {
        "lat": 30.27, "lon": -97.74,
        "commercial": 220, "residential": 160,
        "demand": 300, "tou": 0.14
    },
    "Dallas": {
        "lat": 32.77, "lon": -96.79,
        "commercial": 200, "residential": 140,
        "demand": 280, "tou": 0.13
    },
    "Houston": {
        "lat": 29.76, "lon": -95.37,
        "commercial": 260, "residential": 180,
        "demand": 340, "tou": 0.15
    }
}

# ===============================
# Layout
# ===============================
app.layout = dbc.Container(fluid=True, children=[

    html.H1("Specusol ☀️ Texas Solar Market Simulator", className="text-center my-3"),

    dbc.Row([
        dbc.Col([
            dl.Map(
                center=[31.0, -99.0],
                zoom=6,
                style={"height": "600px"},
                id="texas-map",
                children=[
                    dl.TileLayer(),
                    dl.LayerGroup([
                        dl.Marker(
                            position=[v["lat"], v["lon"]],
                            children=dl.Tooltip(k),
                            id={"type": "city-marker", "city": k}
                        ) for k, v in SOLAR_DATA.items()
                    ])
                ]
            )
        ], width=6),

        dbc.Col([
            dcc.Graph(id="supply-demand-chart")
        ], width=6)
    ]),

    html.Hr(),

    dbc.Row([
        dbc.Col([
            dcc.Graph(id="solar-etf")
        ], width=12)
    ]),

    html.Hr(),

    dbc.Row([
        dbc.Col([
            html.H4("Gemini AI – ERCOT Market Outlook"),
            html.Div(id="gemini-summary", className="p-3 border")
        ])
    ]),

    html.Hr(),

    html.P(
        "Specusol is an information service. Information is for educational purposes only and is not intended to be used as investment advice.",
        className="text-muted text-center"
    )
])

# ===============================
# Supply/Demand Chart
# ===============================
@app.callback(
    Output("supply-demand-chart", "figure"),
    Input({"type": "city-marker", "city": "Austin"}, "n_clicks"),
    Input({"type": "city-marker", "city": "Dallas"}, "n_clicks"),
    Input({"type": "city-marker", "city": "Houston"}, "n_clicks"),
    prevent_initial_call=True
)
def update_chart(austin_click, dallas_click, houston_click):
    # Get triggered city
    triggered_city = None
    if austin_click:
        triggered_city = "Austin"
    elif dallas_click:
        triggered_city = "Dallas"
    elif houston_click:
        triggered_city = "Houston"
    
    if triggered_city:
        d = SOLAR_DATA[triggered_city]

        fig = go.Figure()
        fig.add_bar(name="Commercial Supply", x=["Supply"], y=[d["commercial"]])
        fig.add_bar(name="Residential Supply", x=["Supply"], y=[d["residential"]])
        fig.add_scatter(name="Demand", x=["Supply"], y=[d["demand"]], mode="lines+markers")

        fig.update_layout(
            title=f"{triggered_city} Solar Supply vs Demand (TOU ${d['tou']}/kWh)",
            barmode="group",
            yaxis_title="MW"
        )
        return fig
    return go.Figure()

# ===============================
# Solar ETF Chart
# ===============================
@app.callback(
    Output("solar-etf", "figure"),
    Input("solar-etf", "id")
)
def load_etf(_):
    data = yf.download("TAN", period="1y")
    fig = go.Figure()
    fig.add_scatter(x=data.index, y=data["Close"], mode="lines")
    fig.update_layout(title="Solar ETF (TAN)")
    return fig

# ===============================
# Gemini AI Summary (REST API)
# ===============================
@app.callback(
    Output("gemini-summary", "children"),
    Input("gemini-summary", "id")
)
def gemini_summary(_):
    if not GEMINI_API_KEY:
        return "Gemini API key not set."

    prompt = """
Act as a Senior ERCOT Market Analyst and Energy Broker Advisor.
Provide a concise Texas solar market outlook for 2026.
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    r = requests.post(
        f"{url}?key={GEMINI_API_KEY}",
        json=payload,
        timeout=15
    )

    if r.status_code != 200:
        return "Unable to retrieve Gemini summary."

    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return html.Pre(text)

# ===============================
# Run
# ===============================
if __name__ == "__main__":
    app.run_server(debug=True)

