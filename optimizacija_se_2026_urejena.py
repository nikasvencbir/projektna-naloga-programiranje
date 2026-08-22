import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. FUNKCIJE 
# ==========================================
limit_moci_kw = 300 #Ko boš konec z ostalim naredi da to uporabnik sam vnese
#-----Pomožni funkciji
def ocisti_ceno(tekst):
    if isinstance(tekst, str):
        stevilka_del = tekst.split(' ')[0]
        return float(stevilka_del.replace(',', '.'))
    return tekst
# 2. Oblikovanje številk (€ in vejice)- za lepši Excel
def formatiraj_eur(x):
    return f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

#-------Funkcije, ki jih uporabljam v izračunu
def izracunaj_f(i, p, s_base):
    S_i = s_base * i
    direktna_poraba = np.minimum(S_i, p)
    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)
    return np.sum(direktna_poraba) - np.sum(viski) - np.sum(manjki)

def izracunaj_f_ura(i, p, s_base):
    S_i = s_base * i
    direktna_poraba = np.minimum(S_i, p)
    viski = np.maximum(0, S_i - p)
    manjki = np.maximum(0, p - S_i)
    return np.sum(direktna_poraba) - np.sum(viski) - np.sum(manjki)

def izracunaj_f_spot(i, p, s_base, spot_podatki, cena1=5, cena2=5):
    S_i = s_base * i
    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)
    spot = spot_podatki / 1000
    return np.sum((spot - cena1/1000) * viski) - np.sum((spot + cena2/1000) * manjki)

def izracunaj_celotni_strosek(row, p, s_base, spot_podatki, cena_marza1=5, cena_marza2=5):
    moc_kw = row['Moc_SE_kW']
    capex_skupaj = row['CAPEX_EUR']
    i = moc_kw * 1050
    letni_strosek_capex = capex_skupaj / 30
    S_i = s_base * i
    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)
    direktna_poraba = np.minimum(S_i, p)
    marza1_kwh = cena_marza1 / 1000
    marza2_kwh = cena_marza2 / 1000
    spot_kwh = spot_podatki / 1000 
    prihranek_energija = np.sum(direktna_poraba * spot_kwh)
    zasluzek_viski = np.sum((spot_kwh - marza1_kwh) * viski)
    strosek_manjki = np.sum((spot_kwh + marza2_kwh) * manjki)
    return prihranek_energija + zasluzek_viski - strosek_manjki - letni_strosek_capex

def celotna_bilanca(row, p, s_base, stroski_df, spot_podatki, df_leto_ref, marza1=5):
    df_omreznina1 = df_leto_ref['Tarifa (VT/MT)']
    df_omreznina2 = stroski_df.loc['PowerNetworkFee', 'Cena_num']
    df_meritve    = stroski_df.loc['DutyMeteringPoint', 'Cena_num']
    df_OIEK       = stroski_df.loc['DutyOIEK', 'Cena_num']
    df_PiOI       = stroski_df.loc['DutyPiOI', 'Cena_num']
    df_trosarina  = stroski_df.loc['ExciseTax', 'Cena_num']
    spot_kwh = spot_podatki / 1000 
    marza1_kwh = marza1 / 1000
    
    # Razporeditev omrežnine
    omreznina_kwh = np.where(df_omreznina1 == "MT", 0.01695, 0.03724)
    
    moc_kw = row['Moc_SE_kW']
    capex_skupaj = row['CAPEX_EUR']
    letni_strosek_capex = capex_skupaj / 30
    i_energija = moc_kw * 1050
    S_i = s_base * i_energija
    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)
    limit = limit_moci_kw
    manjki_dejanski = np.minimum(manjki, limit)
    viski_dejanski = np.minimum(viski, limit)

    
    variabilni_strosek_kwh = spot_kwh + marza1_kwh + omreznina_kwh + df_OIEK + df_PiOI + df_trosarina
    strosek_nakupa = np.sum(manjki_dejanski * variabilni_strosek_kwh)  
    strosek_fiksni = (df_omreznina2 * limit_moci_kw) + (df_meritve * 12)
    zasluzek_viski = np.sum((spot_kwh - marza1_kwh) * viski_dejanski)
    skupni_letni_strosek = (strosek_fiksni + letni_strosek_capex + strosek_nakupa - zasluzek_viski) * 1.13

    return {
        'Skupaj' : skupni_letni_strosek,
        'Energija': np.sum(manjki * spot_kwh) * 1.13,
        'Omreznina': (np.sum(manjki * omreznina_kwh) + df_omreznina2 * limit_moci_kw) * 1.13,
        'Prispevki': (df_meritve * 12 + np.sum((df_OIEK + df_PiOI) * manjki)) * 1.13,
        'Trosarina': np.sum(df_trosarina * manjki) * 1.13,
        'CAPEX': letni_strosek_capex * 1.13,
        'Viski': zasluzek_viski * 1.13
    }

