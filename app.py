from dash import Dash, html, dcc, Input, Output
import dash_leaflet as dl
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# ------------------------------
# ERCOT ZONES (SIMPLIFIED)
# ------------------------------
ercot_zones = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature","properties":{"zone":"North"},"geometry":{"type":"Polygon","coordinates":[[[-103,36],[-94,36],[-94,33],[-103,33],[-103,36]]]}},
        {"type": "Feature","properties":{"zone":"South"},"geometry":{"type":"Polygon","coordinates":[[[-102,29],[-96,29],[-96,26],[-102,26],[-102,29]]]}},
        {"type": "Feature","properties":{"zone":"West"},"geometry":{"type":"Polygon","coordinates":[[[-106,33],[-102,33],[-102,29],[-106,29],[-106,33]]]}},
        {"type": "Feature","properties":{"zone":"Houston"},"geometry":{"type":"Polygon","coordinates":[[[-96,31],[-94,31],[-94,29],[-96,29],[-96,31]]]}},
        {"type": "Feature","properties":{"zone":"Coastal"},"geometry":{"type":"Polygon","coordinates":[[[-98,29],[-94,29],[-94,26],[-98,26],[-98,29]]]}}
    ]
}

zone_colors = {
    "North": "#1f77b4",
    "South": "#2ca02c",
    "West": "#ff7f0e",
    "Houston": "#d62728",
    "Coastal": "#9467bd"
}

def zone_style(feature):
    return {
        "fillColor": zone_colors.get(feature["properties"]["zone"], "gray"),
        "color": "black",
        "weight": 1,
        "fillOpacity": 0.3
    }

# ------------------------------
# DATA
# ------------------------------
def get_solar_supply(lat, lon):
    timestamps = pd.date_range(datetime.now(), periods=168, freq="h")

    ghi = np.maximum(0, 1000 * np.sin((timestamps.hour - 6) / 12 * np.pi))
    cloud = 1 - np.random.uniform(0, 0.25, len(timestamps))

    res_kw = ghi * cloud * (10000 * 0.18 / 1000)
    comm_kw = ghi * cloud * (50000 * 0.18 * 0.75 / 1000)

    return pd.DataFrame({
        "timestamp": timestamps,
        "res_supply": res_kw,
        "comm_supply": comm_kw
    })

def build_figure(lat, lon):
    df = get_solar_supply(lat, lon)

    res_demand = df.res_supply * np.random.uniform(0.7, 1.0, len(df))
    comm_demand = df.comm_supply * np.random.uniform(0.7, 1.0, len(df))

    hour = df.timestamp.dt.hour
    price = np.select(
        [hour < 6, hour < 14, hour < 20, hour < 22],
        [0.07, 0.11, 0.22, 0.13],
        default=0.07
    )

    fig = go.Figure()

    fig.add_trace(go.Scatter(df.timestamp, df.res_supply, name="Residential Supply"))
    fig.add_trace(go.Scatter(df.timestamp, res_demand, name="Residential Demand", dash="dash"))
    fig.add_trace(go.Scatter(df.timestamp, df.comm_supply, name="Commercial Supply"))
    fig.add_trace(go.Scatter(df.timestamp, comm_demand, name="Commercial Demand", dash="dash"))

    fig.add_trace(go.Scatter(
        df.timestamp, price,
        name="TOU Price ($/kWh)",
        yaxis="y2",
        line=dict(color="black")
    ))

    fig.update_layout(
        title=f"Texas Solar Supply, Demand & TOU Pricing<br>LAT={lat:.3f}, LON={lon:.3f}",
        yaxis=dict(title="Power (kW)"),
        yaxis2=dict(title="Price ($/kWh)", overlaying="y", side="right"),
        template="plotly_white",
        legend=dict(orientation="h")
    )

    return fig

# ------------------------------
# APP
# ------------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.H2("Texas Solar Dashboard (ERCOT Zones)"),

    dl.Map(
        id="map",
        center=[31, -100],
        zoom=6,
        style={"height": "420px"},
        click_lat_lng=None,
        children=[
            dl.TileLayer(),
            dl.GeoJSON(data=ercot_zones, options=dict(style=zone_style)),
            dl.Marker(id="marker")
        ]
    ),

    html.Div([
        "Latitude:", dcc.Input(id="lat", value=30.26, type="number"),
        "Longitude:", dcc.Input(id="lon", value=-97.74, type="number"),
    ], style={"marginTop": "10px"}),

    dcc.Graph(id="chart")
])

# ------------------------------
# CALLBACKS
# ------------------------------
@app.callback(
    Output("lat", "value"),
    Output("lon", "value"),
    Output("marker", "position"),
    Input("map", "click_lat_lng")
)
def update_coords(click):
    if click is None:
        return 30.26, -97.74, [30.26, -97.74]
    return click[0], click[1], click

@app.callback(
    Output("chart", "figure"),
    Input("lat", "value"),
    Input("lon", "value")
)
def update_chart(lat, lon):
    return build_figure(lat, lon)

# ------------------------------
# RUN (RENDER)
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)


