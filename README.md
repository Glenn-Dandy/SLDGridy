# SLDGridy

[![Release](https://img.shields.io/github/v/release/Glenn-Dandy/SLDGridy)](https://github.com/Glenn-Dandy/SLDGridy/releases/latest)
[![License: GPL v3](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)
[![Support](https://img.shields.io/badge/♥-Support%20the%20project-c62828)](https://paypal.me/GlennDandy)

**[English](#english) · [Deutsch](#deutsch)**

---

## English

CAD-style editor for single-line electrical diagrams on Linux: photovoltaic systems, transformer stations and low-voltage distribution. Drawing in real millimetres with model space and sheet layouts, grid and object snap, layers, blocks with attributes and connection points, a symbol library to DIN EN 60617, and printing up to A0.

The user interface is available in **English and German** (View > Sprache / Language).

License: GPL-3.0-or-later. Target system: Ubuntu 24.04 LTS and 26.04 LTS (X11 and Wayland).

### Installation

Download `sldgridy_<version>_all.deb` from the [releases](https://github.com/Glenn-Dandy/SLDGridy/releases/latest) and install it:

```bash
sudo apt install ./sldgridy_<version>_all.deb
```

SLDGridy then appears in the application menu and `.sldg` files open with a double click. Remove it with `sudo apt remove sldgridy`.

### Quick start

1. Draw in the **Model** tab. The origin is marked with axes; 1 unit = 1 mm.
2. Drag symbols from the **Library** dock (left) into the drawing or double-click them. The shipped library “Symbols to DIN EN 60617” contains 42 symbols for PV, transformer stations and low voltage; a second library “Further symbols” holds common symbols without a standard drawing (selective main switches SHU/SHA, PV module, DC solar storage, AC-coupled wallbox, Internet cloud). After inserting, the program asks for the attributes `BMK` (reference designation), `TYP` and `WERT`; PV module, inverter, wallbox and DC solar storage also have `HERSTELLER` (manufacturer). Shift+Enter in a value starts a new line; the attributes below move down.
3. Connect connection points with **Draw > Wire** (Ctrl+W). Wires snap to connection points (magenta markers) and bend at right angles automatically. **Bus bar** draws a 0.7 mm bar that can be connected anywhere. Connection dots appear automatically.
4. Label wires by double-clicking them or in the Properties dock, e.g. “NYY-J 5x16”; the dock also sets side, position (automatic, start, end, free), alignment (left, centre, right) and size of the label. A selected labelled wire has an orange diamond grip at its label: drag it along the wire to place the label on any segment. Hollow square grips in the middle of each segment shift just that segment; the wire ends stay connected. Grips can be dragged (press, drag, release) or clicked and then placed with a second click; the grip under the mouse turns red.
- Right-click on a wire end at the edge of a block: “Set docking point here” makes it a connection point of this block instance, so the wire follows when the block is moved.
- Wires attached to another wire or bus bar (T branch or end to end) follow when that wire is moved, rotated or reshaped; points separated with right-click “Separate” stay put. This also travels along: a moved block pulls its wire, the wire pulls its branches.
- Right-click inside a wire segment: “Add point” splits it, so each part gets its own segment grip and can be offset on its own.
5. The **Sheet 1** tab holds an A0 landscape frame with title block. **Sheet > Fill in title block** sets project, company, title and so on.
6. **File > Print** (Ctrl+P) or **File > Export** to PDF, SVG or PNG.

### Mouse and keyboard

| Action | How |
|---|---|
| Zoom | mouse wheel (towards the cursor) |
| Pan | drag with the middle mouse button |
| Zoom extents | Home |
| Select | click; Shift+click adds or removes |
| Window / crossing | drag left to right: fully inside; right to left: touching |
| Move objects | drag selected objects or **Modify > Move** |
| Grips | click a blue grip, then click the new position |
| Cancel command | Esc |
| End command | Enter or right click |
| Repeat last command | Space |
| Delete | Del |
| Undo / Redo | Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z), mouse back / forward button |
| Cut / Copy / Paste | Ctrl+X / Ctrl+C / Ctrl+V |
| Object snap / grid / ortho / grid snap / snap tracking | F3 / F7 / F8 / F9 / F11 |

Modify commands without a selection first ask for objects: select them and press Enter.

**Choosing snap modes:** rest on the **OSNAP** button at the bottom or click its small arrow, or **Shift+right click** on the drawing. **Perpendicular** snaps the right-angle point from the last point, e.g. a wire straight onto the bus bar.

**Right click on a point** (no command running): **Connect** places a connection dot, **Separate** suppresses an automatic dot (shown on screen as an orange ring, not printed), **Remove point** deletes a bend or corner of a wire or polyline, **Extend** continues drawing at an end.

**Object snap tracking:** during a command, rest the cursor on a snap point (e.g. a connection point) until a green + appears. Moving horizontally or vertically away from it shows a dotted alignment line and the point snaps onto it, on the grid. Two acquired points give the intersection of their alignments.

**Typed coordinates:** during a drawing command just start typing; input goes to the **Command** line: `120,45` absolute, `@25,0` relative to the last point, `30` length towards the cursor (ortho only). With a decimal comma separate the values with a semicolon: `12,5;7,5`.

### Blocks, libraries and DXF import

- **Block > Create block** (Ctrl+B): select objects (or select them when asked and press Enter), name the block; the block editor opens right away to add connection points and attributes (the base point jumps to the first connection point until you set it yourself), and **Save and close** creates the block. Untick the editor option in the dialog to just click a base point instead. **Block > Edit block** (block editor with yellow bar), **Modify > Explode**.
- **Define attribute** and **Place connection point** create placeholders and terminals, best in the block editor.
- When a block is moved, rotated or mirrored, wire ends on its connection points follow.
- **Block > Save to user library** stores the block in `~/.local/share/sldgridy/library/eigene.sldglib`; libraries can be imported and exported.
- Right-click a symbol in the library dock to open it in the block editor (changes to user library symbols are written back to the library file when you save), to edit its name, category and description or to delete it. This works for blocks of the drawing (undoable; renaming updates all references, deleting only unused blocks) and for user libraries. Shipped libraries are read only.
- **Block > Import symbols from DXF** reads ASCII DXF files: each named block becomes a symbol; lines, polylines (with arcs), circles, arcs, ellipses, texts and attributes (ATTDEF) are taken over, nested blocks are resolved, **POINT** objects become connection points, units are converted to mm. The symbols are stored as a library named after the DXF file.

### Sheets, printing and export

- Tabs at the bottom: model and sheets (new, rename, duplicate, delete, format, templates via right click).
- Formats A4 to A0, portrait and landscape, frame to DIN EN ISO 5457, title block to DIN EN ISO 7200 (180 mm; the block “Schriftfeld” can be changed in the block editor).
- Double-click into a viewport activates it: the wheel zooms, the middle button pans, Esc ends. Scale, position of the area's top left corner in the model (X/Y, button “Top left to 0,0”), lock and “Fit model extents” in the Properties dock.
- Printing **1:1** (A0 on the plotter), **fit to paper** (e.g. A0 on A3) or **tiles** (1:1 on smaller sheets with 10 mm overlap, cut marks and tile numbers); quick print of the model; black and white; printable layers only.
- Vector PDF with exact sheet size and one page per sheet, SVG in mm, PNG with selectable resolution.

### Files and locations

| What | Where |
|---|---|
| Drawing | `*.sldg` (JSON, versioned; saving keeps `*.sldg.bak`) |
| Library | `*.sldglib`; shipped in `/usr/share/sldgridy/library/`, own ones in `~/.local/share/sldgridy/library/` |
| Frame template | `*.sldgframe`; shipped in `/usr/share/sldgridy/templates/`, own ones in `~/.local/share/sldgridy/templates/` |
| Automatic backup | every 5 minutes to `~/.cache/sldgridy/`; after a crash the next start offers recovery |
| Settings | `~/.config/sldgridy/sldgridy.conf` |

### Development

```bash
sudo apt install python3-venv python3-pyqt6 python3-pyqt6.qtsvg lintian
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/python -m sldgridy                     # run
QT_QPA_PLATFORM=offscreen .venv/bin/pytest       # tests without a display
.venv/bin/ruff check . && .venv/bin/ruff format --check .
./packaging/build-deb.sh                         # builds dist/sldgridy_<version>_all.deb
lintian dist/sldgridy_*.deb
```

German is the source language of the user interface; English translations live in `src/sldgridy/resources/i18n/en.json` (a test checks that every text is translated). The specification and all design decisions are in `CLAUDE.md` (German).

### Feedback and support

- Bugs and ideas: [issues](https://github.com/Glenn-Dandy/SLDGridy/issues) (in the program: Help > Report a bug, prefilled with version details)
- Like SLDGridy? Give the project a ⭐ on GitHub.
- [♥ Support the project](https://paypal.me/GlennDandy)

### Notice

SLDGridy is an independent project. It is not affiliated with or endorsed by DIN, IEC, VDE, Autodesk, EPLAN or the LibreCAD project. DIN is a registered trademark of DIN Deutsches Institut für Normung e.V.; AutoCAD and DXF are trademarks of Autodesk, Inc. The symbols were drawn for this project following the standards mentioned; the standards themselves are not included.

### License

GPL-3.0-or-later, see [LICENSE](LICENSE). © Glenn-Dandy

---

## Deutsch

Einpolige Übersichtsschaltpläne (Single-Line-Diagramme) für Photovoltaikanlagen, Transformatorstationen und Niederspannungsverteilungen unter Linux, gezeichnet wie in einem CAD-Programm: maßhaltig in Millimetern, mit Modell und Zeichnungsrahmen, Raster und Objektfang, Ebenen, Blöcken mit Attributen und Anschlusspunkten, einer Symbolbibliothek nach DIN EN 60617 und Drucken bis A0.

Die Oberfläche gibt es auf **Deutsch und Englisch** (Ansicht > Sprache / Language).

Lizenz: GPL-3.0-or-later. Zielsystem: Ubuntu 24.04 LTS und 26.04 LTS (X11 und Wayland).

### Installation

Das Paket `sldgridy_<version>_all.deb` aus den [Releases](https://github.com/Glenn-Dandy/SLDGridy/releases/latest) herunterladen und installieren:

```bash
sudo apt install ./sldgridy_<version>_all.deb
```

Danach steht „SLDGridy“ im Anwendungsmenü, und `.sldg`-Dateien öffnen sich per Doppelklick. Deinstallation mit `sudo apt remove sldgridy`.

### Kurzanleitung

1. Im Reiter **Modell** zeichnen. Der Nullpunkt ist mit einem Achsenkreuz markiert, 1 Einheit = 1 mm.
2. Symbole aus dem Dock **Bibliothek** (links) in die Zeichnung ziehen oder doppelklicken. Die mitgelieferte Bibliothek „Symbole nach DIN EN 60617“ enthält 42 Symbole für PV, Trafostation und Niederspannung; eine zweite Bibliothek „Weitere Symbole“ enthält übliche Symbole ohne Norm-Schaltzeichen (selektive Hauptschalter netzunabhängig/netzabhängig, PV-Modul, DC-Solarspeicher, Wallbox AC-gekoppelt, Internet-Wolke). Nach dem Einfügen fragt das Programm die Attribute `BMK`, `TYP` und `WERT` ab; PV-Modul, Wechselrichter, Wallbox und DC-Solarspeicher zusätzlich `HERSTELLER`. Umschalt+Enter in einem Wert beginnt eine neue Zeile, die Attribute darunter rutschen nach unten.
3. Mit **Zeichnen > Leitung** (Strg+W) Anschlusspunkte verbinden. Die Leitung rastet auf Anschlusspunkte (magentafarbene Marker) und knickt automatisch rechtwinklig. **Sammelschiene** zeichnet eine 0,7-mm-Schiene, an die überall angeschlossen werden kann. Verbindungspunkte entstehen automatisch.
4. Leitungen beschriften: Doppelklick auf die Leitung oder Eigenschaften-Dock, z. B. „NYY-J 5x16“; im Dock auch Lage, Position (automatisch, Anfang, Ende, frei), Ausrichtung (links, mitte, rechts) und Größe der Beschriftung. Eine ausgewählte beschriftete Leitung hat einen orangen Rautengriff an der Beschriftung: entlang der Leitung ziehen, um sie auf einen beliebigen Abschnitt zu setzen. Hohle Quadratgriffe in der Mitte jedes Abschnitts verschieben nur diesen Abschnitt, die Leitungsenden bleiben angeschlossen. Griffe lassen sich ziehen (drücken, ziehen, loslassen) oder anklicken und mit einem zweiten Klick absetzen; der Griff unter der Maus wird rot.
- Rechtsklick auf ein Leitungsende am Rand eines Blocks: „Andockpunkt hier setzen“ macht die Stelle zum Anschlusspunkt dieses einen Blocks, die Leitung folgt dann beim Verschieben.
- Leitungen, die an einer anderen Leitung oder Sammelschiene hängen (T-Abzweig oder Ende an Ende), wandern mit, wenn diese verschoben, gedreht oder umgeformt wird; per Rechtsklick „Trennen“ getrennte Stellen bleiben stehen. Das setzt sich fort: Ein verschobener Block zieht seine Leitung, die Leitung ihre Abzweige.
- Rechtsklick in einen Leitungsabschnitt: „Punkt hinzufügen“ teilt ihn, jeder Teil bekommt seinen eigenen Abschnittsgriff und lässt sich einzeln versetzen.
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
| Rückgängig / Wiederholen | Strg+Z / Strg+Y (oder Strg+Umschalt+Z), Maustaste zurück / vor |
| Ausschneiden / Kopieren / Einfügen | Strg+X / Strg+C / Strg+V |
| Objektfang / Raster / Ortho / Rasterfang / Objektfangspur | F3 / F7 / F8 / F9 / F11 |

Ändern-Befehle ohne Auswahl fragen zuerst nach Objekten: wählen und mit Enter bestätigen.

**Objektfang wählen:** am Knopf **OFANG** unten kurz verweilen oder den kleinen Pfeil anklicken, oder **Umschalt+Rechtsklick** auf der Zeichenfläche. Der **Lotfußpunkt** fängt den rechtwinkligen Punkt vom letzten Punkt aus, z. B. eine Leitung senkrecht auf die Sammelschiene.

**Rechtsklick auf einen Punkt** (ohne laufenden Befehl): **Verbinden** setzt einen Verbindungspunkt, **Trennen** unterdrückt einen automatischen Punkt (am Bildschirm als oranger Ring sichtbar, nicht im Druck), **Punkt entfernen** löscht einen Knick oder Eckpunkt einer Leitung oder Polylinie, **Verlängern** zeichnet an einem Ende weiter.

**Objektfangspur (Hilfslinien):** Während eines Befehls den Cursor kurz auf einem Fangpunkt (z. B. Anschlusspunkt) ruhen lassen, bis ein grünes + erscheint. Bewegt man sich danach waagerecht oder senkrecht davon weg, zeigt eine gepunktete Linie die Flucht, und der Punkt rastet darauf ein, im Raster. Zwei vorgemerkte Punkte ergeben den Kreuzungspunkt ihrer Fluchten.

**Koordinaten eingeben:** Während eines Zeichenbefehls einfach lostippen, die Eingabe landet in der Zeile **Befehl**: `120,45` absolut, `@25,0` relativ zum letzten Punkt, `30` Länge in Cursorrichtung (nur bei Ortho). Mit Dezimalkomma die Werte mit Semikolon trennen: `12,5;7,5`.

### Ebenen und Eigenschaften

Im Dock **Ebenen**: Name, Farbe, Linienbreite (ISO 128: 0,18 bis 0,7 mm), Linienart, sichtbar, gesperrt, druckbar. Doppelklick setzt die aktuelle Ebene. Das Dock **Eigenschaften** ändert Ebene, Farbe, Breite, Linienart, Text, Blockattribute, Leitungsbeschriftung und Ansichtsfenster der Auswahl.

### Blöcke, Bibliotheken und DXF-Import

- **Block > Block erstellen** (Strg+B): Objekte auswählen (oder auf Nachfrage auswählen und Enter drücken), Namen vergeben; danach öffnet sich gleich der Blockeditor für Anschlusspunkte und Attribute (der Basispunkt springt auf den ersten Anschlusspunkt, bis du ihn selbst setzt), **Speichern und schließen** legt den Block an. Ohne den Haken für den Blockeditor im Dialog wird stattdessen nur der Basispunkt geklickt.
- **Block > Attribut definieren** und **Anschlusspunkt setzen** legen Platzhalter und Anschlüsse an, am besten im Blockeditor.
- **Block > Block bearbeiten** öffnet den Blockeditor mit gelber Leiste. „Speichern und schließen“ aktualisiert alle Referenzen.
- **Ändern > Auflösen** ersetzt eine Referenz durch ihre Einzelobjekte.
- **Block > In Benutzerbibliothek speichern** legt den Block in `~/.local/share/sldgridy/library/eigene.sldglib` ab. Bibliotheken lassen sich importieren und exportieren.
- Rechtsklick auf ein Symbol im Bibliotheks-Dock: im Blockeditor öffnen (Symbole der Benutzerbibliothek werden beim Speichern zurück in die Bibliotheksdatei geschrieben), Name, Kategorie und Beschreibung bearbeiten oder löschen. Das geht für Blöcke der Zeichnung (rückgängig machbar; Umbenennen ändert alle Referenzen mit, gelöscht werden nur unbenutzte Blöcke) und für Benutzerbibliotheken. Mitgelieferte Bibliotheken sind schreibgeschützt.
- Wird ein Block verschoben, gedreht oder gespiegelt, wandern die Leitungsenden auf seinen Anschlusspunkten mit.
- **Block > Symbole aus DXF importieren** liest ASCII-DXF-Dateien (z. B. Herstellersymbole oder Exporte aus AutoCAD, EPLAN, LibreCAD): Jeder benannte Block wird ein Symbol; Linien, Polylinien (auch mit Bögen), Kreise, Bögen, Ellipsen, Texte und Attribute (ATTDEF) werden übernommen, verschachtelte Blöcke aufgelöst, **POINT**-Objekte werden zu Anschlusspunkten, die Einheit wird in mm umgerechnet. Die Symbole landen als eigene Bibliothek mit dem Namen der DXF-Datei.

### Zeichnungsrahmen

- Reiter unten: Modell und Blätter. Rechtsklick auf einen Reiter bietet Neu, Umbenennen, Duplizieren, Löschen, Format und Vorlagen. Reiter lassen sich verschieben.
- Formate A4 bis A0, hoch und quer, Rahmen nach DIN EN ISO 5457, Schriftfeld nach DIN EN ISO 7200 (180 mm). Das Schriftfeld ist der Block „Schriftfeld“ und kann im Blockeditor angepasst werden.
- Doppelklick in ein Ansichtsfenster aktiviert es: Mausrad zoomt, mittlere Taste verschiebt den Ausschnitt, Esc beendet. Maßstab (1:1, 2:1, 1:2, 1:5, 1:10 oder frei), Lage der linken oberen Ecke des Ausschnitts im Modell (X/Y, Knopf „Links oben auf 0,0“), Sperre und „Modellgrenzen einpassen“ im Eigenschaften-Dock.
- Im Modell zeigen gestrichelte Umrisse, was auf welches Blatt passt (**Blatt > Blattumrisse im Modell**).
- **Blatt > Als Vorlage speichern** legt eigene Rahmen in `~/.local/share/sldgridy/templates/` ab.

### Drucken und Export

- **1:1**: Blattformat gleich Papierformat (A0 auf dem Plotter). Ist das Format am Drucker nicht verfügbar, ist 1:1 gesperrt.
- **Einpassen**: Blatt auf das gewählte Papier skaliert (z. B. A0 auf A3).
- **Kacheln**: 1:1 auf kleinere Bögen mit 10 mm Überlappung, Schnittmarken und Kachelnummer `Z1/S2`.
- Im Reiter Modell gibt es zusätzlich den Schnelldruck, der die Modellgrenzen auf das Papier einpasst.
- Optionen: Schwarz-weiß, nur druckbare Ebenen. Die Vorschau warnt, wenn der Drucker nicht bis in den Rahmen drucken kann.
- PDF als Vektor mit exakter Blattgröße und einer Seite je Blatt, SVG in mm, PNG mit wählbarer Auflösung.

### Dateien und Speicherorte

| Was | Wo |
|---|---|
| Zeichnung | `*.sldg` (JSON, versioniert; beim Speichern bleibt `*.sldg.bak`) |
| Bibliothek | `*.sldglib`; mitgeliefert in `/usr/share/sldgridy/library/`, eigene in `~/.local/share/sldgridy/library/` |
| Rahmenvorlage | `*.sldgframe`; mitgeliefert in `/usr/share/sldgridy/templates/`, eigene in `~/.local/share/sldgridy/templates/` |
| Automatische Sicherung | alle 5 Minuten nach `~/.cache/sldgridy/`; nach einem Absturz bietet der nächste Start die Wiederherstellung an |
| Einstellungen | `~/.config/sldgridy/sldgridy.conf` |

### Entwicklung

Befehle wie im englischen Teil unter *Development*. Deutsch ist die Quellsprache der Oberfläche, die englischen Texte stehen in `src/sldgridy/resources/i18n/en.json` (ein Test prüft, dass jeder Text übersetzt ist). Die Spezifikation und alle Festlegungen stehen in `CLAUDE.md`.

### Feedback und Unterstützung

- Fehler und Wünsche: [Issues](https://github.com/Glenn-Dandy/SLDGridy/issues) (im Programm unter Hilfe > Fehler melden, mit Versionsangaben vorausgefüllt)
- Gefällt dir SLDGridy? Gib dem Projekt einen ⭐ auf GitHub.
- [♥ Projekt unterstützen](https://paypal.me/GlennDandy)

### Hinweis

SLDGridy ist ein unabhängiges Projekt und steht in keiner Verbindung zu DIN, IEC, VDE, Autodesk, EPLAN oder dem LibreCAD-Projekt. DIN ist eine eingetragene Marke des DIN Deutsches Institut für Normung e.V.; AutoCAD und DXF sind Marken der Autodesk, Inc. Die Symbole wurden für dieses Projekt nach den genannten Normen gezeichnet; die Normen selbst sind nicht enthalten.

### Lizenz

GPL-3.0-or-later, siehe [LICENSE](LICENSE). © Glenn-Dandy
