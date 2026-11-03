import os
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


def ocisti_ceno(tekst):
    if isinstance(tekst, str):
        # Poiščemo prvi pojav števila (števke, ki imajo lahko vmes vejico ali piko)
        ujemanje = re.search(r"\d+(?:[.,]\d+)?", tekst)
        if ujemanje:
            # Vzamemo najdeni del, zamenjamo vejico s piko in pretvorimo v float
            return float(ujemanje.group(0).replace(",", "."))
    return tekst


def formatiraj_eur(x):  # X je zato da nimam hkrati samih pik oz samih vejic
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def izracunaj_f(
    i, p, s_base
):  # ta samo pogleda katera sončna elektrarna najbolj pokrije porabo in ima najmanj viškov in manjkov
    S_i = s_base * i  # proizvodnja
    direktna_poraba = np.minimum(S_i, p)
    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)
    return np.sum(direktna_poraba) - np.sum(viski) - np.sum(manjki)


def celotna_bilanca(
    row,
    p,
    s_base,
    stroski_df,
    spot_podatki,
    df_leto_ref,
    marza1=5,
    limit_moci_kw=300,
):
    df_omreznina1 = df_leto_ref["Tarifa (VT/NT)"]  # rabim cel stolpec
    df_omreznina2 = stroski_df.loc[
        "PowerNetworkFee", "Cena_num"
    ]  # rabim določeno celico
    df_meritve = stroski_df.loc["DutyMeteringPoint", "Cena_num"]
    df_OIEK = stroski_df.loc["DutyOIEK", "Cena_num"]
    df_PiOI = stroski_df.loc["DutyPiOI", "Cena_num"]
    df_trosarina = stroski_df.loc["ExciseTax", "Cena_num"]

    spot_kwh = spot_podatki / 1000
    marza1_kwh = marza1 / 1000
    omreznina_kwh = np.where(df_omreznina1 == "NT", 0.01695, 0.03724)
    moc_kw = row["Moc_SE_kW"]  # vzamemo moč elektrarne v vrstici(row)
    capex_skupaj = row["CAPEX_EUR"]
    letni_strosek_capex = capex_skupaj / 30  # 30 letna amortizacija
    i_energija = moc_kw * 1050
    S_i = s_base * i_energija

    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)

    viski_dejanski = np.minimum(viski, limit_moci_kw)
    variabilni_strosek_kwh = (
        spot_kwh
        + marza1_kwh
        + omreznina_kwh
        + df_OIEK
        + df_PiOI
        + df_trosarina
    )
    strosek_nakupa = np.sum(manjki * variabilni_strosek_kwh)
    strosek_fiksni = (df_omreznina2 * limit_moci_kw) + (df_meritve * 12)
    zasluzek_viski = np.sum((spot_kwh - marza1_kwh) * viski_dejanski)
    skupni_letni_strosek = (
        strosek_fiksni + letni_strosek_capex + strosek_nakupa - zasluzek_viski
    ) * 1.13
    return {
        "Skupaj": skupni_letni_strosek,
        "Energija": np.sum(manjki * spot_kwh) * 1.13,
        "Omreznina": (
            np.sum(manjki * omreznina_kwh) + df_omreznina2 * limit_moci_kw
        )
        * 1.13,
        "Prispevki": (df_meritve * 12 + np.sum((df_OIEK + df_PiOI) * manjki))
        * 1.13,
        "Trosarina": np.sum(df_trosarina * manjki) * 1.13,
        "CAPEX": letni_strosek_capex * 1.13,
        "Viski": zasluzek_viski * 1.13,
    }


# 1. Funkcija za omejitev moči (tvoj vnos in preverjanje):
def doloci_omejitev_moci(vnos_moc=None):
    if vnos_moc is None or str(vnos_moc).strip() == "":
        limit_moci_kw = 300.0
    else:
        try:
            limit_moci_kw = float(str(vnos_moc).replace(",", "."))
        except ValueError:
            print("Vaš vnos ni veljaven. Uporabljam privzeto vrednost 300 kW.")
            limit_moci_kw = 300.0

    print(f"Izbrana omejitev moči: {limit_moci_kw:.1f} kW")
    return limit_moci_kw


