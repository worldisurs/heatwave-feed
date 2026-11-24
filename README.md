# Heat Wave BD — data feed

This repository holds the data file for the তাপপ্রবাহ সতর্কতা app.

- `fetch_forecast.py` fetches the ECMWF IFS forecast for all 64 district
  towns of Bangladesh from Open-Meteo in one call, applies the BMD heat
  wave rule, and writes `forecast.json`.
- A GitHub Actions job runs the script every 6 hours and saves the new
  `forecast.json`.
- GitHub Pages serves `forecast.json` at a public address. The app reads
  the file from that address.

Data source: Open-Meteo (model ECMWF IFS). Free non-commercial use.
