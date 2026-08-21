"""Modul za prenos podatkov o borznih cenah elektrike in sončnem obsevanju."""
import os
import requests
import json
import pandas as pd

#Določim pot do mape "podatki", ki sem jo ustvarila prej, sem se bojo shranjevali podatki iz spleta.
MAPA_PODATKI = os.path.join(os.path.dirname(__file__),"podatki")
def prenesi_spot_cene(leto=2024, drzava="SI"): 
    #prenese urne SPOT cene za Slovenijo v letu 2025
    os.makedirs(MAPA_PODATKI, exist_ok=True)
    pot_datoteke = os.path.join(MAPA_PODATKI, f"spot_cene_{drzava}_{leto}.csv")

    start = f"{leto}-01-01"
    end = f"{leto}-12-31"
    url = f"https://api.energy-charts.info/price?bzn={drzava}&start={start}&end={end}"
    print(f"Prenašam SPOT cene za državo {drzava} za leto {leto}...")
    #Sporoči morebitno napako
    odziv = requests.get(url, timeout=30)
    if odziv.status_code != 200:
        raise ConnectionError(f"Napaka pri prenosu SPOT cen: koda {odziv.status_code}")

    podatki = odziv.json()
    casovni_zigi = pd.to_datetime(podatki["unix_seconds"], unit = "s")
    cene = podatki ["price"]

    df_spot = pd.DataFrame({
        "Timestamp": casovni_zigi,
        "SPOT_EUR_MWh": cene
    })

    #Shranim v CSV
    df_spot.to_csv(pot_datoteke, index=False)
    print(f" -> SPOT cene uspešno shranjene v: {pot_datoteke} (št. vrstic: {len(df_spot)})")
    return df_spot

def prenesi_proizvodnjo(lat = 46.0569, lon = 14.5058, leto = 2020, moc_kw = 1.0):
    #privzete koordinate so LJ, jemljem iz API-ja PVGIS(Evropska komisija), vzamem normiran podatek
    os.makedirs(MAPA_PODATKI, exist_ok = True)
    pot_datoteke = os.path.join(MAPA_PODATKI, f"pvgis_proizvodnja_{lat}_{lon}.csv")
    url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
    parametri = {
        "lat": lat,
        "lon": lon,
        "peakpower": moc_kw,
        "pvcalculation": 1,
        "optimalangles": 1,
        "outputformat": "json",
        "startyear": leto,      
        "endyear": leto,
        "loss": 14       
    }
    print(f"[2/2] Prenašam podatke o sončnem obsevanju s PVGIS za lokacijo ({lat}, {lon})...")
    odziv = requests.get(url, params=parametri, timeout=30)
    if odziv.status_code != 200:
        raise ConnectionError(f"Napaka pri prenosu PVGIS podatkov: koda {odziv.status_code}")

    podatki = odziv.json()
    urna_serija = podatki["outputs"]["hourly"]

    casi = []
    moci_w = []
    for vnos in urna_serija:
        # Oblika časa v PVGIS: "20200101:0010"
        casi.append(pd.to_datetime(vnos["time"], format="%Y%m%d:%H%M"))
        moci_w.append(vnos["P"])  # Moč v W

    df_pvgis = pd.DataFrame({
        "Timestamp": casi,
        "Proizvodnja_normirano": [p / 1000.0 for p in moci_w]  # Pretvornik v kWh za 1 kW SE
    })

    df_pvgis.to_csv(pot_datoteke, index=False)
    print(f" -> PVGIS podatki uspešno shranjeni v: {pot_datoteke} (št. vrstic: {len(df_pvgis)})")
    return df_pvgis

if __name__ == "__main__":
    print("=== ZAGON PRENOSA PODATKOV S SPLETA ===")
    prenesi_spot_cene(leto=2024, drzava="SI")
    prenesi_proizvodnjo(lat=46.0569, lon=14.5058, leto=2020)
    print("=== PRENOS USPEŠNO ZAKLJUČEN ===")