# 2. Glavna funkcija za branje, pretvorbo in združevanje:
def nalozi_in_pripravi_podatke(vnos_datoteka=None):
    # Vnos lastne telemetrije:
    privzeta_datoteka = "Podatki_Optimizacija1.xlsx"

    if vnos_datoteka is None or str(vnos_datoteka).strip() == "":
        pot_excel = os.path.join(os.getcwd(), privzeta_datoteka)
    else:
        pot_excel = os.path.join(os.getcwd(), str(vnos_datoteka).strip())

    if not os.path.exists(pot_excel):
        print(
            f"OPOZORILO: Datoteka '{pot_excel}' ne obstaja! Uporabljena bo privzeta datoteka '{privzeta_datoteka}'."
        )
        pot_excel = os.path.join(os.getcwd(), privzeta_datoteka)

    print(f"Berem podatke iz: {os.path.basename(pot_excel)}")

    MAPA_PODATKI = os.path.join(os.getcwd(), "podatki")
    df_spot = pd.read_csv(os.path.join(MAPA_PODATKI, "spot_cene.csv"))
    df_pvgis = pd.read_csv(os.path.join(MAPA_PODATKI, "pvgis_proizvodnja.csv"))

    # Podatki iz mojih excelov(15-min meritve odjema, capex in tarife):
    vsi_listi = pd.read_excel(
        pot_excel, sheet_name=None
    )  # sheet_name = None pomeni da prebere vse liste v excelu
    df_odjem_15min = vsi_listi["Telemetrija"]
    df_capex = vsi_listi["Cenik_SE"]
    df_stroski = (
        vsi_listi["Tarife"].copy().set_index("Postavka")
    )  # Stolpec 'Postavka' nastavi kot indeks tabele
    df_stroski["Cena_num"] = df_stroski["Cena"].apply(
        ocisti_ceno
    )  # .apply pokliče funkcijo za vsako vrstico

    # 15-min podatke pretvorim v urne
    df_odjem_15min["Timestamp"] = pd.to_datetime(df_odjem_15min["Timestamp"])
    df_odjem_15min = df_odjem_15min.set_index(
        "Timestamp"
    )  # vrstice seindeksirajo po času, timestamp ni več navaden stolpec
    df_odjem = (
        df_odjem_15min.resample("1h")
        .agg({  # grupira podatke po urah
            "reg_A_plus": "sum",  # porabe seštejem
            "Tarifa (VT/NT)": "first",  # za tarifo uporabim tisto ki je bila prva
        })
        .reset_index()
    )

    df_spot["Timestamp"] = pd.to_datetime(df_spot["Timestamp"])
    df_pvgis["Timestamp"] = pd.to_datetime(df_pvgis["Timestamp"])

    # varovalka, če bi izbrali kombinacijo let, ki nimajo isto dni
    st_ur = min(len(df_spot), len(df_pvgis), len(df_odjem))

    # združitev
    df_leto = pd.DataFrame({
        "Timestamp": df_spot["Timestamp"].iloc[:st_ur].values,
        "SPOT_EUR_MWh": df_spot["SPOT_EUR_MWh"].iloc[:st_ur].values,
        "Proizvodnja_normirano": df_pvgis["Proizvodnja_normirano"]
        .iloc[:st_ur]
        .values
        / df_pvgis["Proizvodnja_normirano"].iloc[:st_ur].values.sum(),
        "Odjem_kWh": df_odjem["reg_A_plus"].iloc[:st_ur].values,
        "Tarifa (VT/NT)": df_odjem["Tarifa (VT/NT)"].iloc[:st_ur].values,
    })

    # Vektorji za nadaljne računanje
    poraba = df_leto["Odjem_kWh"].values
    bazicna_proizvodnja = df_leto["Proizvodnja_normirano"].values
    SPOT_cena = df_leto["SPOT_EUR_MWh"].values
    tarifa = df_leto["Tarifa (VT/NT)"].values

    return (
        df_leto,
        df_capex,
        df_stroski,
        poraba,
        bazicna_proizvodnja,
        SPOT_cena,
        tarifa,
    )


