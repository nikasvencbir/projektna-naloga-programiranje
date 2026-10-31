# Optimizacija dimenzioniranja sončne elektrarne

Projektna naloga pri predmetu Uvod v programiranje / Programiranje.

## Kratek opis projekta

Cilj naloge je, da za poljubnega odjemalca električne energije, ki se zanima za nakup sončne elektrarne (brez baterije) izbere najbolj optimalno velikost. Kot najbolj optimalno velikost razumemo tisto, katere investicija se najprej povrne, torej ima najnižji EDV.

Model upošteva:
- **Meritve porabe:** 15-minutno telemetrijo dejanskega odjema, agregirano na urno raven. Če želite preizkusiti program na vašem odjemu, lahko te podatke pridobite od vašega oskrbovalca z električno energijo.
- **Borzne cene:** urne SPOT cene električne energije v Sloveniji za leto 2024.
- **Sončno obsevanje:** simulacijo urne proizvodnje sončne elektrarne prek evropskega modela PVGIS glede na izbrane koordinate.
- **Tarifni sistem:** omrežnino (VT/MT), dajatve (OIE+SPTE, prispevek za delovanje operaterja trga), trošarino in investicijske stroške (CAPEX),
- **Omejitev odjema** za konkretnega odjemalca.


## Viri podatkov

1. **[Energy-Charts API](https://api.energy-charts.info/):** Urne borzne SPOT cene za območje Slovenije (`bzn=SI`).
2. **[PVGIS API (Evropska komisija - JRC)](https://re.jrc.ec.europa.eu/api/v5_2/seriescalc):** Simulacija urnega osončenja in normirane proizvodnje 1 kW fotonapetostnega sistema za poljubno geografsko lokacijo.
3. **`Podatki_Optimizacija1.xlsx`:** Lokalni podatki o meritvah odjema (podatki, ki so nastavljeni kot privzeta vrednost so samo model in jih lahko zamenjamo na katerekoli 15-min podatke o porabi), ceniku postavitve SE (CAPEX) (podatke o cenah sem dobila v času svojega študentskega dela v podjetju Gen-i), ostali podatki iz tabele Tarife:
- **Omrežnina za energijo in moč (`EnergyNetworkFee`, `PowerNetworkFee`):**  
  [Agencija za energijo RS (agen-rs.si)](https://www.agen-rs.si/) – *Akt o določitvi tarifnih postavk za omrežnino elektrooperaterjev*.
- **Prispevki za delovanje operaterja trga in OIE/SPTE (`DutyMeteringPoint`, `DutyPiOI`, `DutyOIEK`):**  
  [Borzen – operater trga z elektriko (borzen.si)](https://www.borzen.si/) in [Uradni list RS (uradni-list.si)](https://www.uradni-list.si/) – *Uredba o določitvi prispevka za spodbujanje soproizvodnje in OIE*.
- **Trošarina na električno energijo (`ExciseTax`):**  
  [Finančna uprava Republike Slovenije - FURS (fu.gov.si)](https://www.fu.gov.si/) – *Zakon o trošarinah*.

## Namestitev in potrebne knjižnice

Projekt je napisan v programskem jeziku **Python 3**. Za delovanje so potrebne naslednje zunanje knjižnice:

* `os` – za določanje in združevanje poti do map in datotek ter za samodejno ustvarjanje ciljne mape za shranjevanje podatkov
* `requests` – za pošiljanje API zahtev in prenos podatkov s spleta,
* `pandas` – za obdelavo podatkovnih okvirjev in časovnih vrst,
* `numpy` – za numerične izračune,
* `matplotlib` – za izris grafov in vizualizacijo rezultatov,

### Namestitev knjižnic
Pred zagonom namestite vse potrebne knjižnice z enim ukazom v terminalu:

```bash
pip install requests pandas numpy matplotlib os
```
## Navodila za zagon projekta
Zagon interaktivnega zvezka:
-Odprite okolje Jupyter Notebook ali VS Code.
-Odprite datoteko analiza.ipynb.
-V meniju izberite Kernel 
$\rightarrow$ Restart & Run All (ali zaporedoma zaženite vse celice).
V zvezku se bodo izvedli prenosi podatkov, simulacija, optimizacija ter izrisali končni grafi dobe vračanja.

Če želite uporabiti svojo telemetrijo se držite spodaj opisane oblike datoteke:
## Navodila za pripravo podatkov (Uporabniške meritve)

Za izvedbo simulacije in optimizacije sončne elektrarne uporabite priloženo predlogo Excel datoteke. 

Delovna lista **`Tarife`** in **`Cenik_SE`** iz datoteke **`Podatki_Optimizacija.xlsx`** sta že vnaprej izpolnjena s privzetimi ekonomskimi parametri in cenikom investicije — **teh dveh listov ne spreminjajte ali brišite**, saj ju program potrebuje za pravilen izračun stroškov in dobe vračanja.

Vaša naloga je le, da v ustrezen delovni list vnesete svoje časovne meritve porabe ali ustvarite novo datoteko tako, da zgoraj omenjena delovna lista enostavno kopirate.

---

### 1. Splošna pravila
* **Format:** Microsoft Excel (`.xlsx`).
* **Vnaprej nastavljeni listi:** Listov `Tarife` in `Cenik_SE` ter njunih obstoječih stolpcev ne preimenujte.
* **Časovni korak:** Podatki meritev morajo biti v enotnem časovnem intervalu (15-minutni) in kronološko urejeni.
* **Numerične vrednosti:** V celicah s podatki naj bodo izključno številke (brez enot, kot so `kWh`, `kW` ipd.).

---

### 2. Vnos meritev (Delovni list za meritve)

V list z meritvami vnesite časovno vrsto za obravnavano obdobje (celotno koledarsko leto).

* **Zahtevana struktura stolpcev:**
  | Stolpec | Opis | Primer |
  | :--- | :--- | :--- |
  | `Timestamp` | Časovni žig meritve (datum in ura) | `2024-01-01 00:00:00` |
  | `Poraba` | Dejanski odjem/poraba objekta v danem intervalu | `12.4` |
  | `Proizvodnja` | Normirana / referenčna proizvodnja SE za skaliranje | `0.0` |

## Struktura repozitorija

```text
├── podatki/                        # Mapa s prenesenimi podatki s spleta
│   ├── spot_cene.csv               # Zajem borznih SPOT cen
│   └── pvgis_proizvodnja.csv       # Zajem urne proizvodnje iz PVGIS
├── Podatki_Optimizacija1.xlsx      # Vhodni Excel s telemetrijo in ceniki
├── zajem_podatkov.py              # Skripta za prenos podatkov prek API-jev
├── analiza.ipynb                   # Glavni Jupyter Notebook s celotno analizo in grafi
├── uporaba_ui.md                   # Dokumentacija uporabe orodij umetne inteligence
├── .gitignore                      # Izločitev odvečnih datotek (__pycache__, *.pyc, itd.)
└── README.md                       # Opis projekta in navodila za uporabo

