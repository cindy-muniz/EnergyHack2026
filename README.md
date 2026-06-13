<p align="center">
  <img src="assets/logo.png" alt="Specusol" width="380">
</p>

<h1 align="center">Specusol — Solar Energy Market Dashboard</h1>

<p align="center">
  <em>Live Solar Insights for Texas Energy Leaders</em><br><br>
  🔗 <a href="https://energyhack2026.onrender.com">Live demo</a>  ·  Built at <strong>EnergyHack @ Georgia Tech</strong>  ·  January 2026<br>
  Python · Plotly Dash · deployed on Render
</p>

---

## What it does

Specusol is an interactive web dashboard that treats excess Texas solar energy as a
tradeable financial asset. Solar farms on the ERCOT grid routinely generate more energy
than the grid can use — Specusol visualizes that surplus and lets you explore it from both
an energy and a market angle.

In one view, the app shows:

- **Supply vs. demand curves** — residential and commercial solar modeled across a 24-hour
  cycle, with automatic equilibrium detection
- **ERCOT zone verification** — enter any Texas address and the app maps it to its ERCOT grid
  zone (North, South, West, Houston) using live geolocation
- **Solar stock tracker** — Texas-relevant equities (TAN, ENPH, VLO, FSLR, WHD) with
  candlestick charts and trend overlays
- **7-hour weather forecast** — localized temperature and solar irradiance estimates (W/m²)
- **Grid health analytics** — carbon intensity and grid-frequency estimates, with the
  underlying formulas shown for transparency

![Specusol dashboard — a verified Houston ERCOT zone alongside the 24-hour supply/demand model with the equilibrium point annotated](assets/dashboard.png)

---

## My role

This was my first hackathon — and my first time using Git, GitHub, and Render. Jenna and I
built Specusol together over 24 hours. We each worked in our own repository and merged our
features into this final, deployed version at the end.

**What I built**

- **ERCOT zone map** — my idea, and I implemented the first working version: lat/lon bounding
  boxes for the four ERCOT zones (pure Python, no geospatial dependencies, for deployment
  stability on Render) with live address-to-zone lookup and pin-drop.
- **Data visualizations** — the supply/demand curves and solar-output charts, including a
  Gaussian daylight model (peaking ~1:15 PM at ~1000 W/m²) and the automatic supply/demand
  equilibrium annotation.

**What Jenna built**

- The **solar stock market tracker** and related financial/Greeks analytics.

We jointly integrated both halves, debugged the merge, and deployed the final app to Render.

> 📝 This project also lives in a second repo,
> [Specusol](https://github.com/cindy-muniz/Specusol) — my individual working copy from the
> hackathon. Jenna and I each developed in our own repos and combined everything here for the
> final deployed build.

---

## Tech stack

| Layer         | Technology                              |
|---------------|------------------------------------------|
| Language      | Python 3                                 |
| Web framework | Plotly Dash + Dash Bootstrap Components  |
| Mapping       | Dash Leaflet                             |
| Data / math   | NumPy, Pandas, SciPy                     |
| Geolocation   | Geopy / Nominatim                        |
| Deployment    | Render                                   |

---

## Run it locally

```bash
git clone https://github.com/cindy-muniz/EnergyHack2026.git
cd EnergyHack2026
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:8050` in your browser.

---

## Background

The EnergyHack prompt focused on energy innovation in Texas. Jenna and I noticed that
ERCOT — the Texas grid operator — frequently sees solar overgeneration with no clear way to
redistribute or value that excess energy. Our solution: model the surplus as a tradeable
commodity, visualize it alongside real energy-sector financial instruments, and give a
spatial tool for understanding where generation happens relative to demand zones.
