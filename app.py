# ------------------------------
# app.py
# ------------------------------

import dash
from dash import html, dcc, Output, Input
import dash_leaflet as dl
import dash_leaflet.express as dlx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ------------------------------
# 1️⃣ Helper: Simulate solar supply
# ------------------------------
def get_solar_supply(lat, lon):
    # Hourly timestamps for 7 days
    timestamps = pd.date_range(datetime.now(), periods=168, freq='h')

    # Simulated solar irradiance (GHI)
    ghi = np.clip(500 + 300*np.sin(np.linspace(0, 3*np.pi, 168)) + 50*np.random.randn(168), 0, None)
    cloud_factor = np.random.uniform(0.7, 1.0, 168)
    temp_factor = 1 - 0.004*(np.random.uniform(20, 35, 168)-25)

    # Areas (m2) and efficiency
    res_area, comm_area = 10000, 50000
    eff, pr = 0.18, 0.75

    res_supply = ghi * cloud_factor * temp_factor * res_area * eff / 1000
    comm_supply = ghi * cloud_factor * temp_factor * comm_area * eff * pr / 1000

    df = pd.DataFrame({
        "timestamp": timestamps,
        "res_supply": res_supply,
        "comm_supply": comm_supply
    })
    return df

# ------------------------------
# 2️⃣ Build the Plotly figure
# ------------------------------
def build_figure(lat, lon):
    df = get_solar_supply(lat, lon)

    # Simulate demand
    df["res_demand"] = df.res_supply * np.random.uniform(0.7, 1.0, len(df))
    df["comm_demand"] = df.comm_supply * np.random.uniform(0.7, 1.0, len(df))

    # Aggregate
    df["total_supply"] = df.res_supply + df.comm_supply
    df["total_demand"] = df.res_demand + df.comm_demand

    # Equilibrium curve
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
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_supply,
                             name="Residential Supply", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.res_demand,
                             name="Residential Demand", line=dict(color="red", dash="dash")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_supply,
                             name="Commercial Supply", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.comm_demand,
                             name="Commercial Demand", line=dict(color="navy", dash="dash")))

    # Equilibrium
    fig.add_trace(go.Scatter(x=df.timestamp, y=df.equilibrium,
                             name="Market Equilibrium (Supply − Demand)",
                             line=dict(color="green", width=3)))

    # Zero reference
    fig.add_hline(y=0, line=dict(color="gray", dash="dot"))

    # TOU pricing overlay
    fig.add_trace(go.Scatter(
        x=df.timestamp, y=df.price,
        name="TOU Price ($/kWh)",
        yaxis="y2",
        line=dict(color="black")
    ))

    fig.update_layout(
        title=f"Texas Solar Supply, Demand & Market Equilibrium<br>LAT={lat:.3f}, LON={lon:.3f}",
        xaxis_title="Time",
        yaxis=dict(title="Power Balance (kW)"),
        yaxis2=dict(title="Price ($/kWh)", overlaying="y", side="right"),
        template="plotly_white",
        legend=dict(orientation="h"),
        height=600
    )
    return fig

# ------------------------------
# 3️⃣ ERCOT zone polygons (simplified)
# ------------------------------
ercot_zones = [
    {"name": "North", "coords": [[33.0, -100.0], [33.0, -95.0], [36.5, -95.0], [36.5, -100.0]]},
    {"name": "South", "coords": [[26.0, -100.0], [26.0, -95.0], [33.0, -95.0], [33.0, -100.0]]}
]

polygons = [dl.Polygon(positions=zone["coords"], color="purple", fillOpacity=0.1, weight=2) for zone in ercot_zones]

# ------------------------------
# 4️⃣ Dash App
# ------------------------------
app = dash.Dash(__name__)
app.title = "Texas Solar Market Dashboard"

app.layout = html.Div([
    html.H2("Texas Solar Market Dashboard"),
    html.Div([
        dl.Map(center=[31.0, -97.0], zoom=6, children=[
            dl.TileLayer(),
            *polygons,
            dl.LayerGroup(id="marker-layer")
        ], style={'width': '100%', 'height': '400px'}, id="map")
    ]),
    dcc.Graph(id="chart", figure=build_figure(30.26, -97.74))
])

# ------------------------------
# 5️⃣ Callbacks: Update chart on map click
# ------------------------------
@app.callback(
    Output("chart", "figure"),
    Input("map", "click_lat_lng")
)
def update_chart(click_lat_lng):
    if click_lat_lng is None:
        lat, lon = 30.26, -97.74  # Austin default
    else:
        lat, lon = click_lat_lng
    return build_figure(lat, lon)

# ------------------------------
# 6️⃣ Run server
# ------------------------------
if __name__ == "__main__":
    # Render uses 0.0.0.0 and PORT environment variable
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
