import numpy as np

def ocisti_ceno(tekst):
    if isinstance(tekst, str):
        stevilka_del = tekst.split(' ')[0]
        return float(stevilka_del.replace(',', '.'))
    return tekst


def formatiraj_eur(x):
    return f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')


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


def celotna_bilanca(row, p, s_base, stroski_df, spot_podatki, df_leto_ref, marza1=5):
    df_omreznina1 = df_leto_ref['Tarifa (VT/MT)']
    df_omreznina2 = stroski_df.loc['PowerNetworkFee', 'Cena_num']
    df_meritve = stroski_df.loc['DutyMeteringPoint', 'Cena_num']
    df_OIEK = stroski_df.loc['DutyOIEK', 'Cena_num']
    df_PiOI = stroski_df.loc['DutyPiOI', 'Cena_num']
    df_trosarina = stroski_df.loc['ExciseTax', 'Cena_num']
    spot_kwh = spot_podatki / 1000
    marza1_kwh = marza1 / 1000
    omreznina_kwh = np.where(df_omreznina1 == "MT", 0.01695, 0.03724)
    moc_kw = row['Moc_SE_kW']
    capex_skupaj = row['CAPEX_EUR']
    letni_strosek_capex = capex_skupaj / 30
    i_energija = moc_kw * 1050
    S_i = s_base * i_energija
    viski = np.maximum(S_i - p, 0)
    manjki = np.maximum(p - S_i, 0)
    limit = limit_moci_kw
    manjki_dejanski = manjki
    viski_dejanski = np.minimum(viski, limit)
    variabilni_strosek_kwh = spot_kwh + marza1_kwh + omreznina_kwh + df_OIEK + df_PiOI + df_trosarina
    strosek_nakupa = np.sum(manjki_dejanski * variabilni_strosek_kwh)
    strosek_fiksni = (df_omreznina2 * limit_moci_kw) + (df_meritve * 12)
    zasluzek_viski = np.sum((spot_kwh - marza1_kwh) * viski_dejanski)
    skupni_letni_strosek = (strosek_fiksni + letni_strosek_capex + strosek_nakupa - zasluzek_viski) * 1.13
    return {
        'Skupaj': skupni_letni_strosek,
        'Energija': np.sum(manjki * spot_kwh) * 1.13,
        'Omreznina': (np.sum(manjki * omreznina_kwh) + df_omreznina2 * limit_moci_kw) * 1.13,
        'Prispevki': (df_meritve * 12 + np.sum((df_OIEK + df_PiOI) * manjki)) * 1.13,
        'Trosarina': np.sum(df_trosarina * manjki) * 1.13,
        'CAPEX': letni_strosek_capex * 1.13,
        'Viski': zasluzek_viski * 1.13
    }
