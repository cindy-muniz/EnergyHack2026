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
# ERCOT Zones (simplified example)
# Replace coordinates with correct ERCOT polygons
# ------------------------------
ercot_zones = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "North"},
            "geometry": {"type": "Polygon",
                         "coordinates": [[[-101, 36], [-97, 36], [-97, 33], [-101, 33], [-101, 36]]]}
        },
        {
            "type": "Feature",
            "properties": {"name": "South"},
            "geometry": {"type": "Polygon",
                         "coordinates": [[[-101, 33], [-97, 33], [-97, 29], [-101, 29], [-101, 33]]]}
        }
    ]
}

# Convert to Dash Leaflet GeoJSON
geojson = dl.GeoJSON(data=ercot_zones, id="geojson",
                     options=dict(style=dict(weight=2, color="green", fillOpacity=0.1)))

# ------------------------------
# NREL API
# ------------------------------
NREL_KEY = "xrKsemxjKJqoObOC1IDEvt4qNFbMQQy79pFqGWKF"
NREL_URL = "https://developer.nrel.gov/api/solar/solar_resource/v1.json"

def get_weather(lat, lon):
    params = {"api_key": NREL_KEY, "lat": lat, "lon": lon}
    r = requests.get(NREL_URL, params=params)
    if r.status_code != 200:
        return {"ghi": 0, "temp": 25, "cloud": 0}
    data = r.json()
    try:
        solrad = data["outputs"]["avg_ghi"]["annual"]
    except:
        solrad = 0
    return {"ghi": solrad, "temp": 25, "cloud": 0}

# ------------------------------
# Solar supply / demand / equilibrium
# ------------------------------
def get_solar_supply(lat, lon):
    timestamps = pd.date_range(datetime.now(), periods=168, freq='h')
    weather = get_weather(lat, lon)
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

    df['res_demand'] = df['res_supply'] * 0.9
    df['comm_demand'] = df['comm_supply'] * 0.9
    df['equilibrium'] = (df['res_supply'] + df['comm_supply'] + df['res_demand'] + df['comm_demand']) / 4
    df['tou_price'] = [0.1 if 6 <= ts.hour <= 22 else 0.05 for ts in df['timestamp']]
    return df

def build_figure(lat, lon):
    df = get_solar_supply(lat, lon)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply, name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_supply, name="Commercial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_demand, name="Residential Demand", line=dict(color="darkorange", dash="dash")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_demand, name="Commercial Demand", line=dict(color="darkblue", dash="dash")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.equilibrium, name="Equilibrium", line=dict(color="green", width=3, dash="dot")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.tou_price, name="TOU Price ($/kWh)", line=dict(color="red"), yaxis="y2"))

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

# Initial marker location
init_lat, init_lon = 30.26, -97.74

app.layout = html.Div([
    html.H2("Texas Solar Dashboard"),
    dl.Map(center=[31, -97], zoom=6, children=[
        dl.TileLayer(),
        geojson,
        dl.LayerGroup(id="weather-overlay"),
        dl.Marker(position=[init_lat, init_lon], id="marker")
    ], style={'width': '100%', 'height': '500px'}, id="map"),
    dcc.Graph(id="chart", figure=build_figure(init_lat, init_lon))
])

# ------------------------------
# Callback for click
# ------------------------------
@app.callback(
    Output("chart", "figure"),
    Output("marker", "position"),
    Output("weather-overlay", "children"),
    Input("map", "click_lat_lng")
)
def update_chart(click):
    if click is None:
        lat, lon = init_lat, init_lon
    else:
        lat, lon = click

    # Weather overlay as a circle
    weather = get_weather(lat, lon)
    circle = dl.Circle(center=[lat, lon], radius=20000,
                       color="yellow", fillOpacity=0.4,
                       tooltip=f"GHI: {weather['ghi']:.1f} W/m2")
    return build_figure(lat, lon), [lat, lon], [circle]

# ------------------------------
# Run server
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

