### 1. Zajem borznih (SPOT) cen električne energije

> **Uporabnik:**
> »Kako lahko v programskem jeziku Python z uporabo API vmesnika avtomatsko pridobim zgodovinske urne SPOT cene električne energije (npr. prek platforme Energy-Charts ali ENTSO-E) ter jih pretvorim v ustrezen pandas.DataFrame za nadaljnjo analizo?«

> **Umetna inteligenca (UI):**
> »Za pridobivanje borznih cen prek Energy-Charts API lahko uporabimo knjižnico `requests`. Spodaj je primer funkcije, ki pošlje zahtevo na API, prebere prejete podatke v formatu JSON, pretvori časovne žige v ustrezen časovni pas ter vrne urejen `DataFrame` z urnimi cenami v €/MWh:
>
> ```python
> import pandas as pd
> import requests
> 
> 
> def pridobi_spot_cene(drzava: str, leto: int) -> pd.DataFrame:
>     url = "https://api.energy-charts.info/price"
>     params = {"bzn": drzava, "start": f"{leto}-01-01T00:00:00Z"}
> 
>     response = requests.get(url, params=params)
>     if response.status_code == 200:
>         data = response.json()
>         df = pd.DataFrame(
>             {
>                 "timestamp": pd.to_datetime(data["unix_seconds"], unit="s"),
>                 "spot_cena_EUR_MWh": data["price"],
>             }
>         )
>         df.set_index("timestamp", inplace=True)
>         return df
>     else:
>         raise ConnectionError(f"Napaka pri prenosu: {response.status_code}")
> ```«

---

### 2. Zajem podatkov o urni proizvodnji sončne elektrarne (PVGIS API)

> **Uporabnik:**
> »Potrebujem kodo za prenos modelske urne proizvodnje sončne elektrarne prek PVGIS API za določeno geografsko lokacijo (zemljepisna širina in dolžina) ter nazivno moč elektrarne. Pri klicu API-ja se mi pojavljajo napake glede manjkajočih parametrov (pvcalculation, peakpower, loss). Kako pravilno nastaviti klic?«

> **Umetna inteligenca (UI):**
> »Napaka se pojavi, ker PVGIS API za izračun urne moči zahteva specifične parametre:
> 
> * `pvcalculation=1` (omogoči izračun proizvodnje),
> * `peakpower` (nazivna moč elektrarne v kWp),
> * `loss` (ocenjene sistemske izgube v %, npr. 14 %) ter
> * `startyear` in `endyear`.
> 
> Primer pravilno sestavljenega klica:
>
> ```python
> def pridobi_pvgis_proizvodnjo(
>     lat: float, lon: float, peakpower: float, year: int
> ) -> pd.DataFrame:
>     url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
>     params = {
>         "lat": lat,
>         "lon": lon,
>         "startyear": year,
>         "endyear": year,
>         "pvcalculation": 1,
>         "peakpower": peakpower,
>         "loss": 14,
>         "outputformat": "json",
>     }
> 
>     response = requests.get(url, params=params)
>     data = response.json()
> 
>     hourly_data = data["outputs"]["hourly"]
>     df = pd.DataFrame(hourly_data)
>     df["timestamp"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")
>     df.rename(columns={"P": "proizvodnja_W"}, inplace=True)
>     df.set_index("timestamp", inplace=True)
> 
>     return df[["proizvodnja_W"]]
> ```«

---

### 3. Sinhronizacija in priprava podatkov za optimizacijski model

> **Uporabnik:**
> »Kako naj v enem DataFrame-u uskladim prenesene podatke o cenah, PVGIS proizvodnji in lastni porabi, če imajo podatki različne časovne korake (npr. 15-minutni vs. urni interval) ali manjkajoče vrednosti?«

> **Umetna inteligenca (UI):**
> »Za uskladitev različnih časovnih resolucij uporabimo metodo `resample()` ali `reindex()` v knjižnici pandas:
> 
> 1. Podatke z višjo frekvenco (15-minutne) agregiramo na urni nivo s povprečjem ali vsoto (`df.resample('1h').mean()` oz. `.sum()`).
> 2. Časovne nize združimo z `pd.merge()` po indeksu časovnih žigov.
> 3. Morebitne manjkajoče vrednosti interpoliramo z metodo `.interpolate(method='time')`.«

---

### 4. Razumevanje delovanja in strukture Jupyter zvezka

> **Uporabnik:**
> »Kako natančno deluje Jupyter Notebook in kakšna je razlika med celicami s kodo (Code cells) ter besedilnimi celicami (Markdown cells)? Kako naj v zvezku smiselno strukturiram potek seminarske naloge, da bodo rezultati in grafi pregledno predstavljeni?«

> **Umetna inteligenca (UI):**
> »Jupyter Notebook je interaktivno razvojno okolje, ki omogoča sočasno izvajanje kode, prikaz rezultatov/grafov ter dokumentiranje z besedilom:
> 
> * **Celice s kodo (Code cells):** Vsebujejo izvedljivo Python kodo. Spremenljivke in funkcije, definirane v predhodnih celicah, ostanejo shranjene v delovnem spominu (jedru – Kernel).
> * **Besedilne celice (Markdown cells):** Uporabljajo se za formatiranje besedila, naslovov, enačb v $\LaTeX$ formatu in razlago rezultatov.
> 
> Priporočena struktura zvezka za projektno nalogo:
> 1. Uvod in cilj naloge: Kratek opis problema in metodologije (Markdown).
> 2. Uvoz knjižnic in modulov: Uvoz lastnih modulov ter zunanjih knjižnic (pandas, matplotlib itd.).
> 3. Zajem in priprava podatkov: Klici funkcij za prenos podatkov (API) in prikaz osnovnih statistik podatkovnega okvira.
> 4. Simulacija in optimizacija: Zagon izračunov ter prikaz tabelarnih rezultatov.
> 5. Vizualizacija in interpretacija: Izris grafov (toplotni zemljevidi, urni profili) z razlago ekonomskih kazalnikov.«

---

### 5. Modularnost: Povezovanje zunanjih Python skript (.py) z Jupyter zvezkom

> **Uporabnik:**
> »Ali je celotno programsko kodo priporočljivo pisati neposredno v Jupyter zvezek ali je bolj smiselno logiko razdeliti v ločene .py datoteke in jih nato uvoziti v zvezek? Kako to pravilno izvedem?«

> **Umetna inteligenca (UI):**
> »V skladu z dobrimi inženirskimi praksami (in standardom PEP 8) je priporočljiva modularna struktura:
> 
> * **Moduli (.py datoteke):** V njih shranimo pomožne funkcije, logiko za prenos podatkov (API) ter matematične modele (npr. modul za izračun hranilnika in sončne elektrarne).
> * **Jupyter zvezek (.ipynb):** Služi kot 'glavni program' (main presentation pipeline), kjer funkcije le uvozimo in kličemo:
> 
> ```python
> # Primer uvoza lastnih modulov v zvezku:
> from modul_zajem import pridobi_pvgis_proizvodnjo, pridobi_spot_cene
> from modul_optimizacija import poisci_optimum, simuliraj_scenarije
> ```
> 
> S tem zvezek ostane pregleden, koda pa je ponovno uporabna in lažja za vzdrževanje.«
