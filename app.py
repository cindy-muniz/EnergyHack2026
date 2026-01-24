# app.py
# ------------------------------
# 1️⃣ Imports
# ------------------------------
from dash import Dash, html, dcc, Input, Output
import dash_leaflet as dl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ------------------------------
# 2️⃣ Solar supply/demand/TOU functions
# ------------------------------
def get_solar_supply(lat, lon, res_area=10000, comm_area=50000):
    # simulate 7-day hourly data
    timestamps = pd.date_range(datetime.now(), periods=168, freq='h')
    # simple GHI model
    ghi = np.maximum(0, 1000 * np.sin((timestamps.hour-6)/12*np.pi))
    cloud_factor = 1 - np.random.uniform(0.0,0.2,len(timestamps))
    eff, pr = 0.18, 0.75
    res_kw = ghi * cloud_factor * (res_area*eff/1000)
    comm_kw = ghi * cloud_factor * (comm_area*eff*pr/1000)
    return pd.DataFrame({
        "timestamp": timestamps,
        "res_supply_kw": res_kw,
        "comm_supply_kw": comm_kw
    })

def get_solar_demand(df):
    res_demand = df["res_supply_kw"] * np.random.uniform(0.7,1.0,len(df))
    comm_demand = df["comm_supply_kw"] * np.random.uniform(0.7,1.0,len(df))
    return res_demand, comm_demand

def get_tou(df, res_demand, comm_demand, res_supply, comm_supply):
    hours = df["timestamp"].dt.hour
    base_price = np.select(
        [(hours >=22)|(hours<6), (hours>=6)&(hours<14), (hours>=14)&(hours<20), (hours>=20)&(hours<22)],
        [0.07,0.11,0.22,0.13]
    )
    net_res = res_supply/(res_demand+1e-6)
    net_comm = comm_supply/(comm_demand+1e-6)
    net_factor = np.minimum(net_res, net_comm)
    responsive_price = base_price*(1.5-0.5*net_factor)
    df["price_per_kwh"] = np.clip(responsive_price + np.random.normal(0,0.005,len(df)), 0.05, 0.30)
    return df

def build_figure(lat, lon):
    supply_df = get_solar_supply(lat, lon)
    res_demand, comm_demand = get_solar_demand(supply_df)
    supply_df = get_tou(supply_df, res_demand, comm_demand, supply_df["res_supply_kw"], supply_df["comm_supply_kw"])
    
    fig = go.Figure()
    # Residential
    fig.add_trace(go.Scatter(x=supply_df.timestamp, y=supply_df.res_supply_kw,
                             mode='lines', name='Residential Supply', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=supply_df.timestamp, y=res_demand,
                             mode='lines', name='Residential Demand', line=dict(color='red', dash='dash')))
    # Commercial
    fig.add_trace(go.Scatter(x=supply_df.timestamp, y=supply_df.comm_supply_kw,
                             mode='lines', name='Commercial Supply', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=supply_df.timestamp, y=comm_demand,
                             mode='lines', name='Commercial Demand', line=dict(color='navy', dash='dash')))
    # TOU price
    fig.add_trace(go.Scatter(x=supply_df.timestamp, y=supply_df.price_per_kwh,
                             mode='lines', name='TOU Price', line=dict(color='black'), yaxis='y2'))
    
    fig.update_layout(
        title=f"Texas Solar Supply & Demand with Dynamic TOU Pricing\nLAT={lat:.3f}, LON={lon:.3f}",
        xaxis_title="Time",
        yaxis=dict(title="Power (kW)"),
        yaxis2=dict(title="Price ($/kWh)", overlaying='y', side='right'),
        legend=dict(x=0, y=1.2),
        template='plotly_white'
    )
    return fig

# ------------------------------
# 3️⃣ Dash App
# ------------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Texas Solar Dashboard"),
    html.Div([
        html.Label("Click on the map to select LAT/LON"),
        dl.Map(center=[31, -100], zoom=6, children=[dl.TileLayer()], id="map", style={'width': '100%', 'height': '400px'}),
    ]),
    html.Div([
        html.Label("Latitude:"), dcc.Input(id='lat-input', type='number', value=30.26),
        html.Label("Longitude:"), dcc.Input(id='lon-input', type='number', value=-97.74),
    ]),
    dcc.Graph(id='solar-graph')
])

# ------------------------------
# 4️⃣ Callbacks
# ------------------------------
@app.callback(
    Output('lat-input', 'value'),
    Output('lon-input', 'value'),
    Input('map', 'click_lat_lng')
)
def map_click(coords):
    if coords is None:
        return 30.26, -97.74
    return coords[0], coords[1]

@app.callback(
    Output('solar-graph', 'figure'),
    Input('lat-input', 'value'),
    Input('lon-input', 'value')
)
def update_chart(lat, lon):
    return build_figure(lat, lon)

# ------------------------------
# 5️⃣ Run App
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)


