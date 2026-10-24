# KinoLel TV (Android TV / Google TV)

Eigene KinoLel-App für Fernseher mit **Chromecast mit Google TV** und andere Android-TV-/Google-TV-Geräte –
alles nur mit der Fernbedienung (Steuerkreuz, OK, Zurück). Fester Server `https://kinolel.de`.

- **Grundlage:** Fork der offiziellen [Jellyfin-App für Android TV](https://github.com/jellyfin/jellyfin-androidtv)
  (v0.20.0-beta.4), Lizenz GPL-2.0 (siehe [LICENSE](LICENSE), Original-Liesmich [README-jellyfin.md](README-jellyfin.md)).
  Alle Rechte an der Jellyfin-App liegen bei den Jellyfin-Autoren.
- **Marke:** Name, Server, Kennung (`de.kinolel.tv`) und Version stehen nur in [marke.properties](marke.properties).
  Bilder (Banner, Symbol, Logo): `marke/tv_bilder.py` (Pillow, KinoLel-Logo, Schrift Inter – Lizenz `marke/Inter-OFL.txt`).
- **KinoLel-Zusätze** (`app/src/main/java/org/jellyfin/androidtv/kinolel/`):
  - Anmeldung mit Quick Connect: Code + QR-Code (öffnet am Handy kinolel.de mit eingetragenem Code)
  - Kopfleiste mit KinoLel-Logo und „Wünsche“ (QR-Codes); „Nach Updates suchen“ unter Einstellungen → Über
  - Hintergrund im KinoLel-Design (nie das Startbild aus dem Server-Branding)
  - Kanäle auf dem Fernseher-Startbildschirm: „Weiter ansehen“, „Als Nächstes“, „Neu in KinoLel“
  - Dialoge im KinoLel-Stil
  - Update-Prüfung bei jedem Start über `https://kinolel.de/web/kinolel/apps.json` (Schlüssel `androidtv`)
  - „Was ist neu“ nach Updates (`app/src/main/assets/kinolel/neuigkeiten.json`)
  - Nachrichten vom Server (z. B. 1-Stream-Grenze) verständlich in der Sprache der Oberfläche
- **Build und Test:** GitHub Actions ([.github/workflows/tv.yml](.github/workflows/tv.yml)): Debug- und signierte
  Release-APK, Unit-Tests, Test im Android-TV-Emulator nur mit Tastendrücken ([.github/scripts/tv_test.py](.github/scripts/tv_test.py)).
- **Installation am Fernseher:** [TESTANLEITUNG.md](TESTANLEITUNG.md).
