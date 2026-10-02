# SLDGridy

Einpolige Übersichtsschaltpläne (Single-Line-Diagramme) für Photovoltaikanlagen, Transformatorstationen und Niederspannungsverteilungen, gezeichnet wie in einem CAD-Programm: maßhaltig in Millimetern, mit Modell und Zeichnungsrahmen, Raster und Objektfang, Ebenen, Blöcken mit Attributen und Drucken bis A0.

Lizenz: GPL-3.0-or-later. Zielsystem: Ubuntu 24.04 (X11 und Wayland).

## Installation

```bash
sudo apt install ./dist/sldgridy_<version>_all.deb
```

Danach steht „SLDGridy“ im Anwendungsmenü, und `.sldg`-Dateien öffnen sich per Doppelklick. Deinstallation mit `sudo apt remove sldgridy`.

## Kurzanleitung

### Erste Zeichnung

1. Im Reiter **Modell** zeichnen. Der Nullpunkt ist mit einem Achsenkreuz markiert, 1 Einheit = 1 mm.
2. Symbole aus dem Dock **Bibliothek** (links) in die Zeichnung ziehen oder doppelklicken. Die mitgelieferte Bibliothek „DIN EN 60617“ enthält 40 Symbole für PV, Trafostation und Niederspannung. Nach dem Einfügen fragt das Programm die Attribute `BMK`, `TYP` und `WERT` ab.
3. Mit **Zeichnen > Leitung** (Strg+W) Anschlusspunkte verbinden. Die Leitung rastet auf Anschlusspunkte (magentafarbene Marker) und knickt automatisch rechtwinklig. **Sammelschiene** zeichnet eine 0,7-mm-Schiene, an die überall angeschlossen werden kann. Verbindungspunkte entstehen automatisch.
4. Leitungen beschriften: Doppelklick auf die Leitung oder Eigenschaften-Dock, z. B. „NYY-J 5x16“.
5. Im Reiter **Blatt 1** liegt der Zeichnungsrahmen A0 quer mit Schriftfeld. **Blatt > Schriftfeld ausfüllen** setzt Projekt, Firma, Titel usw.
6. **Datei > Drucken** (Strg+P) oder **Datei > Exportieren** als PDF, SVG oder PNG.

### Maus und Tastatur

| Aktion | Bedienung |
|---|---|
| Zoomen | Mausrad (auf den Cursor) |
| Verschieben der Ansicht | mittlere Maustaste ziehen |
| Grenzen zoomen | Pos1 |
| Auswählen | Klick; Umschalt+Klick fügt hinzu oder nimmt weg |
| Fenster / Kreuzen | links nach rechts ziehen: vollständig innen; rechts nach links: berührt |
| Objekte verschieben | ausgewählte Objekte direkt ziehen oder **Ändern > Verschieben** |
| Griffe | Klick auf einen blauen Griff, dann neue Position klicken |
| Befehl abbrechen | Esc |
| Befehl beenden | Enter oder Rechtsklick |
| Letzten Befehl wiederholen | Leertaste |
| Löschen | Entf |
| Rückgängig / Wiederholen | Strg+Z / Strg+Y (oder Strg+Umschalt+Z) |
| Ausschneiden / Kopieren / Einfügen | Strg+X / Strg+C / Strg+V |
| Objektfang / Raster / Ortho / Rasterfang | F3 / F7 / F8 / F9 |

Ändern-Befehle ohne Auswahl fragen zuerst nach Objekten: wählen und mit Enter bestätigen.

### Koordinaten eingeben

Während eines Zeichenbefehls einfach lostippen, die Eingabe landet in der Zeile **Befehl** unter der Zeichenfläche:

- `120,45` absoluter Punkt
- `@25,0` relativ zum letzten Punkt
- `30` Länge in Cursorrichtung (nur bei Ortho)
- Mit Dezimalkomma die Werte mit Semikolon trennen: `12,5;7,5`

### Ebenen und Eigenschaften

Im Dock **Ebenen**: Name, Farbe, Linienbreite (ISO 128: 0,18 bis 0,7 mm), Linienart, sichtbar, gesperrt, druckbar. Doppelklick setzt die aktuelle Ebene. Das Dock **Eigenschaften** ändert Ebene, Farbe, Breite, Linienart, Text, Blockattribute, Leitungsbeschriftung und Ansichtsfenster der Auswahl.

