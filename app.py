import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_leaflet as dl
import dash_leaflet.express as dlx
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta

# ------------------------------
# ERCOT zones (GeoJSON) - example simplified
# ------------------------------
ercot_zones = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"name": "North"}, 
         "geometry": {"type": "Polygon", "coordinates":[[[-97,-32],[-97,34],[-100,34],[-100,-32],[-97,-32]]] }},
        {"type": "Feature", "properties": {"name": "South"}, 
         "geometry": {"type": "Polygon", "coordinates":[[[-95,-32],[-95,30],[-100,30],[-100,-32],[-95,-32]]] }}
    ]
}
polygons = [dl.GeoJSON(data=ercot_zones, options=dict(style=dict(weight=2, color="green", fillOpacity=0.1)))]

# ------------------------------
# Constants for NREL API
# ------------------------------
NREL_URL = "https://developer.nrel.gov/api/solar/solar_resource/v1.json"
NREL_KEY = "xrKsemxjKJqoObOC1IDEvt4qNFbMQQy79pFqGWKF"

# ------------------------------
# Functions to get data
# ------------------------------
def get_weather_overlay(lat, lon):
    params = {"api_key": NREL_KEY, "lat": lat, "lon": lon}
    r = requests.get(NREL_URL, params=params)
    if r.status_code != 200:
        return {"ghi": 0, "temp": 25, "cloud": 0}
    data = r.json()
    try:
        solrad = data["outputs"]["avg_ghi"]["annual"]  # Just an example field
    except:
        solrad = 0
    return {"ghi": solrad, "temp": 25, "cloud": 0}

def get_solar_supply(lat, lon):
    # 1 week hourly
    timestamps = pd.date_range(datetime.now(), periods=168, freq='h')
    weather = get_weather_overlay(lat, lon)
    
    ghi = weather['ghi']
    cloud_factor = 1 - weather['cloud']/100
    temp_factor = 1 - 0.004*(weather['temp']-25)
    
    res_area = 10000
    comm_area = 50000
    eff = 0.18
    pr = 0.75

    df = pd.DataFrame({
        'timestamp': timestamps,
        'res_supply': ghi * cloud_factor * temp_factor * (res_area * eff / 1000),
        'comm_supply': ghi * cloud_factor * temp_factor * (comm_area * eff * pr / 1000)
    })

    # Example demand (could replace with ERCOT data)
    df['res_demand'] = df['res_supply'] * 0.9
    df['comm_demand'] = df['comm_supply'] * 0.9

    # Equilibrium
    df['equilibrium'] = (df['res_supply'] + df['comm_supply'] + df['res_demand'] + df['comm_demand']) / 4

    # Example TOU pricing
    df['tou_price'] = [0.1 if 6 <= ts.hour <= 22 else 0.05 for ts in df['timestamp']]

    return df

def build_figure(lat, lon):
    df = get_solar_supply(lat, lon)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply,
                             name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_supply,
                             name="Commercial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_demand,
                             name="Residential Demand", line=dict(color="darkorange", dash="dash")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_demand,
                             name="Commercial Demand", line=dict(color="darkblue", dash="dash")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.equilibrium,
                             name="Equilibrium", line=dict(color="green", width=3, dash="dot")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.tou_price,
                             name="TOU Price ($/kWh)", line=dict(color="red"), yaxis="y2"))
    
    # Dual axis
    fig.update_layout(
        yaxis=dict(title="kW"),
        yaxis2=dict(title="$/kWh", overlaying="y", side="right"),
        title="Solar Supply/Demand + TOU Pricing",
        xaxis_title="Time",
        template="plotly_dark",
        legend=dict(orientation="h")
    )
    return fig

# ------------------------------
# Dash App
# ------------------------------
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Texas Solar Dashboard"),
    html.Div([
        dl.Map(center=[31.0, -97.0], zoom=6, children=[
            dl.TileLayer(),
            *polygons,
            dl.Marker(id="marker", position=[30.26, -97.74])
        ], style={'width': '100%', 'height': '400px'}, id="map")
    ]),
    dcc.Graph(id="chart", figure=build_figure(30.26, -97.74))
])

# ------------------------------
# Callback: update chart + marker
# ------------------------------
@app.callback(
    Output("chart", "figure"),
    Output("marker", "position"),
    Input("map", "click_lat_lng")
)
def update_chart(click_lat_lng):
    if click_lat_lng is None:
        lat, lon = 30.26, -97.74
    else:
        lat, lon = click_lat_lng
    return build_figure(lat, lon), [lat, lon]

# ------------------------------
# Run
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