# ==========================================
# 2. PODATKI 
# ==========================================

MAPA_PODATKI = os.path.join(os.path.dirname(__file__), "podatki")
df_spot = pd.read_csv(os.path.join(MAPA_PODATKI, "spot_cene.csv"))
df_pvgis = pd.read_csv(os.path.join(MAPA_PODATKI, "pvgis_proizvodnja.csv"))

#Podatki iz mojih excelov(15-min meritve odjema, capex in tarife):
ostali_podatki = os.path.join(os.path.dirname(__file__), "Podatki_Optimizacija1.xlsx")
vsi_listi = pd.read_excel(ostali_podatki, sheet_name=None)
df_odjem_15min = vsi_listi["Telemetrija"]
df_capex = vsi_listi["Cenik_SE"]
df_stroski = vsi_listi["Tarife"].copy().set_index('Postavka')
df_stroski['Cena_num'] = df_stroski['Cena'].apply(ocisti_ceno)

#15-min podatke pretvorim v urne
df_odjem_15min['Timestamp'] = pd.to_datetime(df_odjem_15min['Timestamp'])
df_odjem_15min = df_odjem_15min.set_index('Timestamp')
df_odjem = df_odjem_15min.resample('1h').agg({
    'reg_A_plus': 'sum',
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
    'Proizvodnja_normirano': df_pvgis['Proizvodnja_normirano'].iloc[:st_ur].values / df_pvgis['Proizvodnja_normirano'].iloc[:st_ur].values.sum(),
    'Odjem_kWh': df_odjem['reg_A_plus'].iloc[:st_ur].values,
    'Tarifa (VT/MT)': df_odjem['Tarifa (VT/NT)'].iloc[:st_ur].values
})
#Vektorji za nadaljne računanje
poraba = df_leto['Odjem_kWh'].values
bazicna_proizvodnja = df_leto['Proizvodnja_normirano'].values
SPOT_cena = df_leto['SPOT_EUR_MWh'].values
tarifa = df_leto['Tarifa (VT/MT)'].values

# ==========================================
# 3. IZVEDBA (Izračuni in grafi)
# ==========================================

