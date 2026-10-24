#!/usr/bin/env python3
"""KinoLel TV (Android TV / Google TV): Banner, Programmsymbol und Logo aus dem KinoLel-Logo erzeugen (braucht Pillow,
z. B. auf CT 103). Nutzt die Zeichenfunktionen aus dem Windows-Player (kinolel-player/marke/bilder_erzeugen.py).
Aufruf: python3 tv_bilder.py <repo> <pfad/zu/bilder_erzeugen.py> <banner-light.png>"""
import importlib.util
import os
import sys

repo, modul, banner = sys.argv[1:4]
spec = importlib.util.spec_from_file_location('be', modul)
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)
marke = {'APP_NAME': 'KinoLel', 'APP_COLOR_ACCENT': '#9aa4ff', 'APP_COLOR_BACKGROUND': '#0b0f18'}
res = os.path.join(repo, 'app', 'src', 'main', 'res')


def speichern(bild, *teile):
    p = os.path.join(res, *teile)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    bild.save(p, optimize=True)


# Banner auf dem Google-TV-Startbildschirm: 160 x 90 dp (xhdpi 320 x 180 px), Logo + Schriftzug auf dunklem Verlauf
for ordner, f in (('mdpi', 1), ('hdpi', 1.5), ('xhdpi', 2), ('xxhdpi', 3), ('xxxhdpi', 4)):
    w, h = round(160 * f), round(90 * f)
    speichern(be.logo_mit_name(marke, w, h, banner, None, grund=True, anteil=0.36).convert('RGB'), f'mipmap-{ordner}', 'app_banner.png')
    # Programmsymbol (ältere Geräte ohne adaptive Symbole): 40 dp
    speichern(be.symbol(round(40 * f * 2), marke), f'mipmap-{ordner}', 'app_icon.png')

# Logo mit Schriftzug für Startbild und Kopfleiste (252 x 72 dp, 4-fach)
speichern(be.logo_mit_name(marke, 1008, 288, banner, None, grund=False, anteil=0.62), 'drawable-nodpi', 'app_logo.png')
print('fertig')
