import dash
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objs as go
import pandas as pd
import yfinance as yf
import requests
import openai

# ----------------- Setup -----------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Specusol"
app.icon = "/assets/specusol_icon.png"  # Place your favicon in assets folder

server = app.server  # for deployment

# ----------------- Placeholder Data -----------------
# Map zones (replace with actual ERCOT zone polygons)
ercot_zones = {
    "North": [[30, -97], [31, -97], [31, -96], [30, -96]],
    "South": [[29, -98], [30, -98], [30, -97], [29, -97]],
}

# Supply & demand example data
supply_demand_data = {
    "North": {"commercial": 300, "residential": 200, "tou_price": 0.12},
    "South": {"commercial": 250, "residential": 150, "tou_price": 0.10},
}

# ----------------- Layout -----------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Specusol Dashboard"), width=12)
    ]),
    dbc.Row([
        dbc.Col(html.Div("The content on this site is for informational purposes only and should not be considered financial or investment advice."),
                width=12, style={"backgroundColor": "#f8d7da", "padding": "10px", "borderRadius": "5px", "marginBottom": "20px"}),
    ]),
    dbc.Tabs([
        dbc.Tab(label="Map & Solar Data", tab_id="map_tab"),
        dbc.Tab(label="Charts", tab_id="charts_tab"),
        dbc.Tab(label="Finances", tab_id="finances_tab"),
    ], id="tabs", active_tab="map_tab"),
    html.Div(id="tab-content", style={"marginTop": "20px"})
])

# ----------------- Callbacks -----------------

@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab")
)
def render_tab(tab):
    if tab == "map_tab":
        return render_map_tab()
    elif tab == "charts_tab":
        return render_charts_tab()
    elif tab == "finances_tab":
        return render_finances_tab()
    else:
        return html.Div("Tab not found.")

# ----------------- Map Tab -----------------
def render_map_tab():
    polygons = []
    for zone_name, coords in ercot_zones.items():
        polygons.append(dl.Polygon(positions=coords, color="blue", fillOpacity=0.3, id=zone_name))
    
    return html.Div([
        dl.Map(children=[
            dl.TileLayer(),
            *polygons
        ], center=[30.5, -97.5], zoom=6, style={'width': '100%', 'height': '500px'}, id="solar-map"),
        html.Div(id="map-info", style={"marginTop": "20px"})
    ])

@app.callback(
    Output("map-info", "children"),
    Input({"type": "zone", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def update_zone_info(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "Click a zone to see supply-demand data."
    
    # Identify clicked zone
    zone = ctx.triggered[0]['prop_id'].split('.')[0]
    if zone not in supply_demand_data:
        return "No data for this zone."
    
    data = supply_demand_data[zone]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Commercial"], y=[data["commercial"]], name="Commercial"))
    fig.add_trace(go.Bar(x=["Residential"], y=[data["residential"]], name="Residential"))
    fig.add_trace(go.Scatter(x=["Commercial", "Residential"], y=[data["commercial"], data["residential"]], mode="lines+markers", name="Equilibrium"))
    
    fig.update_layout(title=f"{zone} Solar Supply & Demand",
                      yaxis_title="MW",
                      xaxis_title="Sector")
    
    return dcc.Graph(figure=fig)

# ----------------- Charts Tab -----------------
def render_charts_tab():
    # Placeholder chart: will be updated by map selection ideally
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[], y=[]))
    fig.update_layout(title="Commercial vs Residential Solar Supply-Demand",
                      xaxis_title="Sector",
                      yaxis_title="MW")
    return dcc.Graph(figure=fig)

# ----------------- Finances Tab -----------------
def render_finances_tab():
    # Solar ETF data
    etf = yf.Ticker("TAN")  # Example: Solar ETF
    hist = etf.history(period="1y")
    etf_fig = go.Figure()
    etf_fig.add_trace(go.Candlestick(x=hist.index,
                                     open=hist['Open'],
                                     high=hist['High'],
                                     low=hist['Low'],
                                     close=hist['Close'],
                                     name="TAN ETF"))
    etf_fig.update_layout(title="Solar ETF TAN Price History")
    
    # Gemini AI Summary (placeholder)
    openai.api_key = "YOUR_OPENAI_API_KEY"
    prompt = "Provide a short AI summary for solar energy investments."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        ai_summary = response['choices'][0]['message']['content']
    except Exception:
        ai_summary = "AI summary could not be retrieved."

    return html.Div([
        html.H3("Solar Stock ETF"),
        dcc.Graph(figure=etf_fig),
        html.H3("Gemini AI Summary"),
        html.P(ai_summary)
    ])

# ----------------- Run -----------------
if __name__ == "__main__":
    app.run_server(debug=True)
