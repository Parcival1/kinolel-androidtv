#!/usr/bin/env python3
"""KinoLel TV: Test im Android-TV-Emulator – Bedienung NUR mit der Fernbedienung (adb shell input keyevent).

Lel 24.10.2026: „… Google Chromecast freundlich, weil nix Maus und Tastatur, nur die Chromecast-Fernbedienung.“
Kein Tippen auf Koordinaten. Den Bildschirm liest der Test nur (uiautomator dump), um zu prüfen, was zu sehen ist und
wo der Fokus steht. Zum Starten einer Detailseite nutzt er den App-Aufruf, den auch die Google-TV-Suche nimmt.

Ablauf: Installation -> Quick Connect (Code + QR) -> Bestätigen am „Handy“ (Schnittstelle, Testkonto kinolel-hilfe)
-> Startseite (Weiter ansehen / Als Nächstes) -> Wünsche/Hilfe über die Kopfleiste -> Detailseite Testfilm -> Abspielen
-> Spulen mit Vorschau -> Zurück -> Fortschritt beim Server -> Fernsteuerung -> Update-Hinweis (Test-apps.json)
-> „Was ist neu“ -> Speicher (dumpsys meminfo) -> Abmelden.

Umgebung: APK (Pfad), PAKET (Standard de.kinolel.tv.debug), KINOLEL_TEST_PW (Secret; ohne: nur bis zur Anmeldung).
Passwort und Zugangsschlüssel werden nie ausgegeben. Ergebnis: tvtest/ablauf.txt, tvtest/ergebnis.json, Bildschirmfotos.
"""
import http.server
import json
import xml.etree.ElementTree as ET
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

AUS = "tvtest"
os.makedirs(AUS, exist_ok=True)
APK = os.environ.get("APK", "")
PAKET = os.environ.get("PAKET", "de.kinolel.tv.debug")
START = PAKET + "/org.jellyfin.androidtv.ui.startup.StartupActivity"
SERVER = "https://kinolel.de"
PW = os.environ.get("KINOLEL_TEST_PW", "")
TESTFILM = "Zurück in die Zukunft II"
ergebnis = {}
protokoll = open(os.path.join(AUS, "ablauf.txt"), "w", encoding="utf-8")


def log(text):
    zeile = time.strftime("%H:%M:%S ") + text
    print("TV-Test:", text, flush=True)
    protokoll.write(zeile + "\n")
    protokoll.flush()


def merke(schritt, ok, info=""):
    ergebnis[schritt] = {"ok": bool(ok), "info": info}
    log(f"{'OK    ' if ok else 'FEHLER'} {schritt}{(' – ' + info) if info else ''}")


# --- adb ---------------------------------------------------------------------------------------------------------

def adb(*args, timeout=60, binaer=False):
    r = subprocess.run(["adb", *args], capture_output=True, timeout=timeout)
    return r.stdout if binaer else r.stdout.decode("utf-8", "replace")


def taste(name, mal=1, pause=0.7):
    """Ein Druck auf der Fernbedienung (DPAD_UP/DOWN/LEFT/RIGHT, DPAD_CENTER = OK, BACK)."""
    for _ in range(mal):
        adb("shell", "input", "keyevent", "KEYCODE_" + name)
        time.sleep(pause)


def bild(name):
    with open(os.path.join(AUS, name + ".png"), "wb") as f:
        f.write(adb("exec-out", "screencap", "-p", binaer=True))


# Lel 25.10.: „… in den Einstellungen steht irgendwo immer noch ‚Jellyfin‘“ – jede gelesene Oberfläche prüfen
# (außer den Lizenzen: dort stehen die technischen Namen der Grundlage zu Recht)
JELLYFIN_FUNDE = {}
JELLYFIN_ERLAUBT = [False]
LIZENZ_JELLYFIN = set()  # nur zur Info: „Jellyfin“ in den Lizenzen (Namen der Grundlage, bleiben)
SEITE = ["?"]


def ui():
    xml = adb("exec-out", "uiautomator", "dump", "/dev/tty", timeout=30)
    xml = xml[: xml.rfind(">") + 1] if ">" in xml else ""
    if not JELLYFIN_ERLAUBT[0]:
        for t in texte(xml):
            if "jellyfin" in t.lower():
                JELLYFIN_FUNDE.setdefault(t[:100], SEITE[0])
    return xml


KNOTEN = re.compile(r"<node [^>]*>")


def knoten(xml):
    for k in KNOTEN.findall(xml):
        yield {
            "text": (re.search(r' text="([^"]*)"', k) or [None, ""])[1],
            "desc": (re.search(r' content-desc="([^"]*)"', k) or [None, ""])[1],
            "fokus": ' focused="true"' in k,
        }


def texte(xml):
    return [t for k in knoten(xml) for t in (k["text"], k["desc"]) if t]


def fokus(xml=None):
    """Text des Elements mit Fokus (innerstes). Bei Compose sitzt der Text oft in einem Kind -> erste Texte darunter."""
    xml = xml if xml is not None else ui()
    alle = KNOTEN.findall(xml)
    for i, k in enumerate(alle):
        if ' focused="true"' in k:
            eigene = (re.search(r' text="([^"]+)"', k) or re.search(r' content-desc="([^"]+)"', k))
            if eigene:
                return eigene[1]
            for kind in alle[i + 1:i + 6]:
                t = re.search(r' text="([^"]+)"', kind) or re.search(r' content-desc="([^"]+)"', kind)
                if t:
                    return t[1]
            return "?"
    return ""


def fokus_roh(xml=None):
    """Der fokussierte Knoten als Rohtext (Klasse, Kennung, Beschreibung) – zur Fehlersuche im Player."""
    xml = xml if xml is not None else ui()
    for k in KNOTEN.findall(xml):
        if ' focused="true"' in k:
            teile = [re.search(f' {a}="([^"]*)"', k) for a in ("class", "resource-id", "content-desc", "text")]
            return " | ".join((m[1] if m else "") for m in teile)
    return ""


def warte_auf(bedingung, sekunden, takt=2.0):
    ende = time.time() + sekunden
    while time.time() < ende:
        xml = ui()
        if xml and bedingung(xml):
            return xml
        time.sleep(takt)
    return None


def enthaelt(*woerter):
    return lambda xml: any(w in t for t in texte(xml) for w in woerter)


def app_start(extra=()):
    adb("shell", "am", "start", "-W", "-n", START, *extra)


def app_stopp():
    adb("shell", "am", "force-stop", PAKET)