def optimiziraj_samooskrbnost(
    poraba,
    bazicna_proizvodnja,
    izracunaj_f,
    min_velikost=0.1,
    max_velikost=1000000,
    korakov=1000,
):
    print("OPTIMIZACIJA SONČNA ELEKTRARNA")
    print("-" * 60)
    print("CILJ: največja samooskrbnost")

    velikosti = np.linspace(
        min_velikost, max_velikost, korakov
    )  # tu so velikosti glede na letno proizvedeno energijo
    rezultati = [izracunaj_f(i, poraba, bazicna_proizvodnja) for i in velikosti]
    optimalni_i = velikosti[
        np.argmax(rezultati)
    ]  # argmax izlušči indeks od najboljšega rezultata
    proizvodnja_optimalna = bazicna_proizvodnja * optimalni_i

    print(
        f"Optimalna letna količna proizvedene energije: {optimalni_i:.2f} kWh"
    )
    print(f"Optimalna velikost: {optimalni_i / 1050:.2f} kW")

    return optimalni_i, proizvodnja_optimalna


def narisi_analizo_proizvodnje(df_leto, optimalni_i, proizvodnja_optimalna):
    # Graf 1: Celoletna primerjava
    plt.figure(figsize=(20, 7))
    plt.plot(
        df_leto["Timestamp"],
        df_leto["Odjem_kWh"],
        label="Poraba",
        color="blue",
        alpha=0.7,
    )
    plt.plot(
        df_leto["Timestamp"],
        proizvodnja_optimalna,
        label=f"Optimalna proizvodnja ({optimalni_i:.2f} kW)",
        color="orange",
        alpha=0.7,
    )
    plt.title("Poraba in proizvodnja energije v letu 2026")
    plt.legend()
    plt.grid(True)  # pomožna mreža v ozadju
    plt.show()

    # 2. Povprečne ure
    df_ura = df_leto.groupby(df_leto["Timestamp"].dt.hour).mean(
        numeric_only=True
    )  # razvrsti skupaj podatke z istimi urami in (samo za številske) izračuna povprečje
    povprecna_poraba = df_ura["Odjem_kWh"].values
    povprečna_proizvodnja = df_ura["Proizvodnja_normirano"].values

    # Graf 2: Povprečni dan
    plt.figure(figsize=(12, 6))
    ure = range(24)
    proizvodnja_optimalna_ura = povprečna_proizvodnja * optimalni_i
    plt.plot(ure, povprecna_poraba, label="Povprečna poraba", marker="o")
    plt.plot(
        ure, proizvodnja_optimalna_ura, label="Optimalna proizvodnja", marker="s"
    )
    plt.fill_between(
        ure,
        np.minimum(povprecna_poraba, proizvodnja_optimalna_ura),
        color="green",
        alpha=0.2,
    )
    plt.title("Poraba in proizvodnja v povprečnem dnevu")
    plt.legend()
    plt.grid(True)
    plt.show()


