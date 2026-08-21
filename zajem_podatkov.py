"""Modul za prenos podatkov o borznih cenah elektrike in sončnem obsevanju."""
import os

#Določim pot do mape "podatki", ki sem jo ustvarila prej, sem se bojo shranjevali podatki iz spleta.
MAPA_PODATKI = os.path.join(os.path.dirname(__file__),"podatki")