### Blöcke

- **Block > Block aus Auswahl** (Strg+B): Namen vergeben, dann Basispunkt klicken.
- **Block > Attribut definieren** und **Anschlusspunkt setzen** legen Platzhalter und Anschlüsse an, am besten im Blockeditor.
- **Block > Block bearbeiten** öffnet den Blockeditor mit gelber Leiste. „Speichern und schließen“ aktualisiert alle Referenzen.
- **Ändern > Auflösen** ersetzt eine Referenz durch ihre Einzelobjekte.
- **Block > In Benutzerbibliothek speichern** legt den Block in `~/.local/share/sldgridy/library/eigene.sldglib` ab. Bibliotheken lassen sich importieren und exportieren.

Wird ein Block verschoben, gedreht oder gespiegelt, wandern die Leitungsenden auf seinen Anschlusspunkten mit.

### Zeichnungsrahmen

- Reiter unten: Modell und Blätter. Rechtsklick auf einen Reiter bietet Neu, Umbenennen, Duplizieren, Löschen, Format und Vorlagen. Reiter lassen sich verschieben.
- Formate A4 bis A0, hoch und quer, Rahmen nach DIN EN ISO 5457, Schriftfeld nach DIN EN ISO 7200 (180 mm). Das Schriftfeld ist der Block „Schriftfeld“ und kann im Blockeditor angepasst werden.
- Doppelklick in ein Ansichtsfenster aktiviert es: Mausrad zoomt, mittlere Taste verschiebt den Ausschnitt, Esc beendet. Maßstab (1:1, 2:1, 1:2, 1:5, 1:10 oder frei), Sperre und „Modellgrenzen einpassen“ im Eigenschaften-Dock.
- Im Modell zeigen gestrichelte Umrisse, was auf welches Blatt passt (**Blatt > Blattumrisse im Modell**).
- **Blatt > Als Vorlage speichern** legt eigene Rahmen in `~/.local/share/sldgridy/templates/` ab.

### Drucken und Export

- **1:1**: Blattformat gleich Papierformat (A0 auf dem Plotter). Ist das Format am Drucker nicht verfügbar, ist 1:1 gesperrt.
- **Einpassen**: Blatt auf das gewählte Papier skaliert (z. B. A0 auf A3).
- **Kacheln**: 1:1 auf kleinere Bögen mit 10 mm Überlappung, Schnittmarken und Kachelnummer `Z1/S2`.
- Im Reiter Modell gibt es zusätzlich den Schnelldruck, der die Modellgrenzen auf das Papier einpasst.
- Optionen: Schwarz-weiß, nur druckbare Ebenen. Die Vorschau warnt, wenn der Drucker nicht bis in den Rahmen drucken kann.
- PDF als Vektor mit exakter Blattgröße und einer Seite je Blatt, SVG in mm, PNG mit wählbarer Auflösung.

## Dateien und Speicherorte

| Was | Wo |
|---|---|
| Zeichnung | `*.sldg` (JSON, versioniert; beim Speichern bleibt `*.sldg.bak`) |
| Bibliothek | `*.sldglib`; mitgeliefert in `/usr/share/sldgridy/library/`, eigene in `~/.local/share/sldgridy/library/` |
| Rahmenvorlage | `*.sldgframe`; mitgeliefert in `/usr/share/sldgridy/templates/`, eigene in `~/.local/share/sldgridy/templates/` |
| Automatische Sicherung | alle 5 Minuten nach `~/.cache/sldgridy/`; nach einem Absturz bietet der nächste Start die Wiederherstellung an |
| Einstellungen | `~/.config/sldgridy/sldgridy.conf` |

## Entwicklung

```bash
sudo apt install python3-venv python3-pyqt6 python3-pyqt6.qtsvg lintian
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/python -m sldgridy                     # starten
QT_QPA_PLATFORM=offscreen .venv/bin/pytest       # Tests ohne Display
.venv/bin/ruff check . && .venv/bin/ruff format --check .
./packaging/build-deb.sh                         # erzeugt dist/sldgridy_<version>_all.deb
lintian dist/sldgridy_*.deb
```

Die Spezifikation und alle Festlegungen stehen in `CLAUDE.md`.