def analiza_ekonomike(
    df_capex,
    df_stroski,
    df_leto,
    poraba,
    bazicna_proizvodnja,
    SPOT_cena,
    limit_moci_kw,
):
    scenariji = df_capex.copy()

    # 5. Celotna bilanca
    print("-" * 60)
    print("CILJ: NAJNIŽJI CELOTNI LETNI STROŠEK - brez upoštevanja capex")
    scenariji["Rezultat_dict"] = scenariji.apply(
        lambda row: celotna_bilanca(
            row,
            poraba,
            bazicna_proizvodnja,
            df_stroski,
            SPOT_cena,
            df_leto,
            limit_moci_kw=limit_moci_kw,
        ),
        axis=1,
    )
    scenariji["Strosek_EUR"] = scenariji["Rezultat_dict"].apply(
        lambda x: x["Skupaj"]
    )

    # Izračun stanja BREZ SE
    omr_kwh_brez = np.where(df_leto["Tarifa (VT/NT)"] == "NT", 0.01695, 0.03724)
    strosek_brez_spot = np.sum(poraba * (SPOT_cena / 1000 + 5 / 1000)) * 1.13
    strosek_brez_omr = (
        np.sum(poraba * omr_kwh_brez)
        + df_stroski.loc["PowerNetworkFee", "Cena_num"] * limit_moci_kw
    ) * 1.13
    strosek_brez_pris = (
        df_stroski.loc["DutyMeteringPoint", "Cena_num"] * 12
        + np.sum(
            (
                df_stroski.loc["DutyOIEK", "Cena_num"]
                + df_stroski.loc["DutyPiOI", "Cena_num"]
            )
            * poraba
        )
    ) * 1.13
    strosek_brez_tros = (
        np.sum(df_stroski.loc["ExciseTax", "Cena_num"] * poraba) * 1.13
    )
    strosek_brez_SE_full = (
        strosek_brez_spot
        + strosek_brez_omr
        + strosek_brez_pris
        + strosek_brez_tros
    )

    najboljsa_opcija_final = scenariji.loc[scenariji["Strosek_EUR"].idxmin()]
    print(f"Optimalna velikost: {najboljsa_opcija_final['Moc_SE_kW']} kW")
    print(f"Letni strošek s SE: {najboljsa_opcija_final['Strosek_EUR']:.2f} €")
    print(f"Letni strošek brez SE: {strosek_brez_SE_full:.2f} €")
    print(
        f"Prihranek s SE: {strosek_brez_SE_full - najboljsa_opcija_final['Strosek_EUR']:.2f} €"
    )

    # Rezultati za vse velikosti
    print("-" * 60)
    print(" REZULTATI ZA VSE VELIKOSTI SE ")
    edv_seznam = []
    for idx, row in scenariji.iterrows():
        prihranek_v = strosek_brez_SE_full - row["Strosek_EUR"]
        edv_v = row["CAPEX_EUR"] / prihranek_v if prihranek_v > 0 else 0
        edv_seznam.append(edv_v)
        donosnost_v = (prihranek_v * 30) / row["CAPEX_EUR"]
        print(
            f"Velikost SE: {row['Moc_SE_kW']:7.1f} kW | EDV: {edv_v:5.3f} let | Letni prihranek: {prihranek_v:5.2f} € | Donosnost: {donosnost_v:5.2f} %"
        )

    scenariji["EDV_let"] = edv_seznam
    najboljsa_edv = scenariji.loc[
        scenariji["EDV_let"][scenariji["EDV_let"] > 0].idxmin()
    ]
    opt_res_edv = najboljsa_edv["Rezultat_dict"]

    # Tabela primerjave
    print("-" * 60)
    print("OPTIMALNA VELIKOST GLEDE NA EDV:")
    print(f"Optimalna velikost: {najboljsa_edv['Moc_SE_kW']} kW")
    print(f"Letni strošek s SE: {najboljsa_edv['Strosek_EUR']:.2f} €")
    print(f"Letni strošek brez SE: {strosek_brez_SE_full:.2f} €")
    prihranek_edv = strosek_brez_SE_full - najboljsa_edv["Strosek_EUR"]
    print(f"Prihranek s SE: {prihranek_edv:.2f} €")
    print(f"EDV: {najboljsa_edv['EDV_let']:.2f} let")

    primerjava = {
        "Kategorija": [
            "Znesek energije",
            "Znesek omrežnine",
            "Znesek ostalih prispevkov",
            "Znesek trošarine",
            "Zaslužek od viškov",
            "Znesek capex",
            "SKUPAJ",
        ],
        "Strošek pred": [
            round(strosek_brez_spot, 2),
            round(strosek_brez_omr, 2),
            round(strosek_brez_pris, 2),
            round(strosek_brez_tros, 2),
            0,
            0,
            round(strosek_brez_SE_full, 2),
        ],
        "Strošek po": [
            opt_res_edv["Energija"],
            opt_res_edv["Omreznina"],
            opt_res_edv["Prispevki"],
            opt_res_edv["Trosarina"],
            -opt_res_edv["Viski"],
            opt_res_edv["CAPEX"],
            opt_res_edv["Skupaj"],
        ],
    }
    print("\nOcena letnega prihranka s sončno elektrarno:")
    print(pd.DataFrame(primerjava))

    # TUKAJ rešimo manjkajoči spremenljivki:
    df_ura = df_leto.groupby(df_leto["Timestamp"].dt.hour).mean(
        numeric_only=True
    )
    povprecna_poraba = df_ura["Odjem_kWh"].values
    povprečna_proizvodnja = df_ura["Proizvodnja_normirano"].values

    # Graf - dnevna samooskrba
    plt.figure(figsize=(12, 6))
    ure = range(24)
    proizvodnja_optimalna_ura = (
        povprečna_proizvodnja * najboljsa_edv["Moc_SE_kW"] * 1050
    )
    plt.plot(ure, povprecna_poraba, label="Povprečna poraba", marker="o")
    plt.plot(
        ure,
        proizvodnja_optimalna_ura,
        label="Optimalna proizvodnja",
        marker="s",
    )
    plt.fill_between(
        ure,
        np.minimum(povprecna_poraba, proizvodnja_optimalna_ura),
        color="green",
        alpha=0.2,
    )
    plt.title("Poraba in proizvodnja v povprečnem dnevu")
    plt.legend()
    plt.grid(True)
    plt.show()

    # Končni graf - EDV
    plt.figure(figsize=(10, 6))
    plt.plot(scenariji["Moc_SE_kW"], scenariji["EDV_let"], marker="o", color="blue")
    plt.title("Ekonomska doba vračanja (EDV) glede na moč SE")
    plt.xlabel("Moč SE [kW]")
    plt.ylabel("EDV [leta]")
    plt.grid(True)
    plt.show()

    # Excel tabela
    df_koncna_tabela = pd.DataFrame(primerjava)
    df_koncna_tabela["Prihranek"] = (
        df_koncna_tabela["Strošek pred"] - df_koncna_tabela["Strošek po"]
    )

    df_za_export = df_koncna_tabela.copy()
    for col in ["Strošek pred", "Strošek po", "Prihranek"]:
        df_za_export[col] = df_za_export[col].apply(formatiraj_eur)

    ime_datoteke = f"Rezultati_Optimizacije_{najboljsa_edv['Moc_SE_kW']}kW.xlsx"
    df_za_export.to_excel(ime_datoteke, index=False)
    print(f"\n[USPEH] Rezultati so shranjeni v datoteko: {ime_datoteke}")

    return scenariji, najboljsa_edv, df_koncna_tabela