def einstellungen_schreiben(werte):
    """KinoLel-Einstellungen der Test-App setzen (nur Debug-Version: run-as). App muss gestoppt sein."""
    eintraege = []
    for name, wert in werte.items():
        if isinstance(wert, int):
            eintraege.append(f'<long name="{name}" value="{wert}" />')
        else:
            eintraege.append(f'<string name="{name}">{wert}</string>')
    inhalt = "<?xml version='1.0' encoding='utf-8' standalone='yes' ?><map>" + "".join(eintraege) + "</map>"
    # adb shell setzt die Argumente zu EINER Zeile zusammen -> Befehl als ein String mit eigenen Anführungszeichen
    r = subprocess.run(["adb", "shell", f"run-as {PAKET} sh -c 'mkdir -p shared_prefs && cat > shared_prefs/kinolel.xml'"],
                       input=inhalt.encode(), capture_output=True, timeout=30)
    pruef = adb("shell", f"run-as {PAKET} cat shared_prefs/kinolel.xml")
    log(f"Einstellungen geschrieben: {sorted(werte)} – {'ok' if all(n in pruef for n in werte) else 'FEHLT: ' + (r.stderr.decode()[:200] or pruef[:200])}")


# --- Jellyfin-Schnittstelle (spielt das Handy, das Quick Connect bestätigt, und den Server) ----------------------

class Api:
    def __init__(self):
        self.token = None
        self.user = None
        self.geraet = "kinolel-tv-ci-" + str(int(time.time()))

    def kopf(self, token=None):
        a = f'MediaBrowser Client="KinoLel TV Test", Device="GitHub", DeviceId="{self.geraet}", Version="1"'
        t = token or self.token
        if t:
            a += f', Token="{t}"'
        return {"Authorization": a, "Content-Type": "application/json"}

    def ruf(self, meth, pfad, daten=None, token=None):
        req = urllib.request.Request(SERVER + pfad, method=meth, headers=self.kopf(token),
                                     data=None if daten is None else json.dumps(daten).encode())
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return json.loads(body) if body and r.headers.get_content_type() == "application/json" else None

    def anmelden(self):
        a = self.ruf("POST", "/Users/AuthenticateByName", {"Username": "kinolel-hilfe", "Pw": PW})
        self.token, self.user = a["AccessToken"], a["User"]["Id"]

    def abmelden(self, token=None):
        try:
            self.ruf("POST", "/Sessions/Logout", token=token)
        except Exception as e:
            log(f"Abmelden: {e}")

    def tv_sitzung(self):
        for s in self.ruf("GET", "/Sessions?activeWithinSeconds=600") or []:
            if s.get("UserId") == self.user and (s.get("Client") or "").startswith("KinoLel TV ("):
                return s
        return None

    def befehl(self, sid, pfad, daten=None):
        return self.ruf("POST", f"/Sessions/{sid}/{pfad}", daten)


api = Api()


# --- Startseite wie bei Lel, Startvideo, Einstellungs-Rundgang (Lel 25.10.) ----------------------------------------
LEL_ABSCHNITTE = ["smalllibrarytiles", "resume", "resumeaudio", "resumebook", "livetv", "nextup", "latestmedia",
                  "none", "none", "none"]
ANZEIGE_ORIGINAL = [None]


def anzeige_pfad():
    return f"/DisplayPreferences/usersettings?userId={api.user}&client=emby"


def startseite_wie_lel():
    """Lels Konto „TV“ hat die Startseiten-Abschnitte der Weboberfläche inkl. Live-TV – damit blitzten beim Öffnen
    Live-TV-Knöpfe auf. Fürs Testkonto vorübergehend genauso setzen (am Ende zurück)."""
    try:
        d = api.ruf("GET", anzeige_pfad())
        ANZEIGE_ORIGINAL[0] = json.loads(json.dumps(d))
        d["CustomPrefs"] = {**(d.get("CustomPrefs") or {}), **{f"homesection{i}": w for i, w in enumerate(LEL_ABSCHNITTE)}}
        api.ruf("POST", anzeige_pfad(), d)
        log("Startseiten-Abschnitte des Testkontos wie bei Lel (mit Live-TV)")
    except Exception as e:  # noqa: BLE001
        log(f"Startseiten-Abschnitte nicht gesetzt: {e}")


def sprache_konto(wert):
    """„kl-sprache“ des Testkontos setzen wie die Wahl Deutsch/Magyar auf kinolel.de (None: entfernen).
    Ursprungszustand merken – am Ende stellt startseite_zurueck() alles wieder her."""
    try:
        d = api.ruf("GET", anzeige_pfad())
        if ANZEIGE_ORIGINAL[0] is None:
            ANZEIGE_ORIGINAL[0] = json.loads(json.dumps(d))
        prefs = dict(d.get("CustomPrefs") or {})
        if wert is None:
            prefs.pop("kl-sprache", None)
        else:
            prefs["kl-sprache"] = wert
        d["CustomPrefs"] = prefs
        api.ruf("POST", anzeige_pfad(), d)
        log(f"Sprache im Testkonto: {wert or 'keine'}")
    except Exception as e:  # noqa: BLE001
        log(f"Sprache im Testkonto nicht gesetzt: {e}")


def startseite_zurueck():
    if ANZEIGE_ORIGINAL[0] is not None:
        try:
            api.ruf("POST", anzeige_pfad(), ANZEIGE_ORIGINAL[0])
            log("Startseiten-Abschnitte des Testkontos zurückgesetzt")
        except Exception as e:  # noqa: BLE001
            log(f"Startseiten-Abschnitte nicht zurückgesetzt: {e}")


