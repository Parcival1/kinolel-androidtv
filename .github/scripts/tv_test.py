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


def ui():
    xml = adb("exec-out", "uiautomator", "dump", "/dev/tty", timeout=30)
    return xml[: xml.rfind(">") + 1] if ">" in xml else ""


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
    subprocess.run(["adb", "shell", "run-as", PAKET, "sh", "-c",
                    "mkdir -p shared_prefs && cat > shared_prefs/kinolel.xml"], input=inhalt.encode(), timeout=30)


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


# --- Test-Server für die Update-Prüfung (der Emulator erreicht den Runner unter 10.0.2.2) ------------------------

def test_server(apps_json):
    class Antwort(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(apps_json).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
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
    # Lel 24.10.: „… aber auch mit Tippen möglich machen“ – Passwort-Weg gleichwertig daneben, Fokus im Benutzernamen
    merke("Anmeldung: Benutzername/Passwort daneben", bool(xml) and any("Mit Benutzername und Passwort" in t for t in texte(xml)),
          "Fokus: " + fokus(xml or ""))
    if not code or not PW:
        if not PW:
            log("Kein KINOLEL_TEST_PW (Secret fehlt) – Test endet nach dem Anmeldebildschirm.")
        return

    api.anmelden()
    try:
        api.ruf("POST", f"/QuickConnect/Authorize?code={code}&userId={api.user}")
        merke("Anmeldung: Code am „Handy“ bestätigt", True)
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
    merke("Startseite: Zeilen Weiter ansehen / Als Nächstes", len(zeilen) == 2, ", ".join(zeilen) or "keine (Konto ohne laufende Titel?)")
    merke("Startseite: Fokus erkennbar", bool(fokus(xml)), fokus(xml))

    # 3. Kopfleiste: Wünsche und Hilfe nur mit dem Steuerkreuz
    for ziel, kennzeichen, name in (("Wünsche", "wuensche.kinolel.de", "03-wuensche"), ("Hilfe", "Hilfe auf kinolel.de", "04-hilfe")):
        gefunden = False
        for _ in range(8):  # nach oben in die Kopfleiste
            if fokus() in ("Startseite", "Suche", "Wünsche", "Hilfe"):
                break
            taste("DPAD_UP")
        for _ in range(8):  # nach rechts bis zum Ziel
            f = fokus()
            if f == ziel:
                gefunden = True
                break
            taste("DPAD_RIGHT" if f in ("Startseite", "Suche") or not f else "DPAD_LEFT")
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
    app_start(("--es", "ItemId", film["Id"]))
    xml = warte_auf(enthaelt(TESTFILM), 60)
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

    # 5. Spulen mit Vorschau (Trickplay): Leiste zeigen, nach rechts spulen, sofort fotografieren
    taste("DPAD_CENTER", pause=1.5)
    bild("07a-leiste")
    for i in range(4):
        taste("DPAD_RIGHT", pause=0.4)
    bild("07b-spulen-vorschau")
    time.sleep(3)
    s = api.tv_sitzung() or {}
    pos = (s.get("PlayState") or {}).get("PositionTicks", 0) / 1e7
    merke("Spulen (Position beim Server)", pos > 35, f"{pos:.0f} s")

    # 6. Zurück: erst Leiste, dann Player
    taste("BACK", pause=2)
    taste("BACK", pause=4)
    bild("08-zurueck")
    xml = warte_auf(enthaelt(TESTFILM), 30)
    merke("Zurück aus dem Player auf die Detailseite", xml is not None)
    daten = api.ruf("GET", f"/Items/{film['Id']}?userId={api.user}") or {}
    pos = (daten.get("UserData") or {}).get("PlaybackPositionTicks", 0) / 1e7
    merke("Fortschritt beim Server gemeldet", pos > 20, f"{pos:.0f} s")

    # 7. Fernsteuerung vom Server (wie aus der Web-Oberfläche)
    s = api.tv_sitzung()
    if s:
        sid = s["Id"]
        api.befehl(sid, f"Playing?playCommand=PlayNow&itemIds={film['Id']}&startPositionTicks=600000000")
        ok = False
        for _ in range(20):
            s2 = api.tv_sitzung() or {}
            if (s2.get("NowPlayingItem") or {}).get("Id") == film["Id"]:
                ok = True
                break
            time.sleep(2)
        merke("Fernsteuerung: Abspielen", ok)
        time.sleep(8)
        api.befehl(sid, "Playing/Pause")
        time.sleep(4)
        merke("Fernsteuerung: Pause", ((api.tv_sitzung() or {}).get("PlayState") or {}).get("IsPaused") is True)
        api.befehl(sid, "Message", {"Header": "KinoLel", "TimeoutMs": 12000,
                                    "Text": "Pro Person ist nur eine Wiedergabe gleichzeitig möglich – bitte beende zuerst die andere. / "
                                            "Személyenként egyszerre csak egy lejátszás lehetséges – előbb állítsd le a másikat."})
        xml = warte_auf(enthaelt("Pro Person ist nur eine Wiedergabe"), 15, takt=1)
        bild("09-nachricht-vom-server")
        merke("Fernsteuerung: Nachricht (nur deutscher Teil)", xml is not None and not any("Személyenként" in t for t in texte(xml)))
        taste("DPAD_CENTER", pause=1)
        api.befehl(sid, "Playing/Unpause")
        time.sleep(4)
        merke("Fernsteuerung: Weiter", ((api.tv_sitzung() or {}).get("PlayState") or {}).get("IsPaused") is False)
        api.befehl(sid, "Playing/Seek?seekPositionTicks=1200000000")
        time.sleep(5)
        pos = (((api.tv_sitzung() or {}).get("PlayState") or {}).get("PositionTicks") or 0) / 1e7
        merke("Fernsteuerung: Spulen", 115 <= pos <= 140, f"{pos:.0f} s")
        api.befehl(sid, "Playing/Stop")
        time.sleep(5)
        merke("Fernsteuerung: Stopp", not (api.tv_sitzung() or {}).get("NowPlayingItem"))
    else:
        merke("Fernsteuerung: Sitzung gefunden", False)

    # 8. Update-Hinweis mit Test-apps.json (Version 9.9.9)
    server = test_server({"androidtv": {"version": "9.9.9", "url": "http://10.0.2.2:8765/nicht-da.apk"}})
    app_stopp()
    einstellungen_schreiben({"apps_liste": "http://10.0.2.2:8765/apps.json", "neuigkeiten_gesehen": "99.0.0"})
    app_start()
    xml = warte_auf(enthaelt("Update verfügbar"), 60)
    bild("10-update-hinweis")
    merke("Update-Hinweis (Test-apps.json 9.9.9)", xml is not None and "9.9.9" in " ".join(texte(xml or "")),
          "Fokus: " + fokus(xml or ""))
    taste("BACK", pause=2)  # = Später
    server.shutdown()

    # 9. „Was ist neu“ einmal nach einem Update (zuletzt gesehen: 0.0.9)
    app_stopp()
    einstellungen_schreiben({"neuigkeiten_gesehen": "0.0.9", "spaeter_bis": int(time.time() * 1000) + 3600_000})
    app_start()
    xml = warte_auf(enthaelt("Neu in KinoLel"), 60)
    bild("11-was-ist-neu")
    merke("„Was ist neu“ nach Update", xml is not None, "Fokus: " + fokus(xml or ""))
    taste("DPAD_CENTER", pause=2)
    app_stopp()
    app_start()
    time.sleep(8)
    merke("„Was ist neu“ nur einmal", not any("Neu in KinoLel" in t for t in texte(ui())))

    # 10. Speicher (Ziel: Chromecast HD mit 1,5 GB stabil)
    mem = adb("shell", "dumpsys", "meminfo", PAKET)
    gesamt = re.search(r"TOTAL PSS:\s*(\d+)", mem) or re.search(r"TOTAL\s+(\d+)", mem)
    mb = int(gesamt[1]) / 1024 if gesamt else 0
    with open(os.path.join(AUS, "meminfo.txt"), "w") as f:
        f.write(mem)
    merke("Speicher (PSS)", 0 < mb < 400, f"{mb:.0f} MB")


try:
    main()
except Exception as e:  # Testfehler nicht verschlucken, aber Abmelden trotzdem
    merke("Ablauf", False, f"{type(e).__name__}: {e}")
finally:
    # Abmelden: TV-Sitzung (Zugang aus der Test-App, nur Debug) und Hilfssitzung – nie ausgeben
    try:
        roh = subprocess.run(["adb", "shell", "run-as", PAKET, "cat", "files/authentication_store.json"],
                             capture_output=True, timeout=20).stdout.decode()
        for t in set(re.findall(r'"accessToken"\s*:\s*"([0-9a-f]{32})"', roh)):
            api.abmelden(token=t)
            log("TV-Sitzung abgemeldet")
    except Exception as e:
        log(f"TV-Abmeldung: {e}")
    if api.token:
        api.abmelden()
        log("Hilfssitzung abgemeldet")
    with open(os.path.join(AUS, "logcat.txt"), "w", encoding="utf-8") as f:
        f.write(adb("logcat", "-d", timeout=60)[-400000:])
    with open(os.path.join(AUS, "ergebnis.json"), "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=1)
    fehler = [k for k, v in ergebnis.items() if not v["ok"]]
    log(f"Ergebnis: {len(ergebnis) - len(fehler)} von {len(ergebnis)} OK" + (f" – Fehler: {', '.join(fehler)}" if fehler else ""))
    sys.exit(0)