def pridobi_trosarino_splet():
    """S spletnega portala zakonodaje PISRS z regularnimi izrazi (regex)

    izlušči uradno zakonsko določeno trošarino za električno energijo v Sloveniji.
    Vrne znesek v €/kWh.
    """
    url = "https://pisrs.si/pregledPredpisa?idZak=ZAKO6679"  # Zakon o trošarinah (ZTro-1)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    print(
        "Prenašam Zakon o trošarinah s portala PISRS za luščenje z regularnimi izrazi..."
    )

    try:
        odziv = requests.get(url, headers=headers, timeout=20)
        besedilo = odziv.text
    except Exception as e:
        print(
            f"Povezava ni uspela ({e}). Uporabljam zakonsko vrednost 3,05 €/MWh."
        )
        return 0.00305

    # REGULARNI IZRAZ:
    # V zakonu iščemo člen:
    # "Trošarina za električno energijo znaša 3,05 eura za eno megavatno uro"
    vzorec = (
        r"Trošarina\s+za\s+električno\s+energijo\s+znaša\s+(\d+,\d+)\s+eura"
    )

    najdeno = re.search(vzorec, besedilo, re.IGNORECASE)

    if najdeno:
        trosarina_mwh = float(najdeno.group(1).replace(",", "."))
        trosarina_kwh = trosarina_mwh / 1000.0  # pretvorba iz €/MWh v €/kWh
        print(
            f" -> Z regexom uspešno izluščena trošarina: {trosarina_mwh:.2f} €/MWh ({trosarina_kwh:.5f} €/kWh)"
        )
        return trosarina_kwh
    else:
        print(
            " -> Regex ni našel točnega člena, uporabljam zakonsko vrednost 0,00305 €/kWh."
        )
        return 0.00305