Zakaj je prišlo do sledeče napake: PS C:\Users\Nika\Documents\Projektna_naloga_UVP> & C:\Users\Nika\AppData\Local\Programs\Python\Python314\python.exe c:/Users/Nika/Documents/Projektna_naloga_UVP/projektna-naloga-programiranje/zajem_podatkov.py Traceback (most recent call last): File "c:\Users\Nika\Documents\Projektna_naloga_UVP\projektna-naloga-programiranje\zajem_podatkov.py", line 3, in <module> import requests ModuleNotFoundError: No module named 'requests' PS C:\Users\Nika\Documents\Projektna_naloga_UVP>


MathGPT Assistant
Napaka ModuleNotFoundError: No module named 'requests' pomeni, da Python knjižnice requests še nima nameščene v svojem okolju.
Kako težavo odpravite:
V terminalu v VS Code (kjer se vam je izpisala napaka) vpišite naslednji ukaz in pritisnite Enter:
pip install requests pandas openpyxl matplotlib
(Z enim ukazom boste namestili knjižnico requests ter še ostale (pandas, openpyxl, matplotlib), ki jih program potrebuje za delo s podatki in tabelami).
Kaj storiti po namestitvi?
Ko se namestitev zaključi (ko se v terminalu ponovno pojavi vrstica PS C:\...), ponovno zaženite skripto:
python c:/Users/Nika/Documents/Projektna_naloga_UVP/projektna-naloga-programiranje/zajem_podatkov.py
Skripta bo zdaj normalno prenesla podatke s spleta.

pomagal mi je združiti 15min podatke v urne