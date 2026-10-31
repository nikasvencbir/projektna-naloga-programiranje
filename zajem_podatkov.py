"""Modul za prenos podatkov o borznih cenah elektrike in sončnem obsevanju."""
import os
import requests
import pandas as pd

#Določim pot do mape "podatki", ki sem jo ustvarila prej, sem se bojo shranjevali podatki iz spleta.
#__file__ je vgrajena Pythonova spremenljivka, ki hrani pot do trenutne datoteke (skripte), v kateri se ta koda izvaja.
# os.path.dirname- shrani pot do datoteke brez imena datoteke(mape)
MAPA_PODATKI = os.path.join(os.path.dirname(__file__),"podatki") #nastavi pot do nove mape(je še ne ustvari)
def prenesi_spot_cene(leto=2025, drzava="SI"): 
    #prenese urne SPOT cene za Slovenijo v letu 2025
    os.makedirs(MAPA_PODATKI, exist_ok=True) #make directories, ustvari mapo
    pot_datoteke = os.path.join(MAPA_PODATKI, f"spot_cene.csv") #nastavi pot+ime

    start = f"{leto}-01-01"
    end = f"{leto}-12-31"
    url = f"https://api.energy-charts.info/price?bzn={drzava}&start={start}&end={end}"
    print(f"Prenašam SPOT cene za državo {drzava} za leto {leto}...")
    #Sporoči morebitno napako
    odziv = requests.get(url, timeout=30)
    if odziv.status_code != 200: # 200-OK, 404-ne najde, 500-sesul se je streznik
        raise ConnectionError(f"Napaka pri prenosu SPOT cen: koda {odziv.status_code}")

    podatki = odziv.json() #pretvori v pythonov slovar iz surovega teksta
    casovni_zigi = pd.to_datetime(podatki["unix_seconds"], unit = "s") #iz unix časa(št sekund od 1970) da v berljiv datum
    cene = podatki ["price"]

    df_spot = pd.DataFrame({
        "Timestamp": casovni_zigi,
        "SPOT_EUR_MWh": cene
    })

    #Shranim v CSV
    df_spot.to_csv(pot_datoteke, index=False)
    print(f" -> SPOT cene uspešno shranjene v: {pot_datoteke} (št. vrstic: {len(df_spot)})")
    return df_spot

def prenesi_proizvodnjo(lat, lon, leto = 2020, moc_kw = 1.0):
    #privzete koordinate so LJ, jemljem iz API-ja PVGIS(Evropska komisija), vzamem normiran podatek
    os.makedirs(MAPA_PODATKI, exist_ok = True)
    pot_datoteke = os.path.join(MAPA_PODATKI, f"pvgis_proizvodnja.csv")
    url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
    parametri = {
        "lat": lat,
        "lon": lon,
        "peakpower": moc_kw, #nastavljena je na 1, da lahko delam z normiranim profilom
        "pvcalculation": 1, # da ne vrne samo obsevanosti ampak tudi izkoristek
        "optimalangles": 1, #idealni nagib se bo izračunal sam
        "outputformat": "json", #najboljši način za python
        "startyear": leto,      
        "endyear": leto,
        "loss": 14  #standardna privzeta vrednost v SLO     
    }
    print(f"[2/2] Prenašam podatke o sončnem obsevanju s PVGIS za lokacijo ({lat}, {lon})...")
    odziv = requests.get(url, params=parametri, timeout=30)
    if odziv.status_code != 200:
        raise ConnectionError(f"Napaka pri prenosu PVGIS podatkov: koda {odziv.status_code}")

    podatki = odziv.json()
    urna_serija = podatki["outputs"]["hourly"]
#    {
#  "inputs": {
#    "location": { "latitude": 46.0569, "longitude": 14.5058 },
#    "pv_module": { "peak_power": 1.0 }
#  },
#  "outputs": { <-----najprej določim naj to pogleda
#    "totals": { ... },
#    "hourly": [ <------potem določim naj to vzame za nov seznam, da dobim enostaven pythonov seznam z malomi slovarčki
#      {"time": "20200101:0010", "P": 0.0, "G(i)": 0.0},
#      {"time": "20200101:0110", "P": 0.0, "G(i)": 0.0},
#      ...
#      {"time": "20200101:1210", "P": 650.4, "G(i)": 710.2}
#    ]
#  }
#}

    casi = []
    moci_w = []
    for vnos in urna_serija:
        # Oblika časa v PVGIS: "20200101:0010"
        casi.append(pd.to_datetime(vnos["time"], format="%Y%m%d:%H%M"))
        moci_w.append(vnos["P"])  # Proizvedena električna moč v W

    df_pvgis = pd.DataFrame({
        "Timestamp": casi,
        "Proizvodnja_normirano": [p / 1000.0 for p in moci_w]  # Pretvornik v kWh za 1 kW SE
    })

    df_pvgis.to_csv(pot_datoteke, index=False)
    print(f" -> PVGIS podatki uspešno shranjeni v: {pot_datoteke} (št. vrstic: {len(df_pvgis)})")
    return df_pvgis

#if __name__ == "__main__": #da se ne izvaja če datoteko samo importam kam drugam
    vnos_lat = input(f"Vnesite zemljepisno širino, kjer bo postavljena SE (ali pritisnite Enter za Ljubljana): ").strip()
    if vnos_lat == "":
        lat = 46.0569
    else:
        try:
            lat = float(vnos_lat.replace(',','.'))
        except ValueError:
            print("Vaš vnos ni veljaven. Uporabljam privzeto vrednost (Ljubljana).")
    vnos_lon = input(f"Vnesite zemljepisno dolžino, kjer bo postavljena SE (ali pritisnite Enter za Ljubljana): ").strip()
    if vnos_lon == "":
        lon = 14.5058
    else:
        try:
            lon = float(vnos_lon.replace(',','.'))
        except ValueError:
            print("Vaš vnos ni veljaven. Uporabljam privzeto vrednost (Ljubljana).")
    print(f"Izbrana lokacija za SE: širina = {lat:.4f}, dolžina = {lon:.4f}")

    print("=== ZAGON PRENOSA PODATKOV S SPLETA ===")
    prenesi_spot_cene(leto=2024, drzava="SI")
    prenesi_proizvodnjo(lat, lon, leto=2020)
    print("=== PRENOS USPEŠNO ZAKLJUČEN ===")