def startvideo():
    """Öffnen im Bildschirmvideo: Startbild, bis die Reihen stehen – nie Kopfleiste ohne Reihen, nie Live-TV."""
    app_stopp()
    time.sleep(2)
    adb("shell", "rm", "-f", "/sdcard/kl-start-*.mp4")
    rahmen = os.path.join(AUS, "oeffnen-rahmen")
    os.makedirs(rahmen, exist_ok=True)
    # screenrecord hört auf dem Emulator nach ~10 s von selbst auf -> Abschnitte hintereinander, bis 30 s erfasst sind
    teile = []

    def aufnehmen():
        beginn = time.time()
        while time.time() - beginn < 30 and len(teile) < 6:
            ziel = f"/sdcard/kl-start-{len(teile)}.mp4"
            t0 = time.time()
            subprocess.run(["adb", "shell", "screenrecord", "--time-limit", "30", "--bit-rate", "8000000", ziel],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            teile.append(ziel)
            log(f"Startvideo Abschnitt {len(teile)}: {time.time() - t0:.1f} s aufgenommen")
    rekorder = threading.Thread(target=aufnehmen)
    rekorder.start()
    time.sleep(1.5)
    adb("shell", "monkey", "-p", PAKET, "-c", "android.intent.category.LEANBACK_LAUNCHER", "1")
    rekorder.join(timeout=120)
    bild("15b-nach-dem-oeffnen")
    time.sleep(2)
    for i, ziel in enumerate(teile):
        video = os.path.join(AUS, f"15-oeffnen-{i}.mp4")
        adb("pull", ziel, video, timeout=60)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vf", "fps=6", os.path.join(rahmen, f"t{i}-r%03d.png")],
                       timeout=180)
    bilder = sorted(f for f in os.listdir(rahmen) if f.endswith(".png"))
    zeile = []
    for b in bilder:
        txt = subprocess.run(["tesseract", os.path.join(rahmen, b), "-", "-l", "deu", "--psm", "11"],
                             capture_output=True, text=True, timeout=60).stdout
        kopf = "Startseite" in txt or "Wünsche" in txt
        reihen = any(w in txt for w in ("Nächstes", "Weiter ansehen", "Kürzlich", "Meine Medien"))
        livetv = any(w in txt for w in ("Live-TV", "Läuft gerade", "Fernsehprogramm", "Fernsehaufnahmen"))
        zeile.append("L" if livetv else ("H" if kopf and not reihen else ("F" if reihen else ".")))
    verlauf = "".join(zeile)
    log(f"Öffnen, Bild für Bild (6/s; . Startbild, H halb aufgebaut, F fertig, L Live-TV): {verlauf}")
    with open(os.path.join(AUS, "15-oeffnen-verlauf.txt"), "w", encoding="utf-8") as f:
        f.write(verlauf + "\n")
    halb = max((len(s) for s in re.findall(r"H+", verlauf)), default=0)
    erst_fertig = verlauf.find("F")
    merke("Öffnen (Video): kein Live-TV-Abschnitt", bool(bilder) and "L" not in verlauf, f"{len(bilder)} Bilder")
    # Überblendung (0,25 s) darf ein einzelnes Bild „halb“ zeigen, länger nicht
    merke("Öffnen (Video): Startbild, bis die Reihen stehen (keine halb aufgebaute Startseite)",
          erst_fertig >= 0 and halb <= 1,
          f"fertig nach {erst_fertig / 6:.1f} s, längste halbe Phase {halb} Bild(er)" if erst_fertig >= 0 else "Startseite nicht erkannt")
    for b in bilder:
        os.remove(os.path.join(rahmen, b))
    os.rmdir(rahmen)


# Einträge, die etwas auslösen statt eine Seite zu öffnen: nie drücken
VERBOTEN = re.compile(r"(?i)abmeld|sign ?out|kijelentkez|entfern|remove|eltávolít|lösch|delete|törl|hinzufüg|hozzáad|"
                      r"\badd\b|update|frissít|leeren|clear|ürít|neu ?start|restart|zurücksetz|reset|visszaállít|"
                      r"teilen|share|megoszt|senden|send|küld|wechseln|"
                      r"switch|vált|beenden|kilép")
LIZENZ = re.compile(r"(?i)lizenz|licen")


# Die Einstellungen sind ein Fenster am rechten Rand (350 dp = 700 px bei 1920 px Breite): Fokus links davon heißt,
# der Rundgang ist aus den Einstellungen herausgefallen -> nichts mehr drücken
PANEL_LINKS = 1100


def fokus_eintrag(xml):
    """(Beschriftung, umschaltbar, linker Rand) des fokussierten Eintrags, Beschriftung aus allen Texten darunter"""
    try:
        wurzel = ET.fromstring(xml)
    except ET.ParseError:
        return None
    for n in wurzel.iter("node"):
        if n.get("focused") == "true":
            teile = [k.get("text") or k.get("content-desc") for k in n.iter("node") if (k.get("text") or k.get("content-desc"))]
            links = int((re.match(r"\[(\d+),", n.get("bounds", "")) or [0, 0])[1])
            # Umschalter/Auswahl (Checkbox, Schalter, Radio) nie drücken – das würde Einstellungen ändern
            umschaltbar = any(k.get("checkable") == "true" or k.get("selected") == "true"
                              or any(c in (k.get("class") or "") for c in ("RadioButton", "CheckBox", "Switch"))
                              for k in n.iter("node"))
            return " / ".join(teile)[:90], umschaltbar, links
    return None


def signatur(xml):
    return tuple(t for t in texte(xml))[:40]


