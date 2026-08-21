"""Modul za prenos podatkov o borznih cenah elektrike in sončnem obsevanju."""
import os
import requests
import json
import pandas as pd

#Določim pot do mape "podatki", ki sem jo ustvarila prej, sem se bojo shranjevali podatki iz spleta.
MAPA_PODATKI = os.path.join(os.path.dirname(__file__),"podatki")
def prenesi_spot_cene(leto=2025, drzava="SI"): 
    #prenese urne SPOT cene za Slovenijo v letu 2025
    os.makedirs(MAPA_PODATKI, exist_ok=True)
    pot_datoteke = os.path.join(MAPA_PODATKI, f"spot_cene_{drzava}_{leto}.csv")

    url = f"https://api.energy-charts.info/price?country={drzava}"
    print(f"Prenašam SPOT cene za državo {drzava} za leto {leto}...")
    #Sporoči morebitno napako
    odziv = requests.get(url, timeout=30)
    if odziv.status_code != 200:
        raise ConnectionError(f"Napaka pri prenosu SPOT cen: koda {odziv.status_code}")

    podatki = odziv.json()
    casovni_zigi = pd.to_datatime(podatki["unix_seconds"], unit = "s")
    cene = podatki ["price"]

    df_spot = pd.DataFrame({
        "Timestamp": casovni_zigi,
        "SPOT_EUR_MWh": cene
    })

    #Filtrira za izbrano leto
    df_spot = df_spot[df_spot["Timestamp"].dt.year == leto].copy()
    #Shranim v CSV
    df_spot.to_csv(pot_datoteke, index=False)
    print(f" -> SPOT cene uspešno shranjene v: {pot_datoteke} (št. vrstic: {len(df_spot)})")
    return df_spot