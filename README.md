# ⚡ Specusol — Texas Solar Stock Market Dashboard

> Built at **EnergyHack @ Georgia Tech** (January 2026) · 24-hour hackathon project  
> 🏆 Live demo: [energyhack2026.onrender.com](https://energyhack2026.onrender.com)

---

## What It Does

Specusol is an interactive web dashboard that treats excess Texas solar energy as a tradeable financial asset. The core idea: solar farms on the ERCOT grid routinely generate more energy than the grid can use — so what if that surplus could be redirected and valued like a stock?

The app gives energy analysts and grid operators a single view of:

- **Real-time supply vs. demand curves** for residential and commercial solar across a 24-hour cycle
- **ERCOT zone verification** — enter any Texas address and the app maps it to its ERCOT grid zone (North, South, West, Houston) using live geolocation
- **Solar stock market tracker** — compare Texas-relevant equities (TAN, ENPH, VLO, FSLR, WHD) with candlestick charts, trend overlays, and options Greeks
- **7-hour localized weather forecast** with solar irradiance estimates (W/m²) and temperature in Fahrenheit
- **Grid health analytics** — live carbon intensity and grid frequency estimates, with the underlying formulas displayed for transparency

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Web Framework | Plotly Dash + Dash Bootstrap Components |
| Mapping | Dash Leaflet (CartoDB dark tile layer) |
| Data / Math | NumPy, Pandas, SciPy (linear regression) |
| Geolocation | Geopy / Nominatim |
| Deployment | Render (live, public URL) |

---

## Key Features in the Code

**Supply/Demand Equilibrium Detection** (`app.py` lines ~160–170)  
Uses NumPy sign-change detection on the difference between total supply and demand curves to automatically annotate the market equilibrium point on the chart.

**ERCOT Zone Boundary Logic** (`app.py` lines ~35–40)  
Custom zone definitions using lat/lon bounding boxes for ERCOT's North, South, West, and Houston zones — implemented in pure Python for deployment stability on Render (no geospatial library dependencies).

**Solar Irradiance Model** (`app.py` lines ~145–148)  
Models daylight output using a Gaussian curve centered at 1:15 PM (`e^(-(t-13.25)²/2·2.5²) × 1000 W/m²`), giving a physically realistic bell-curve shape for solar generation throughout the day.

**Options Greeks Display**  
Displays Option Delta and Trend Confidence for solar asset portfolios, with a plain-English explanation of what the metrics mean for hedging against ERCOT volatility.

---

## How to Run Locally

```bash
git clone https://github.com/cindy-muniz/EnergyHack2026.git
cd EnergyHack2026
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:8050` in your browser.

---

## Background

This project was built collaboratively with teammate **Jenna** during EnergyHack 2026 at Georgia Tech. The hackathon prompt focused on energy innovation in Texas. We identified that ERCOT — the Texas grid operator — frequently experiences solar overgeneration with no clear mechanism for redistributing or valuing that excess energy.

Our solution: model the surplus as a tradeable commodity, visualize it alongside real financial instruments in the Texas energy sector, and give grid operators a spatial tool to understand where generation is happening relative to demand zones.

The Specusol repo (`github.com/cindy-muniz/Specusol`) contains the extended solo development of this idea, adding deeper analytics and map features beyond what was built during the 24-hour window.

---

## Project Structure

```
EnergyHack2026/
├── app.py              # Main Dash application (all logic and layout)
├── requirements.txt    # Python dependencies
└── assets/
    └── logo.png        # Specusol branding asset
```