def einstellungen_rundgang():
    """Alle Einstellungsseiten mit dem Steuerkreuz öffnen (Umschalter und Auslöser nicht drücken) – jede gelesene
    Oberfläche läuft durch den „Jellyfin“-Sammler in ui()."""
    for _ in range(8):
        if fokus() in ("Startseite", "Suche", "Wünsche"):
            break
        taste("DPAD_UP")
    for _ in range(8):
        if fokus() in ("Einstellungen", "Settings"):
            break
        taste("DPAD_RIGHT")
    taste("DPAD_CENTER", pause=2)
    seiten = []
    raus = [False]

    def im_panel(e):
        return e is not None and e[2] >= PANEL_LINKS

    def seite(tiefe, pfad, vorfahren=()):
        """True, wenn diese Seite sich durch eine Auswahl selbst geschlossen hat (dann kein Zurück beim Aufrufer)"""
        SEITE[0] = " > ".join(pfad) or "Einstellungen"
        xml = ui()
        seiten.append(SEITE[0])
        gesehen = []
        eintrag = fokus_eintrag(xml)
        while eintrag and eintrag[0] not in gesehen and len(gesehen) < 30 and not raus[0]:
            if not im_panel(eintrag):
                raus[0] = True
                log(f"Einstellungs-Rundgang: Fokus außerhalb der Einstellungen ({eintrag[0]}) – Rundgang beendet")
                break
            gesehen.append(eintrag[0])
            name, umschaltbar, _ = eintrag
            if tiefe < 3 and not umschaltbar and not VERBOTEN.search(name):
                lizenz = bool(LIZENZ.search(name))
                vorher = signatur(xml)
                JELLYFIN_ERLAUBT[0] = lizenz
                taste("DPAD_CENTER", pause=1.5)
                neu = ui()
                if signatur(neu) in vorfahren:
                    # die Auswahl hat diese Seite geschlossen (eine Ebene höher gelandet)
                    JELLYFIN_ERLAUBT[0] = False
                    return True
                if signatur(neu) != vorher:
                    selbst_zu = False
                    if not lizenz:
                        selbst_zu = seite(tiefe + 1, pfad + [name.split(" / ")[0]], tuple(vorfahren) + (vorher,))
                    else:
                        LIZENZ_JELLYFIN.update(x[:80] for x in texte(neu) if "jellyfin" in x.lower())
                        seiten.append(" > ".join(pfad + [name.split(" / ")[0]]) + " (Lizenzen, nicht geprüft)")
                    if not selbst_zu:
                        taste("BACK", pause=1.2)
                    # Fokus zurück auf denselben Eintrag
                    for _ in range(30):
                        e = fokus_eintrag(ui())
                        if not e or e[0] == name or not im_panel(e):
                            break
                        taste("DPAD_DOWN", pause=0.4)
                JELLYFIN_ERLAUBT[0] = False
                SEITE[0] = " > ".join(pfad) or "Einstellungen"
            taste("DPAD_DOWN", pause=0.5)
            xml = ui()
            eintrag = fokus_eintrag(xml)
        return False

    try:
        if im_panel(fokus_eintrag(ui())):
            seite(0, [])
        else:
            log("Einstellungen nicht geöffnet (Fokus nicht im Einstellungsfenster)")
    finally:
        JELLYFIN_ERLAUBT[0] = False
        for _ in range(6):  # Einstellungen schließen
            if any(w in texte(ui()) for w in ("Startseite", "Wünsche")):
                break
            taste("BACK", pause=1)
    with open(os.path.join(AUS, "16-einstellungen-seiten.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(seiten) + "\n")
    return [] if raus[0] else seiten


# --- Test-Server für die Update-Prüfung (der Emulator erreicht den Runner unter 10.0.2.2) ------------------------

def test_server(apps_json):
    class Antwort(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.endswith(".apk"):  # die Test-APK selbst als „neue Version“
                body = open(APK, "rb").read()
                art = "application/vnd.android.package-archive"
            else:
                body = json.dumps(apps_json).encode()
                art = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", art)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("0.0.0.0", 8765), Antwort)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


# --- Ablauf -------------------------------------------------------------------------------------------------------

def main():
    adb("wait-for-device")
    log("Gerät: " + adb("shell", "getprop", "ro.product.model").strip() + ", Android "
        + adb("shell", "getprop", "ro.build.version.release").strip()
        + ", Leanback: " + str("android.software.leanback" in adb("shell", "pm", "list", "features")))
    log("Installation: " + adb("install", "-r", "-g", APK, timeout=240).strip().splitlines()[-1])
    adb("shell", "cmd", "locale", "set-app-locales", PAKET, "--locales", "de-DE")

    # 1. Anmeldung mit Quick Connect: Code + QR-Code
    app_start()
    xml = warte_auf(lambda x: any(re.fullmatch(r"\d{3} \d{3}", t) for t in texte(x)), 120)
    bild("01-anmeldung-quickconnect")
    code = next((t.replace(" ", "") for t in texte(xml or "") if re.fullmatch(r"\d{3} \d{3}", t)), None)
    merke("Anmeldung: Quick-Connect-Code sichtbar", code is not None)
    merke("Anmeldung: QR-Code sichtbar", bool(xml) and "kinolel.quickconnect.qr" in xml)
    # Inhalt des QR-Codes aus dem Bildschirmfoto lesen (Lel 24.10.: öffnet am Handy die KinoLel-App bzw. den Browser)
    try:
        import zxingcpp
        from PIL import Image
        gelesen = [t.text for t in zxingcpp.read_barcodes(Image.open(os.path.join(AUS, "01-anmeldung-quickconnect.png")))]
    except Exception as e:  # noqa: BLE001
        gelesen = [f"nicht lesbar: {type(e).__name__}: {e}"]
    erwartet = f"https://kinolel.de/web/kinolel/qc.html?code={code}"
    merke("Anmeldung: QR-Code enthält kinolel.de/web/kinolel/qc.html mit dem angezeigten Code",
          bool(code) and erwartet in gelesen, ", ".join(gelesen)[:160])
    # Lel 24.10.: „… aber auch mit Tippen möglich machen“ – Passwort-Weg gleichwertig daneben, Fokus im Benutzernamen
    merke("Anmeldung: Benutzername/Passwort daneben", bool(xml) and any("Mit Benutzername und Passwort" in t for t in texte(xml)),
          "Fokus: " + fokus(xml or ""))
    merke("Kein „Jellyfin“ in der Oberfläche (Anmeldung)", bool(xml) and not any("Jellyfin" in t for t in texte(xml)))
    if not code or not PW:
        if not PW:
            log("Kein KINOLEL_TEST_PW (Secret fehlt) – Test endet nach dem Anmeldebildschirm.")
        return

    api.anmelden()
    startseite_wie_lel()
    try:
        api.ruf("POST", f"/QuickConnect/Authorize?code={code}&userId={api.user}")
        merke("Anmeldung: Code am „Handy“ bestätigt", True)
        # Übergang Anmeldung -> Startseite nicht per uiautomator lesen (Android 14: NPE in der Bedienungshilfe, 25.10.)
        time.sleep(8)
    except urllib.error.HTTPError as e:
        merke("Anmeldung: Code am „Handy“ bestätigt", False, f"HTTP {e.code}")
        return

    # 2. Startseite
    xml = warte_auf(enthaelt("Weiter ansehen", "Als Nächstes", "Kürzlich", "Meine Medien"), 120)
    time.sleep(4)
    bild("02-startseite")
    xml = ui()
    zeilen = [w for w in ("Weiter ansehen", "Als Nächstes") if any(w in t for t in texte(xml))]
    merke("Startseite geladen", xml is not None and any("Kürzlich" in t or "Meine Medien" in t or "Weiter" in t for t in texte(xml)))
    # „Weiter ansehen“ gibt es nur, wenn das Konto etwas angefangen hat (Server fragen) – sonst zeigt Jellyfin die Zeile nicht
    angefangen = len((api.ruf("GET", f"/UserItems/Resume?userId={api.user}&limit=1&mediaTypes=Video") or {}).get("Items", []))
    erwartet = ["Weiter ansehen", "Als Nächstes"] if angefangen else ["Als Nächstes"]
    merke("Startseite: Zeilen Weiter ansehen / Als Nächstes", all(w in zeilen for w in erwartet),
          ", ".join(zeilen) + ("" if angefangen else " (Konto hat nichts angefangen -> ohne „Weiter ansehen“)"))
    merke("Startseite: Fokus erkennbar", bool(fokus(xml)), fokus(xml))

    # 3. Kopfleiste: Wünsche und Hilfe nur mit dem Steuerkreuz
    # (Hilfe gibt es am Fernseher nicht mehr – Lel 24.10.)
    merke("Kopfleiste: Logo mit Schriftzug sichtbar, kein „Hilfe“", "KinoLel" in " ".join(texte(ui())) and "Hilfe" not in texte(ui()))
    for ziel, kennzeichen, name in (("Wünsche", "wuensche.kinolel.de", "03-wuensche"),):
        gefunden = False
        for _ in range(8):  # nach oben in die Kopfleiste
            if fokus() in ("Startseite", "Suche", "Wünsche"):
                break
            taste("DPAD_UP")
        reihe = ["Startseite", "Suche", "Wünsche"]
        for _ in range(8):  # seitwärts bis zum Ziel
            f = fokus()
            if f == ziel:
                gefunden = True
                break
            taste("DPAD_LEFT" if f in reihe and reihe.index(f) > reihe.index(ziel) else "DPAD_RIGHT")
        if gefunden:
            taste("DPAD_CENTER", pause=2)
        xml = warte_auf(enthaelt(kennzeichen), 20)
        bild(name)
        merke(f"Kopfleiste: {ziel} (QR-Code)", gefunden and xml is not None)
        taste("BACK", pause=2)

    # 4. Detailseite des Testfilms (wie aus der Google-TV-Suche) und Abspielen
    film = api.ruf("GET", f"/Items?userId={api.user}&searchTerm={urllib.parse.quote(TESTFILM)}&includeItemTypes=Movie&recursive=true&limit=5")
    film = next((i for i in film["Items"] if i["Name"] == TESTFILM), None)
    if not film:
        merke("Testfilm gefunden", False, TESTFILM)
        return
    time.sleep(5)  # Startseite nach der Rückkehr fertig laden lassen
    app_start(("--es", "ItemId", film["Id"]))
    xml = warte_auf(enthaelt(TESTFILM), 30)
    if xml is None:
        # beobachtet (1 von 5 Läufen): Detailseite bleibt leer, wenn der Aufruf ins Nachladen der Startseite fällt
        log("Detailseite blieb leer – zweiter Aufruf")
        bild("05a-details-leer")
        app_start(("--es", "ItemId", film["Id"]))
        xml = warte_auf(enthaelt(TESTFILM), 40)
    time.sleep(3)
    bild("05-details")
    merke("Detailseite Testfilm", xml is not None, "Fokus: " + fokus())

    taste("DPAD_CENTER", pause=3)  # Abspielen / Fortsetzen hat den Fokus
    if any("Fortsetzen" in t or "Von vorne" in t for t in texte(ui())):
        bild("05b-fortsetzen-frage")
        taste("DPAD_CENTER", pause=3)
    sitzung = None
    for _ in range(30):
        s = api.tv_sitzung()
        if s and (s.get("NowPlayingItem") or {}).get("Id") == film["Id"]:
            sitzung = s
            break
        time.sleep(2)
    merke("Wiedergabe gestartet (Server sieht den Film)", sitzung is not None,
          (sitzung or {}).get("PlayState", {}).get("PlayMethod", ""))
    time.sleep(30)
    bild("06-wiedergabe-30s")

    # 5. Spulen mit Vorschau (Trickplay): Leiste zeigen (OK), mit rechts spulen (Vorschaubild), OK übernimmt die Stelle
    taste("DPAD_CENTER", pause=1.5)
    bild("07a-leiste")
    for i in range(4):
        taste("DPAD_RIGHT", pause=0.4)
    bild("07b-spulen-vorschau")
    taste("DPAD_CENTER", pause=2)
    pos = 0
    for _ in range(10):
        pos = ((api.tv_sitzung() or {}).get("PlayState") or {}).get("PositionTicks", 0) / 1e7
        if pos > 60:
            break
        time.sleep(2)
    merke("Spulen mit dem Steuerkreuz (Position beim Server)", pos > 60, f"{pos:.0f} s")

    # 6. Tonspur wechseln über die Leiste (♪): Knopfreihe ansteuern, Liste öffnen, die andere Sprache wählen
    vorher = ((api.tv_sitzung() or {}).get("PlayState") or {}).get("AudioStreamIndex")
    # Jellyfin merkt sich die letzte Tonspur des Kontos -> immer auf die jeweils andere Sprache wechseln
    spuren = [s for s in ((api.ruf("GET", f"/Items/{film['Id']}?userId={api.user}&fields=MediaStreams") or {}).get("MediaStreams") or [])
              if s.get("Type") == "Audio"]
    jetzt_sprache = next((s.get("Language") or "" for s in spuren if s.get("Index") == vorher), "")
    ziel_muster = r"(?i)german|deutsch|\bdeu\b" if jetzt_sprache.startswith("en") else r"(?i)english|englisch|\beng\b"
    log(f"Tonspur jetzt {vorher} ({jetzt_sprache}) -> Ziel {'Deutsch' if jetzt_sprache.startswith('en') else 'Englisch'}")
    taste("DPAD_CENTER", pause=1.5)   # Leiste einblenden (OK; Fokus: Wiedergabeleiste)
    for _ in range(4):                # von der Wiedergabeleiste hoch in die Knopfreihe
        f = fokus_roh()
        if f and "SeekBar" not in f:
            break
        taste("DPAD_UP", pause=1.2)
    log("Player-Fokus nach oben: " + fokus_roh()[:120])
    bild("07c-knopfreihe-fokus")
    gewechselt = False
    if "SeekBar" not in fokus_roh():
        # Knopfreihe: Abspielen, Zurück, Vor, Untertitel, Tonspur -> ganz nach links, dann 4× rechts
        for _ in range(6):
            taste("DPAD_LEFT", pause=0.4)
        for _ in range(4):
            taste("DPAD_RIGHT", pause=0.6)
        log("Player-Fokus Tonspur-Knopf: " + (fokus() + " " + fokus_roh())[:140])
        taste("DPAD_CENTER", pause=2.5)
        bild("07d-tonspuren")
        optionen = [t for t in texte(ui()) if re.search(r"(?i)eng|englisch|deu|deutsch", t)]
        log("Tonspuren in der Liste: " + " | ".join(optionen[:6]))
        if optionen:
            # Liste in Server-Reihenfolge, Fokus beginnt oben -> so oft runter, wie die Zielspur in der Liste steht
            ziel_pos = next((i for i, s in enumerate(spuren) if re.search(ziel_muster, s.get("DisplayTitle") or s.get("Language") or "")), 1)
            log(f"Tonspur-Ziel an Position {ziel_pos + 1} von {len(spuren)}")
            for _ in range(ziel_pos):
                taste("DPAD_DOWN", pause=0.8)
            bild("07e-tonspur-ziel")
            taste("DPAD_CENTER", pause=4)
            gewechselt = True
    nachher = vorher
    for _ in range(8):
        nachher = ((api.tv_sitzung() or {}).get("PlayState") or {}).get("AudioStreamIndex")
        if nachher != vorher:
            break
        time.sleep(2)
    merke("Tonspur wechseln (andere Sprache)", gewechselt and nachher is not None and nachher != vorher, f"{vorher} -> {nachher}")

    # 7. Zurück: erst Leiste, dann Player – so oft, bis die Detailseite da ist (höchstens 5 Drücke)
    # Jellyfin merkt sich eine Stelle erst ab 5 % der Laufzeit (Film 108 min) -> vorher auf 15 min springen
    # nach dem Tonspurwechsel startet der Stream neu – erst danach springen (sonst verwirft der Player den Sprung)
    time.sleep(8)
    for versuch in range(3):
        try:
            api.befehl((api.tv_sitzung() or {})["Id"], "Playing/Seek?seekPositionTicks=9000000000")
        except Exception as e:  # noqa: BLE001
            log(f"Sprung auf 15 min: {e}")
        time.sleep(10)
        stelle = (((api.tv_sitzung() or {}).get("PlayState") or {}).get("PositionTicks") or 0) / 1e7
        log(f"Sprung auf 15 min, Versuch {versuch + 1}: {stelle:.0f} s")
        if stelle > 800:
            break
    zurueck = 0
    xml = None
    for zurueck in range(1, 6):
        taste("BACK", pause=3)
        xml = ui()
        if any(TESTFILM in t for t in texte(xml)) and not (api.tv_sitzung() or {}).get("NowPlayingItem"):
            break
    bild("08-zurueck")
    merke("Zurück aus dem Player auf die Detailseite", xml is not None and any(TESTFILM in t for t in texte(xml)), f"{zurueck}× Zurück")
    time.sleep(3)
    daten = api.ruf("GET", f"/Items/{film['Id']}?userId={api.user}") or {}
    pos = (daten.get("UserData") or {}).get("PlaybackPositionTicks", 0) / 1e7
    merke("Fortschritt beim Server gemeldet", pos > 600, f"{pos:.0f} s")

    # 8. Fernsteuerung vom Server (wie aus der Web-Oberfläche) – Sitzung vor jedem Befehl neu holen
    def befehl(pfad, daten=None):
        s = api.tv_sitzung()
        if not s:
            raise RuntimeError("TV-Sitzung nicht gefunden")
        try:
            api.befehl(s["Id"], pfad, daten)
        except urllib.error.HTTPError as e:
            log(f"Befehl {pfad.split('?')[0]}: HTTP {e.code}")
            raise

    def zustand():
        return (api.tv_sitzung() or {}).get("PlayState") or {}

    for name, schritt in (
        ("Abspielen", lambda: befehl(f"Playing?playCommand=PlayNow&itemIds={film['Id']}&startPositionTicks=600000000")),
    ):
        try:
            schritt()
        except Exception as e:  # noqa: BLE001
            log(f"Fernsteuerung {name}: {e}")
    ok = False
    for _ in range(20):
        if ((api.tv_sitzung() or {}).get("NowPlayingItem") or {}).get("Id") == film["Id"]:
            ok = True
            break
        time.sleep(2)
    merke("Fernsteuerung: Abspielen", ok)
    time.sleep(8)
    for name, pfad, daten, pruef in (
        ("Pause", "Playing/Pause", None, lambda: zustand().get("IsPaused") is True),
        ("Nachricht (nur deutscher Teil)", "Message", {"Header": "KinoLel", "TimeoutMs": 12000,
            "Text": "Pro Person ist nur eine Wiedergabe gleichzeitig möglich – bitte beende zuerst die andere. / "
                    "Személyenként egyszerre csak egy lejátszás lehetséges – előbb állítsd le a másikat."}, None),
        ("Weiter", "Playing/Unpause", None, lambda: zustand().get("IsPaused") is False),
        ("Spulen", "Playing/Seek?seekPositionTicks=1200000000", None,
         lambda: 115 <= (zustand().get("PositionTicks") or 0) / 1e7 <= 140),
        ("Stopp", "Playing/Stop", None, lambda: not (api.tv_sitzung() or {}).get("NowPlayingItem")),
    ):
        try:
            befehl(pfad, daten)
        except Exception as e:  # noqa: BLE001
            merke("Fernsteuerung: " + name, False, str(e)[:120])
            continue
        if name.startswith("Nachricht"):
            xml = warte_auf(enthaelt("Pro Person ist nur eine Wiedergabe"), 15, takt=1)
            bild("09-nachricht-vom-server")
            merke("Fernsteuerung: " + name, xml is not None and not any("Személyenként" in t for t in texte(xml)))
            taste("DPAD_CENTER", pause=1)
            continue
        ok = False
        for _ in range(10):
            time.sleep(2)
            if pruef():
                ok = True
                break
        merke("Fernsteuerung: " + name, ok, f"{(zustand().get('PositionTicks') or 0) / 1e7:.0f} s" if name == "Spulen" else "")

    # 9. Nächste Folge: Folge kurz vor dem Ende starten -> Countdown „Als Nächstes“ -> nächste Folge läuft von selbst
    nu = (api.ruf("GET", f"/Shows/NextUp?userId={api.user}&limit=5") or {}).get("Items", [])
    folge = None
    for kandidat in nu:
        folgen = (api.ruf("GET", f"/Shows/{kandidat['SeriesId']}/Episodes?userId={api.user}&seasonId={kandidat.get('SeasonId', '')}") or {}).get("Items", [])
        ids = [f["Id"] for f in folgen]
        if kandidat["Id"] in ids and ids.index(kandidat["Id"]) < len(ids) - 1:
            folge, naechste = kandidat, folgen[ids.index(kandidat["Id"]) + 1]
            break
    if folge:
        laenge = (api.ruf("GET", f"/Items/{folge['Id']}?userId={api.user}") or {}).get("RunTimeTicks") or 0
        try:
            befehl(f"Playing?playCommand=PlayNow&itemIds={folge['Id']}&startPositionTicks={max(0, laenge - 450_000_000)}")
        except Exception as e:  # noqa: BLE001
            log(f"Nächste Folge starten: {e}")
        weiter = None
        ende = time.time() + 150
        countdown_bild = False
        while time.time() < ende:
            if not countdown_bild and any(re.search(r"(?i)nächste|als nächstes|next", t) for t in texte(ui())):
                bild("10a-naechste-folge-countdown")
                countdown_bild = True
            jetzt = ((api.tv_sitzung() or {}).get("NowPlayingItem") or {}).get("Id")
            if jetzt == naechste["Id"]:
                weiter = jetzt
                break
            time.sleep(3)
        bild("10b-naechste-folge-laeuft")
        merke("Nächste Folge startet von selbst (Countdown)", weiter is not None,
              f"{folge.get('SeriesName')}: {folge.get('Name')} -> {naechste.get('Name')}")
        try:
            befehl("Playing/Stop")
        except Exception:  # noqa: BLE001
            pass
        time.sleep(4)
        for _ in range(3):  # zurück zur Startseite der App
            if not (api.tv_sitzung() or {}).get("NowPlayingItem"):
                break
            taste("BACK", pause=2)
    else:
        merke("Nächste Folge: passende Folge gefunden", False, "keine Serie mit weiterer Folge in „Als Nächstes“")

    # 10. Update mit Test-apps.json (Version 9.9.9, APK = diese Test-APK): Hinweis -> „Jetzt aktualisieren“ -> Download ->
    #     Androids Abfrage „App aktualisieren?“ -> bestätigen -> App neu installiert. Alles per Tastendruck.
    adb("shell", "appops", "set", PAKET, "REQUEST_INSTALL_PACKAGES", "allow")
    vorher_inst = re.search(r"lastUpdateTime=([^\n]+)", adb("shell", "dumpsys", "package", PAKET))
    server = test_server({"androidtv": {"version": "9.9.9", "url": "http://10.0.2.2:8765/kinolel-tv-test.apk"}})
    app_stopp()
    einstellungen_schreiben({"apps_liste": "http://10.0.2.2:8765/apps.json", "neuigkeiten_gesehen": "99.0.0"})
    app_start()
    time.sleep(4)  # nicht lesen, während der Dialog einblendet (uiautomator + Android 14: Absturz in der Bedienungshilfe)
    xml = warte_auf(enthaelt("Update verfügbar"), 60, takt=3)
    bild("11-update-hinweis")
    merke("Update-Hinweis (Test-apps.json 9.9.9)", xml is not None and "9.9.9" in " ".join(texte(xml or "")),
          "Fokus: " + fokus(xml or ""))
    if xml is not None:
        taste("DPAD_CENTER", pause=3)  # „Jetzt aktualisieren“ hat den Fokus
        abfrage = warte_auf(lambda x: ("packageinstaller" in x)
                            and any(re.search(r"(?i)update|aktualisieren|installieren|install", t) for t in texte(x)), 90, takt=3)
        bild("11b-android-abfrage")
        if abfrage:
            # Android-TV-Abfrage: „Update“ links, „Abbrechen“ rechts mit Fokus -> nach links
            for _ in range(4):
                if re.search(r"(?i)^(update|aktualisieren|installieren|install)$", fokus()):
                    break
                taste("DPAD_LEFT", pause=0.8)
            log("Installationsabfrage, Fokus: " + fokus())
            taste("DPAD_CENTER", pause=10)
        nachher_inst = re.search(r"lastUpdateTime=([^\n]+)", adb("shell", "dumpsys", "package", PAKET))
        merke("Update: Download + Installation über die Android-Abfrage",
              bool(abfrage) and vorher_inst and nachher_inst and vorher_inst[1] != nachher_inst[1],
              f"{vorher_inst and vorher_inst[1]} -> {nachher_inst and nachher_inst[1]}")
        bild("11c-nach-update")
    else:
        taste("BACK", pause=2)  # = Später
    server.shutdown()

    # 11. „Was ist neu“ einmal nach einem Update (zuletzt gesehen: 0.0.9)
    app_stopp()
    einstellungen_schreiben({"neuigkeiten_gesehen": "0.0.9", "spaeter_bis": int(time.time() * 1000) + 3600_000})
    app_start()
    time.sleep(4)
    xml = warte_auf(enthaelt("Neu in KinoLel"), 60, takt=3)
    bild("12-was-ist-neu")
    merke("„Was ist neu“ nach Update", xml is not None, "Fokus: " + fokus(xml or ""))
    taste("DPAD_CENTER", pause=2)
    app_stopp()
    app_start()
    time.sleep(8)
    merke("„Was ist neu“ nur einmal", not any("Neu in KinoLel" in t for t in texte(ui())))

    # 12. Speicher (Ziel: Chromecast HD mit 1,5 GB stabil)
    mem = adb("shell", "dumpsys", "meminfo", PAKET)
    gesamt = re.search(r"TOTAL PSS:\s*(\d+)", mem) or re.search(r"TOTAL\s+(\d+)", mem)
    mb = int(gesamt[1]) / 1024 if gesamt else 0
    with open(os.path.join(AUS, "meminfo.txt"), "w") as f:
        f.write(mem)
    merke("Speicher (PSS)", 0 < mb < 400, f"{mb:.0f} MB")

    # 13. Zurück auf der Startseite -> Google-TV-Startbildschirm, KinoLel bleibt im Hintergrund (Prozess lebt)
    for _ in range(3):
        taste("BACK", pause=1.5)
    oben = adb("shell", "dumpsys", "activity", "activities")
    vorne = re.search(r"(?:mResumedActivity|topResumedActivity)[^\n]*", oben)
    lebt = bool(adb("shell", "pidof", PAKET).strip())
    bild("13-zurueck-startbildschirm")
    merke("Zurück auf der Startseite: Google-TV-Startbildschirm, App im Hintergrund",
          lebt and vorne is not None and PAKET not in vorne[0], (vorne[0] if vorne else "?")[:120])

    # 14. Wieder öffnen wie vom Google-TV-Startbildschirm (Lel 24.10.: „… wieder geöffnet … nur noch der alte Hintergrund
    #     und keine Inhalte“): nach Zurück, nach Home, nach Home + beendetem App-Prozess (Speichermangel), nach Pause
    def vom_startbildschirm():
        adb("shell", "monkey", "-p", PAKET, "-c", "android.intent.category.LEANBACK_LAUNCHER", "1")

    def startseite_da(name):
        xml = warte_auf(enthaelt("Als Nächstes", "Weiter ansehen", "Kürzlich"), 40, takt=3)
        bild(name)
        return xml is not None

    vom_startbildschirm()
    merke("Wieder öffnen nach Zurück: Startseite mit Inhalten", startseite_da("14a-wieder-nach-zurueck"))
    taste("HOME", pause=4)
    vom_startbildschirm()
    merke("Wieder öffnen nach Home-Taste: Startseite mit Inhalten", startseite_da("14b-wieder-nach-home"))
    taste("HOME", pause=4)
    adb("shell", "am", "kill", PAKET)  # wie der Chromecast bei Speichermangel: Prozess im Hintergrund beendet
    time.sleep(3)
    log("Prozess im Hintergrund beendet: " + ("nein" if adb("shell", "pidof", PAKET).strip() else "ja"))
    vom_startbildschirm()
    merke("Wieder öffnen nach beendetem Prozess: Startseite mit Inhalten", startseite_da("14c-wieder-nach-prozessende"))
    taste("HOME", pause=60)  # längere Pause
    vom_startbildschirm()
    merke("Wieder öffnen nach 60 s Pause: Startseite mit Inhalten", startseite_da("14d-wieder-nach-pause"))
    # wie auf Lels Fotos: erst eine andere Seite (Wünsche), dann Home-Taste, dann wieder öffnen
    for _ in range(8):
        if fokus() in ("Startseite", "Suche", "Wünsche"):
            break
        taste("DPAD_UP")
    for _ in range(4):
        if fokus() == "Wünsche":
            break
        taste("DPAD_RIGHT")
    taste("DPAD_CENTER", pause=2)
    auf_wuensche = warte_auf(enthaelt("wuensche.kinolel.de"), 20) is not None
    taste("HOME", pause=4)
    vom_startbildschirm()
    # wieder da: Startseite mit Reihen oder die Wünsche-Seite, nur nicht leer
    da = warte_auf(enthaelt("Als Nächstes", "Weiter ansehen", "Kürzlich", "wuensche.kinolel.de"), 40, takt=3)
    bild("14e-wieder-nach-wuensche")
    merke("Wieder öffnen nach Wünsche + Home-Taste: Inhalte da", da is not None and auf_wuensche,
          "" if auf_wuensche else "Wünsche-Seite nicht erreicht")

    # 14f. Lels Absturz 24.10. (v0.1.0): Bibliothek aus einem Google-TV-Kanal („Meine Medien“) öffnen, während KinoLel im
    #      Hintergrund liegt – die Seite wurde ohne ihre Argumente aufgebaut (NullPointerException)
    ansichten = (api.ruf("GET", f"/UserViews?userId={api.user}") or {}).get("Items", [])
    bib = next((v for v in ansichten if v.get("CollectionType") == "movies"), ansichten[0] if ansichten else None)
    if bib:
        taste("HOME", pause=3)
        pid_vorher = adb("shell", "pidof", PAKET).strip()
        app_start(("--es", "ItemId", bib["Id"], "--ez", "ItemIsUserView", "true"))
        xml = warte_auf(enthaelt(bib.get("Name", "Filme")), 30, takt=3)
        time.sleep(3)
        bild("14f-bibliothek-aus-kanal")
        merke("Bibliothek aus einem Google-TV-Kanal öffnen (App im Hintergrund, Lels Absturz 24.10.)",
              xml is not None and adb("shell", "pidof", PAKET).strip() == pid_vorher, bib.get("Name", ""))
        taste("BACK", pause=2)

    # 15. Öffnen im Bildschirmvideo (Lel 25.10.: „… sieht man kurz für eine halbe Sekunde irgendwelche komischen
    #     Menüelemente … Der Ladescreen muss also noch verlängert werden.“)
    startvideo()
    xml = warte_auf(enthaelt("Als Nächstes", "Weiter ansehen", "Kürzlich", "Meine Medien"), 40, takt=3)
    merke("Startseite ohne Live-TV-Abschnitt (Server ohne Sender)", xml is not None
          and not any(w in t for t in texte(xml) for w in ("Live-TV", "Läuft gerade")))

    # 16. Alle Einstellungsseiten öffnen (Lel 25.10.: „… in den Einstellungen steht irgendwo immer noch ‚Jellyfin‘“)
    seiten = einstellungen_rundgang()
    merke("Einstellungen: Seiten mit der Fernbedienung geöffnet", len(seiten) >= 8, f"{len(seiten)} Seiten")

    # 17. Sprache wie in KinoLel gewählt (Lel 25.10.: „Sind Updatenachrichten auch auf Ungarisch … wenn die ausgewählte
    #     Sprache auf Ungarisch ist?“): App auf Deutsch, im Konto „Magyar“ -> „Was ist neu“ auf Ungarisch.
    #     Danach App wieder Deutsch, Konto-Eintrag entfernt (am Ende stellt finally den Ursprungszustand her).
    sprache_konto("hu")
    app_stopp()
    einstellungen_schreiben({"neuigkeiten_gesehen": "0.0.9", "spaeter_bis": int(time.time() * 1000) + 3600_000})
    app_start()
    time.sleep(12)  # Sprache lesen, App-Sprache umstellen, Activity neu – währenddessen nicht lesen (Bedienungshilfe)
    xml = warte_auf(enthaelt("Újdonságok", "Neu in KinoLel"), 60, takt=3)
    bild("17-was-ist-neu-ungarisch")
    titel = next((t for t in texte(xml or "") if "Újdonságok" in t or "Neu in KinoLel" in t), "nicht gezeigt")
    gebiet = adb("shell", "cmd", "locale", "get-app-locales", PAKET).strip()
    merke("„Was ist neu“ ungarisch (App auf Deutsch, im Konto Magyar)", "Újdonságok" in titel, f"{titel}; {gebiet[-40:]}")
    if xml is not None:
        taste("DPAD_CENTER", pause=2)
    sprache_konto(None)
    app_stopp()
    adb("shell", "cmd", "locale", "set-app-locales", PAKET, "--locales", "de-DE")


try:
    main()
except Exception as e:  # Testfehler nicht verschlucken, aber Abmelden trotzdem
    merke("Ablauf", False, f"{type(e).__name__}: {e}")
finally:
    # Abmelden: TV-Sitzung (Zugang aus der Test-App, nur Debug) und Hilfssitzung – nie ausgeben
    try:
        roh = subprocess.run(["adb", "shell", "run-as", PAKET, "cat", "files/authentication_store.json"],
                             capture_output=True, timeout=20).stdout.decode()
        for t in set(re.findall(r'"access_token"\s*:\s*"([0-9a-f]{32})"', roh)):
            api.abmelden(token=t)
            log("TV-Sitzung abgemeldet")
    except Exception as e:
        log(f"TV-Abmeldung: {e}")
    if LIZENZ_JELLYFIN:
        log("Info – „Jellyfin“ in den Lizenzen (bleibt, Namen der Grundlage): " + "; ".join(sorted(LIZENZ_JELLYFIN))[:600])
    merke("Kein „Jellyfin“ auf allen geprüften Seiten (ohne Lizenzen)", not JELLYFIN_FUNDE,
          "; ".join(f"{k} ({v})" for k, v in JELLYFIN_FUNDE.items())[:400])
    if api.token:
        startseite_zurueck()
        api.abmelden()
        log("Hilfssitzung abgemeldet")
    # ohne die Masse an uiautomator-/Fenster-Zeilen, damit der ganze Lauf hineinpasst
    zeilen = [z for z in adb("logcat", "-d", timeout=60).splitlines()
              if "AccessibilityNodeInfoDumper" not in z and " V WindowManager" not in z and " V ShellTransitions" not in z]
    with open(os.path.join(AUS, "logcat.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen)[-1500000:])
    # Kanäle für den Fernseher-Startbildschirm (Lel 24.10.): „Weiter ansehen“, „Als Nächstes“, „Neu in KinoLel“
    kanaele = [z for z in zeilen if "KinoLel-Kanäle:" in z]
    merke("Startbildschirm-Kanäle Weiter ansehen / Als Nächstes / Neu in KinoLel / Meine Medien angelegt",
          bool(kanaele) and "alle angelegt" in kanaele[-1], (kanaele[-1].split("KinoLel-Kanäle:")[-1] if kanaele else "kein Lauf"))
    with open(os.path.join(AUS, "ergebnis.json"), "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=1)
    fehler = [k for k, v in ergebnis.items() if not v["ok"]]
    log(f"Ergebnis: {len(ergebnis) - len(fehler)} von {len(ergebnis)} OK" + (f" – Fehler: {', '.join(fehler)}" if fehler else ""))
    sys.exit(0)
