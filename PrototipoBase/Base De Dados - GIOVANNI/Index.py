from wsgiref import headers
import folium
from flask import Flask, request, jsonify, render_template_string
import threading
import webbrowser
import requests
import io
import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np

time_series_url = "https://api.giovanni.earthdata.nasa.gov/timeseries"
data = "GLDAS_NOAH025_3H_2_1_Tair_f_inst"

VAR_TEMP = "GLDAS_NOAH025_3H_2_1_Tair_f_inst"
VAR_QAIR = "GLDAS_NOAH025_3H_2_1_Qair_f_inst"
VAR_PRES = "GLDAS_NOAH025_3H_2_1_Psurf_f_inst"

token = "eyJ0eXAiOiJKV1QiLCJvcmlnaW4iOiJFYXJ0aGRhdGEgTG9naW4iLCJzaWciOiJlZGxqd3RwdWJrZXlfb3BzIiwiYWxnIjoiUlMyNTYifQ.eyJ0eXBlIjoiVXNlciIsInVpZCI6Imhpa2lrb21vcmkiLCJleHAiOjE3NjQ3ODkyNTksImlhdCI6MTc1OTYwNTI1OSwiaXNzIjoiaHR0cHM6Ly91cnMuZWFydGhkYXRhLm5hc2EuZ292IiwiaWRlbnRpdHlfcHJvdmlkZXIiOiJlZGxfb3BzIiwiYWNyIjoiZWRsIiwiYXNzdXJhbmNlX2xldmVsIjozfQ.YdNvDhPO1IfWWg2WSj5-rD05neTSOkzFIuNqlzyzTCD9SmXi4twZcbsf8jvL1HY277qgz9CVT-zrMeWJpRY77-ol95JdE7s8IRa7ZJmzQz0Usj4rUKQobemwVlJSYfpF_W5vq4YYGjBV47nmKLBP0jKS628nTfGc4jMDNsYmav72pmaM8JqcBZZnaFIPE8Z8lkxC9vgGX7cA3rbtj_HeBZRASGukmJFSmRyfzXWGGUcxN39Q8J1PJQVGnGMQQEPtRHVYWRDaIhuf6VCT8a2_pAyQ-dknZsh7lJhhHmxUhvXegzFMdDrQCAUlqrZiCXXkPoWpxGFpr7UowxIPQjcuSg"

app = Flask(__name__)
coords = {"lat": None, "lon": None}

TEMPLATE = """
<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <title>Mapa Interativo - NASA Giovanni</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {{ folium_map | safe }}

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

    <style>
        body {
            margin: 0;
            padding: 0;
        }

        #map {
            height: 100vh;
            width: 100vw;
        }
    </style>
</head>

<body>
    <div id="map"></div>

    <div class="modal fade" id="confirmModal" tabindex="-1" aria-labelledby="modalTitle" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title" id="modalTitle">Confirmar Localização</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"
                        aria-label="Fechar"></button>
                </div>
                <div class="modal-body">
                    <p>Você selecionou as coordenadas:</p>
                    <p><strong>Latitude:</strong> <span id="latText"></span></p>
                    <p><strong>Longitude:</strong> <span id="lonText"></span></p>
                    <p>Deseja enviar para o servidor e gerar o gráfico?</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="button" id="confirmBtn" class="btn btn-success">Confirmar</button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="TempoModal" tabindex="-1" aria-labelledby="modalTitle" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title" id="modalTitle">Confirmar Localização</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"
                        aria-label="Fechar"></button>
                </div>
                <div class="modal-body">
                    <p>Selecione a data de inicio e de fim do gráfico:</p>
                    <input id="startDate" type="date" />
                    <input id="endDate" type="date" />
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="button" id="confirmarData" class="btn btn-success">Confirmar</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const map = L.map('map').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 9,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        let selectedLat = null;
        let selectedLon = null;
        const modalEl = document.getElementById('confirmModal');
        const modalTempo = document.getElementById('TempoModal');
        const modal = new bootstrap.Modal(modalEl);
        const modal2 = new bootstrap.Modal(modalTempo);

        map.on('click', function (e) {
            selectedLat = e.latlng.lat.toFixed(3);
            selectedLon = e.latlng.lng.toFixed(3);

            document.getElementById('latText').textContent = selectedLat;
            document.getElementById('lonText').textContent = selectedLon;

            modal.show();
        });

        document.getElementById('confirmBtn').addEventListener('click', function () {
            modal.hide();
            modal2.show();
        });

        document.getElementById('confirmarData').addEventListener('click', function () {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            alert(`Selecionado: ${selectedLat}, ${selectedLon} de ${startDate} até ${endDate}`);
            fetch('/clicked', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: selectedLat, lon: selectedLon, startDate: startDate, endDate: endDate })
            });
        });
    </script>
"""

