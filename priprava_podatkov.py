import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#Podatki iz interneta
MAPA_PODATKI = os.path.join(os.path.dirname(__file__), "podatki")
df_spot = pd.read_csv(os.path.join(MAPA_PODATKI, "spot_cene_SI_2025.csv"))
df_pvgis = pd.read_csv(os.path.join(MAPA_PODATKI, "pvgis_proizvodnja_46.0569_14.5058.csv"))

#Podatki iz mojih excelov(15-min meritve odjema, capex in tarife):
ostali_podatki = "Podatki_Optimizacija1"
vsi_listi = pd.read_excel(ostali_podatki, sheet_name=None)
df_odjem_15min = vsi_listi["Telemetrija"]
df_capex = vsi_listi["Cenik_SE"]
df_stroski = vsi_listi["Tarife"]

#15-min podatke pretvorim v urne
df_odjem_15min['Timestamp'] = pd.to_datetime(df_odjem_15min['Timestamp'])
df_odjem_15min = df_odjem_15min.set_index('Timestamp')
df_odjem = df_odjem_15min.resample('1h').agg({
    'Odjem_kWh': 'sum',
    'Tarifa (VT/NT)': 'first'
}).reset_index()


df_spot['Timestamp'] = pd.to_datetime(df_spot['Timestamp'])
df_pvgis['Timestamp'] = pd.to_datetime(df_pvgis['Timestamp'])
#varovalka, če bi izbrali kombinacijo let, ki nimajo isto dni
st_ur = min(len(df_spot), len(df_pvgis), len(df_odjem))

#združitev
df_leto = pd.DataFrame({
    'Timestamp': df_spot['Timestamp'].iloc[:st_ur].values,
    'SPOT_EUR_MWh': df_spot['SPOT_EUR_MWh'].iloc[:st_ur].values,
    'Proizvodnja_normirano': df_pvgis['Proizvodnja_normirano'].iloc[:st_ur].values,
    'Odjem_kWh': df_odjem['Odjem_kWh'].iloc[:st_ur].values,
    'Tarifa (VT/MT)': df_odjem['Tarifa (VT/NT)'].iloc[:st_ur].values
})
#Vektorji za nadaljne računanje
poraba = df_leto['Odjem_kWh'].values
bazicna_proizvodnja = df_leto['Proizvodnja_normirano'].values
SPOT_cena = df_leto['SPOT_EUR_MWh'].values
tarifa = df_leto['Tarifa (VT/MT)'].values
