from dash import Dash, html, dcc, Input, Output
import dash_leaflet as dl
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go

# ------------------------------
# ERCOT ZONES (SIMPLIFIED GEOJSON)
# ------------------------------
ercot_zones = {
    "type": "FeatureCollection",
    "features": [
        {"type":"Feature","properties":{"zone":"North"},
         "geometry":{"type":"Polygon","coordinates":[[[-103,36],[-94,36],[-94,33],[-103,33],[-103,36]]]}},
        {"type":"Feature","properties":{"zone":"South"},
         "geometry":{"type":"Polygon","coordinates":[[[-102,29],[-96,29],[-96,26],[-102,26],[-102,29]]]}},
        {"type":"Feature","properties":{"zone":"West"},
         "geometry":{"type":"Polygon","coordinates":[[[-106,33],[-102,33],[-102,29],[-106,29],[-106,33]]]}},
        {"type":"Feature","properties":{"zone":"Houston"},
         "geometry":{"type":"Polygon","coordinates":[[[-96,31],[-94,31],[-94,29],[-96,29],[-96,31]]]}},
        {"type":"Feature","properties":{"zone":"Coastal"},
         "geometry":{"type":"Polygon","coordinates":[[[-98,29],[-94,29],[-94,26],[-98,26],[-98,29]]]}}
    ]
}

# ------------------------------
# SOLAR SUPPLY MODEL
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

# ------------------------------
# FIGURE BUILDER (WITH EQUILIBRIUM)
# ------------------------------
def build_figure(lat, lon):
    df = get_solar_supply(lat, lon)

    # Demand proxies
    df["res_demand"] = df.res_supply * np.random.uniform(0.7, 1.0, len(df))
    df["comm_demand"] = df.comm_supply * np.random.uniform(0.7, 1.0, len(df))

    # Aggregate
    df["total_supply"] = df.res_supply + df.comm_supply
    df["total_demand"] = df.res_demand + df.comm_demand

    # ⚖️ Equilibrium curve
    df["equilibrium"] = df.total_supply - df.total_demand

    # TOU pricing
    hour = df.timestamp.dt.hour
    df["price"] = np.select(
        [hour < 6, hour < 14, hour < 20, hour < 22],
        [0.07, 0.11, 0.22, 0.13],
        default=0.07
    )

    fig = go.Figure()

    # Supply & Demand
    fig.add_trace(go.Scatter(df.timestamp, df.res_supply,
                             name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(df.timestamp, df.res_demand,
                             name="Residential Demand", line=dict(color="red", dash="dash")))

    fig.add_trace(go.Scatter(df.timestamp, df.comm_supply,
                             name="Commercial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(df.timestamp, df.comm_demand,
                             name="Commercial Demand", line=dict(color="navy", dash="dash")))

    # ⚖️ Equilibrium
    fig.add_trace(go.Scatter(
        df.timestamp, df.equilibrium,
        name="Market Equilibrium (Supply − Demand)",
        line=dict(color="green", width=4)
    ))

    # Zero reference
    fig.add_hline(y=0, line=dict(color="gray", dash="dot"))

    # TOU pricing
    fig.add_trace(go.Scatter(
        df.timestamp, df.price,
        name="TOU Price ($/kWh)",
        yaxis="y2",
        line=dict(color="black")
    ))

    fig.update_layout(
        title=f"Texas Solar Supply, Demand & Market Equilibrium<br>LAT={lat:.3f}, LON={lon:.3f}",
        xaxis_title="Time",
        yaxis=dict(title="Power Balance (kW)"),
        yaxis2=dict(
            title="Price ($/kWh)",
            overlaying="y",
            side="right"
        ),
        template="plotly_white",
        legend=dict(orientation="h")
    )

    return fig

# ------------------------------
# DASH APP
# ------------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.H2("Texas Solar Market Dashboard"),

    dl.Map(
        id="map",
        center=[31, -100],
        zoom=6,
        style={"height": "420px"},
        children=[
            dl.TileLayer(),
            dl.GeoJSON(
                data=ercot_zones,
                style={
                    "fillColor": "#1f77b4",
                    "color": "black",
                    "weight": 1,
                    "fillOpacity": 0.25
                }
            ),
            dl.Marker(id="marker", position=[30.26, -97.74])
        ]
    ),

    html.Div([
        "Latitude:",
        dcc.Input(id="lat", value=30.26, type="number", step=0.001),
        "Longitude:",
        dcc.Input(id="lon", value=-97.74, type="number", step=0.001)
    ], style={"marginTop": "10px"}),

    dcc.Graph(
        id="chart",
        figure=build_figure(30.26, -97.74)
    )
])

# ------------------------------
# CALLBACKS
# ------------------------------
@app.callback(
    Output("lat", "value"),
    Output("lon", "value"),
    Output("marker", "position"),
    Input("map", "clickData")
)
def update_coords(clickData):
    if clickData is None:
        lat, lon = 30.26, -97.74
        return lat, lon, [lat, lon]

    lat = clickData["latlng"]["lat"]
    lon = clickData["latlng"]["lng"]
    return lat, lon, [lat, lon]

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