@app.route("/")
def index():
    m = folium.Map(location=[0, 0], zoom_start=2)
    map_html = m.get_root().render()
    return render_template_string(TEMPLATE, folium_map=map_html)

@app.route("/clicked", methods=["POST"])
def clicked():
    global coords
    coords.update(request.get_json())
    threading.Thread(
        target=process_data,
        args=(
            coords["lat"],
            coords["lon"],
            coords["startDate"],
            coords["endDate"],
        ),
    ).start()
    return jsonify(success=True)


def call_time_series(lat, lon, time_start, time_end, data):
    query_parameters = {
        "data": data,
        "location": f"[{lat},{lon}]",
        "time": f"{time_start}/{time_end}"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(time_series_url, params=query_parameters, headers=headers)
    return response.text

def parse_csv(ts):
    with io.StringIO(ts) as f:
        headers = {}
        for i in range(13):
            line = f.readline().strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                key, value = parts[0].strip(), ",".join(parts[1:]).strip()
                headers[key] = value
        df = pd.read_csv(
            f,
            header=1,
            names=("Timestamp", headers.get("param_name", "Value")),
            converters={"Timestamp": pd.Timestamp}
        )
    return headers, df

def relative_humidity(Qair, Psurf, Tair):
    P = Psurf / 100.0
    e = (Qair * P) / (0.622 + 0.378 * Qair)
    es = 6.112 * np.exp((17.67 * (Tair - 273.15)) / (Tair - 29.65))
    RH = (e / es) * 100.0
    return np.clip(RH, 0, 100)

def process_data(lat, lon, time_start, time_end):
    lat, lon = float(lat), float(lon)
    start = time_start + "T03:00:00"
    end = time_end + "T21:00:00"

    ts_temp = call_time_series(lat, lon, start, end, VAR_TEMP)
    ts_qair = call_time_series(lat, lon, start, end, VAR_QAIR)
    ts_pres = call_time_series(lat, lon, start, end, VAR_PRES)

    _, df_temp = parse_csv(ts_temp)
    _, df_qair = parse_csv(ts_qair)
    _, df_pres = parse_csv(ts_pres)
    print(df_temp.head())
    print(df_temp.info())

    for df in [df_temp, df_qair, df_pres]:
        for col in df.columns:
            if col != "Timestamp":
                df[col] = pd.to_numeric(df[col], errors="coerce")
    df = pd.merge(df_temp, df_qair, on="Timestamp", suffixes=("_T", "_Q"))
    df = pd.merge(df, df_pres, on="Timestamp")
    df.columns = ["Timestamp", "Tair", "Qair", "Psurf"]
    print(df.head())
    print(df.info())


    df["RH"] = df.apply(lambda r: relative_humidity(r.Qair, r.Psurf, r.Tair), axis=1)
    df["Tair_C"] = df["Tair"] - 273.15
    df["HeatIndex"] = df.apply(lambda r: heat_index(r.Tair_C, r.RH), axis=1)

    for col, color, label in [
        ("RH", "royalblue", "Umidade Relativa (%)"),
        ("HeatIndex", "orangered", "Sensação Térmica (°C)"),
        ("Tair_C", "forestgreen", "Temperatura do Ar (°C)"),
    ]:
        plt.figure(figsize=(10, 5))
        df.plot(x="Timestamp", y=col, color=color, label=label)
        plt.title(f"{label} - [{lat:.2f}, {lon:.2f}] ({start} → {end})")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"{col}.png", dpi=300)
        webbrowser.open(f"{col}.png")


def heat_index(temp_c: float, humidity: float) -> float:
    c1 = -8.78469475556
    c2 = 1.61139411
    c3 = 2.33854883889
    c4 = -0.14611605
    c5 = -0.012308094
    c6 = -0.0164248277778
    c7 = 0.002211732
    c8 = 0.00072546
    c9 = -0.000003582

    hi = (c1 + (c2 * temp_c) + (c3 * humidity) + (c4 * temp_c * humidity) +
          (c5 * temp_c*2) + (c6 * humidity*2) +
          (c7 * temp_c*2 * humidity) + (c8 * temp_c * humidity*2) +
          (c9 * temp_c*2 * humidity*2))

    return round(hi, 2)



def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    app.run(debug=False)