if __name__ == "__main__":
    print("OPTIMIZACIJA SONČNA ELEKTRARNA")
    print("-" * 60)

    # 1. Letna raven
    print("CILJ: največja samooskrbnost")
    velikosti = np.linspace(0.1, 1000000, 1000)
    rezultati = [izracunaj_f(i, poraba, bazicna_proizvodnja) for i in velikosti]
    optimalni_i = velikosti[np.argmax(rezultati)]
    print(f"Optimalna letna količna proizvedene energije: {optimalni_i:.2f} kWh")
    proizvodnja_optimalna = bazicna_proizvodnja * optimalni_i
    print(f"Optimalna velikost: {optimalni_i / 1050:.2f} kW")

    # Graf 1
    plt.figure(figsize=(15, 7))
    plt.plot(df_leto['Timestamp'], df_leto['Odjem_kWh'], label='Poraba', color='blue', alpha=0.7)
    plt.plot(df_leto['Timestamp'], proizvodnja_optimalna, label=f'Optimalna proizvodnja ({optimalni_i:.2f} kW)', color='orange', alpha=0.7)
    plt.title('Poraba in proizvodnja energije v letu 2026')
    plt.legend()
    plt.grid(True)

    # 2. Povprečne ure
    df_ura = df_leto.groupby(df_leto['Timestamp'].dt.hour).mean(numeric_only=True)
    povprecna_poraba = df_ura['Odjem_kWh'].values
    povprečna_proizvodnja = df_ura['Proizvodnja_normirano'].values
    
    rezultati_ura = [izracunaj_f_ura(i, povprecna_poraba, povprečna_proizvodnja) for i in velikosti]
    optimalni_i_ura = velikosti[np.argmax(rezultati_ura)]
    print(f"Optimalna dnevna količna proizvedene energije: {optimalni_i_ura:.2f} kWh")
    print(f"Optimalna velikost: {optimalni_i_ura / 1050:.2f} kW")

    # Graf 2
    plt.figure(figsize=(12, 6))
    ure = range(24)
    proizvodnja_optimalna_ura = povprečna_proizvodnja * optimalni_i_ura
    plt.plot(ure, povprecna_poraba, label='Povprečna poraba', marker='o')
    plt.plot(ure, proizvodnja_optimalna_ura, label='Optimalna proizvodnja', marker='s')
    plt.fill_between(ure, np.minimum(povprecna_poraba, proizvodnja_optimalna_ura), color='green', alpha=0.2)
    plt.title('Poraba in proizvodnja v povprečnem dnevu')
    plt.legend()
    plt.grid(True)

    # 3. SPOT optimizacija
    print("-" * 60)
    print("CILJ: najnižji stroški - samo SPOT")
    rezultati_spot = [izracunaj_f_spot(i, poraba, bazicna_proizvodnja, SPOT_cena) for i in velikosti]
    optimalni_i_spot = velikosti[np.argmax(rezultati_spot)]
    print(f"Optimalna letna količna (SPOT): {optimalni_i_spot:.2f} kWh")
    print(f"Optimalna velikost naprave (SPOT): {optimalni_i_spot / 1050:.2f} kW")

    # 4. CAPEX + SPOT
    scenariji = df_capex.copy()
    scenariji['Bilanca_EUR'] = scenariji.apply(lambda row: izracunaj_celotni_strosek(row, poraba, bazicna_proizvodnja, SPOT_cena), axis=1)
    najboljsa_opcija_capex = scenariji.loc[scenariji['Bilanca_EUR'].idxmax()]
    print("-" * 60)
    print(" CILJ: najnižji stroški SPOT + CAPEX ")
    print(f"Najboljša moč elektrarne: {najboljsa_opcija_capex['Moc_SE_kW']} kW")
    print(f"Letna bilanca: {najboljsa_opcija_capex['Bilanca_EUR']:.2f} €")
    
    strosek_brez_SE_osnovni = np.sum(poraba * (SPOT_cena/1000 + 5/1000))
    print(f"Strošek BREZ sončne elektrarne: -{strosek_brez_SE_osnovni:.2f} €")
    print(f"Z elektrarno prihraniš: {najboljsa_opcija_capex['Bilanca_EUR'] + strosek_brez_SE_osnovni:.2f} € na leto")

    # 5. Celotna bilanca
    print("-" * 60)
    print("CILJ: NAJNIŽJI CELOTNI LETNI STROŠEK")
    scenariji['Rezultat_dict'] = scenariji.apply(lambda row: celotna_bilanca(row, poraba, bazicna_proizvodnja, df_stroski, SPOT_cena, df_leto), axis=1)
    scenariji['Strosek_EUR'] = scenariji['Rezultat_dict'].apply(lambda x: x['Skupaj'])
    
    # Izračun stanja BREZ SE
    omr_kwh_brez = np.where(df_leto['Tarifa (VT/MT)'] == "MT", 0.01695, 0.03724)
    strosek_fiksni_brez = (df_stroski.loc['PowerNetworkFee','Cena_num'] * limit_moci_kw) + (df_stroski.loc['DutyMeteringPoint','Cena_num'] * 12)
    var_strosek_brez = SPOT_cena/1000 + 5/1000 + omr_kwh_brez + df_stroski.loc['DutyOIEK','Cena_num'] + df_stroski.loc['DutyPiOI','Cena_num'] + df_stroski.loc['ExciseTax','Cena_num']
    strosek_brez_SE_full = (np.sum(poraba * var_strosek_brez) + strosek_fiksni_brez) * 1.13
    
    najboljsa_opcija_final = scenariji.loc[scenariji['Strosek_EUR'].idxmin()]
    print(f"Optimalna velikost: {najboljsa_opcija_final['Moc_SE_kW']} kW")
    print(f"Letni strošek s SE: {najboljsa_opcija_final['Strosek_EUR']:.2f} €")
    print(f"Letni strošek brez SE: {strosek_brez_SE_full:.2f} €")
    print(f"Prihranek s SE: {strosek_brez_SE_full - najboljsa_opcija_final['Strosek_EUR']:.2f} €")

    # Rezultati za vse velikosti
    print("-" * 60)
    print(" REZULTATI ZA VSE VELIKOSTI SE ")
    edv_seznam, donosnost_seznam = [], []
    for idx, row in scenariji.iterrows():
        prihranek_v = strosek_brez_SE_full - row['Strosek_EUR']
        edv_v = row['CAPEX_EUR'] / prihranek_v if prihranek_v > 0 else 0
        edv_seznam.append(edv_v)
        donosnost_seznam.append((prihranek_v * 30) / row['CAPEX_EUR'])
        print(f"Velikost SE: {row['Moc_SE_kW']:7.1f} kW | EDV: {edv_v:5.3f} let | Letni prihranek: {prihranek_v:5.2f} €")
    
    scenariji['EDV_let'] = edv_seznam
    najboljsa_edv = scenariji.loc[scenariji['EDV_let'][scenariji['EDV_let']>0].idxmin()]
    opt_res_edv = najboljsa_edv['Rezultat_dict']

    # Tabela primerjave
    strosek_brez_spot = np.sum(poraba * (SPOT_cena/1000 + 5/1000)) * 1.13
    strosek_brez_omr = (np.sum(poraba * omr_kwh_brez) + df_stroski.loc['PowerNetworkFee','Cena_num']* limit_moci_kw) * 1.13
    strosek_brez_pris = (df_stroski.loc['DutyMeteringPoint','Cena_num']*12 + np.sum((df_stroski.loc['DutyOIEK','Cena_num']+df_stroski.loc['DutyPiOI','Cena_num'])*poraba)) * 1.13
    strosek_brez_tros = np.sum(df_stroski.loc['ExciseTax','Cena_num'] * poraba) * 1.13
    print("-" * 60)
    print("OPTIMALNA VELIKOST GLEDE NA EDV:")
    print(f"Optimalna velikost: {najboljsa_edv['Moc_SE_kW']} kW")
    print(f"Letni strošek s SE: {najboljsa_edv['Strosek_EUR']:.2f} €")
    print(f"Letni strošek brez SE: {strosek_brez_SE_full:.2f} €")
    prihranek_edv = strosek_brez_SE_full - najboljsa_edv['Strosek_EUR']
    print(f"Prihranek s SE: {prihranek_edv:.2f} €")
    print(f"EDV: {najboljsa_edv['EDV_let']:.2f} let")
    opt_res_edv = najboljsa_edv['Rezultat_dict']
    primerjava = {
        'Kategorija': ['Znesek energije', 'Znesek omrežnine', 'Znesek ostalih prispevkov', 'Znesek trošarine', 'Zaslužek od viškov', 'Znesek capex', 'SKUPAJ'],
        'Strošek pred': [round(strosek_brez_spot, 2), round(strosek_brez_omr, 2), round(strosek_brez_pris, 2), round(strosek_brez_tros, 2), 0, 0, round(strosek_brez_SE_full, 2)],
        'Strošek po': [opt_res_edv['Energija'], opt_res_edv['Omreznina'], opt_res_edv['Prispevki'], opt_res_edv['Trosarina'], -opt_res_edv['Viski'], opt_res_edv['CAPEX'], opt_res_edv['Skupaj']]
    }
    print("\nOcena letnega prihranka s sončno elektrarno:")
    print(pd.DataFrame(primerjava))

    # Končni graf
    plt.figure(figsize=(10,6))
    plt.plot(scenariji['Moc_SE_kW'], scenariji['EDV_let'], marker='o', color='blue')
    plt.title('Ekonomska doba vračanja (EDV) glede na moč SE')
    plt.xlabel('Moč SE [kW]')
    plt.ylabel('EDV [leta]')
    plt.grid(True)
    plt.show()

    #excel tabela:
    # 1. Priprava podatkov za tabelo (izračunamo še stolpec Prihranek)
    df_koncna_tabela = pd.DataFrame(primerjava)
    
    # Prepričamo se, da so vrednosti številke
    df_koncna_tabela['Strošek pred'] = pd.to_numeric(df_koncna_tabela['Strošek pred'])
    df_koncna_tabela['Strošek po'] = pd.to_numeric(df_koncna_tabela['Strošek po'])
    
    # Izračunamo prihranek
    df_koncna_tabela['Prihranek'] = df_koncna_tabela['Strošek pred'] - df_koncna_tabela['Strošek po']
    
    
    # Ustvarimo kopijo za izvoz, da ne pokvarimo originalnih številk za izračune
    df_za_export = df_koncna_tabela.copy()
    for col in ['Strošek pred', 'Strošek po', 'Prihranek']:
        df_za_export[col] = df_za_export[col].apply(formatiraj_eur)
    
    # 3. Izvoz v Excel
    ime_datoteke = f"Rezultati_Optimizacije_{najboljsa_edv['Moc_SE_kW']}kW.xlsx"
    df_za_export.to_excel(ime_datoteke, index=False)
    
    print(f"\n[USPEH] Rezultati so shranjeni v datoteko: {ime_datoteke}")
    