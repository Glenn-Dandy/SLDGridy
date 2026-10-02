# CLAUDE.md: SLDGridy

Programmname „SLDGridy“, Paket- und Modulname `sldgridy`. Bei einer Umbenennung überall konsistent ändern (Modul, Paket, Desktop-Datei, MIME-Typ, Dateiendungen, Pfade).

## Was gebaut wird

Ein Desktop-Programm für Linux zum Zeichnen einpoliger Übersichtsschaltpläne (Single-Line-Diagramme, SLD) mit CAD-typischer Bedienung: maßhaltiges Zeichnen in Millimetern, getrennte Bereiche für Modell und Zeichnungsrahmen, Raster und Objektfang, Ebenen, wiederverwendbare Blöcke, Drucken und Plotten bis A0. Ausgeliefert wird ein installierbares `.deb`.

Schwerpunkt sind SLDs für Photovoltaikanlagen (PV-Generator, Wechselrichter, Speicher, NA-Schutz, Netzanschluss) und Transformatorstationen (Mittelspannungsschaltanlage, Transformator, Niederspannungsverteilung) sowie allgemeine Niederspannungsverteilungen.

Nicht im Umfang: allgemeines 2D-CAD (Bemaßung, Schraffur, Splines), Stromlaufpläne mit Querverweisen, elektrische Berechnung oder Prüfung, 3D.

## Technik (festgelegt)

- Python ≥ 3.12
- PyQt6 aus den Distributionspaketen: QtWidgets (QGraphicsView), QtPrintSupport, QtSvg
- Zur Laufzeit keine pip-Abhängigkeiten. Neue Abhängigkeiten nur nach Rückfrage.
- Entwicklung: pytest, ruff
- Lizenz: GPL-3.0-or-later (folgt aus PyQt6)
- Zielsystem: Ubuntu 24.04 LTS, X11 und Wayland. Entwickelt und getestet wird nur dagegen.

## Grundregeln

Diese Regeln gelten für jeden Meilenstein und werden nicht aufgeweicht.

1. **Einheit ist Millimeter.** In Modell und Zeichnungsrahmen gilt 1 Szeneneinheit = 1 mm, Y zeigt nach unten. Im Zeichnungsrahmen ist der Ursprung die linke obere Blattecke, im Modell ein frei liegender Nullpunkt.
2. **Modell ohne Qt.** `sldgridy/model/` importiert nichts aus PyQt6. Geometrie, Blöcke, Serialisierung und Kachelberechnung sind reines Python und ohne Display testbar.
3. **Jede Dokumentänderung ist ein Undo-Kommando** (`QUndoCommand` auf einem `QUndoStack`). Kein Werkzeug und kein Dialog verändert das Modell direkt.
4. **Linienbreiten sind echte Millimeter** (ISO 128: 0,18 / 0,25 / 0,35 / 0,5 / 0,7), keine kosmetischen Stifte. Am Bildschirm wird mindestens 1 Pixel breit gezeichnet.
5. **Hilfsdarstellung wird nie ausgegeben.** Raster, Fangmarker, Auswahlgriffe, Anschlusspunkt-Marker und die Blattumrisse im Modell erscheinen weder im Druck noch im Export.
6. **Sprache:** Oberfläche Deutsch, alle Texte über `tr()`. Code, Bezeichner, Kommentare und Commits Englisch.
7. **Dateiformat ist versioniert.** Ältere Dateiversionen bleiben über Migrationsfunktionen ladbar.

## Projektstruktur

```
sldgridy/
├── CLAUDE.md
├── pyproject.toml
├── src/sldgridy/
│   ├── __init__.py          # __version__ (einzige Versionsquelle)
│   ├── __main__.py
│   ├── model/               # Document, ModelSpace, SheetLayout, Viewport, Layer, Entities, BlockDefinition, BlockReference, Wire
│   ├── fileio/              # JSON laden/speichern, Migration, Bibliotheksdateien
│   ├── view/                # QGraphicsScene/-Items, Canvas, Raster, Fang
│   ├── tools/               # Zeichen- und Bearbeitungswerkzeuge als Zustandsautomaten
│   ├── commands/            # QUndoCommand-Klassen
│   ├── ui/                  # Hauptfenster, Docks (Ebenen, Blöcke, Eigenschaften), Dialoge
│   ├── printing/            # Drucken, Vorschau, Kacheln, PDF/SVG/PNG
│   └── resources/           # Icons, mitgelieferte Symbolbibliothek, Rahmenvorlagen
├── tests/
└── packaging/
    ├── build-deb.sh
    ├── sldgridy.sh          # Startskript für /usr/bin/sldgridy
    ├── sldgridy.1           # Manpage
    ├── copyright            # DEP-5, landet in /usr/share/doc/sldgridy/
    ├── sldgridy.desktop
    ├── sldgridy.xml         # MIME-Typ
    └── sldgridy.svg         # Programmsymbol
```

## Funktionsumfang

### Modell und Zeichnungsrahmen

Die Zeichnung besteht aus zwei getrennten Bereichen, umschaltbar über Reiter am unteren Rand der Zeichenfläche. Nicht mit Ebenen (Layern) verwechseln: Ebenen gelten in beiden Bereichen.

**Modell**

- Unbegrenzte Zeichenfläche ohne Blatt. Hier entsteht der Schaltplan; Blöcke, Leitungen und Sammelschienen werden hier gezeichnet.
- Der Nullpunkt ist mit einem Achsenkreuz markiert.
- Zur Orientierung wird für jedes Ansichtsfenster der zugehörige Ausschnitt als dünner Umriss mit dem Namen des Zeichnungsrahmens eingeblendet (abschaltbar). So ist beim Zeichnen sichtbar, was auf das Blatt passt.

**Zeichnungsrahmen**

- Ein Blatt mit Format, Rahmen, Schriftfeld und einem oder mehreren Ansichtsfenstern auf das Modell.
- Eine Zeichnung kann mehrere Zeichnungsrahmen haben (Blatt 1, Blatt 2, …). Reiter lassen sich anlegen, umbenennen, duplizieren, sortieren und löschen.
- Formate A4 bis A0, hoch und quer. **Standard: A0 quer (1189 × 841 mm).** Eine neue Zeichnung enthält das Modell und einen Zeichnungsrahmen A0 quer.
- Rahmen nach DIN EN ISO 5457: Rand links 20 mm, sonst 10 mm.
- Schriftfeld nach DIN EN ISO 7200 unten rechts, 180 mm breit. Technisch ein Block mit Attributen, damit ein eigenes Schriftfeld im Blockeditor gestaltet werden kann. Felder: Projekt, Titel, Zeichnungsnummer, Datum, Bearbeiter, Geprüft, Blatt x von y, Firma, Änderungsindex.
- Projekt, Firma und Bearbeiter gelten für die ganze Zeichnung, die übrigen Felder je Blatt. „Blatt x von y“ ergibt sich aus der Reihenfolge der Reiter.
- Im Zeichnungsrahmen kann mit den normalen Zeichenwerkzeugen gearbeitet werden (Texte, Linien, Legende, Firmenangaben). Diese Objekte gehören zum Blatt, nicht zum Modell.
- Rahmenvorlagen: Ein Zeichnungsrahmen ohne Ansichtsinhalt (Format, Rahmen, Schriftfeld, Blattobjekte) lässt sich als Vorlage speichern und für neue Blätter verwenden. Benutzervorlagen liegen in `~/.local/share/sldgridy/templates/`; mitgeliefert werden Normrahmen A4 bis A0.
- Ein Formatwechsel behält Blattobjekte und Ansichtsfenster bei und warnt, wenn etwas außerhalb des Blatts liegt.

**Ansichtsfenster**

- Rechteck auf dem Blatt, das einen Ausschnitt des Modells zeigt. Eigenschaften: Lage und Größe auf dem Blatt, Modellpunkt in der Mitte, Maßstab, gesperrt, Rahmen drucken ja/nein (Standard nein).
- Maßstab: 1:1 als Standard, feste Stufen 2:1 / 1:2 / 1:5 / 1:10, freier Wert und „Modellgrenzen einpassen“.
- Ein neuer Zeichnungsrahmen erhält ein Ansichtsfenster, das die Zeichenfläche innerhalb des Rahmens füllt; das Schriftfeld liegt deckend darüber.
- Doppelklick in ein Ansichtsfenster aktiviert es, dann lässt sich der Ausschnitt verschieben und zoomen. Modellobjekte werden dort nicht bearbeitet, das geschieht nur im Reiter „Modell“.
- Linienbreiten und Texthöhen skalieren mit dem Maßstab des Ansichtsfensters. Bei 1:1 entsprechen sie den eingestellten Millimetern.

### Zeichnen

- Elemente: Linie, Polylinie, Rechteck, Kreis, Bogen, Text (einzeilig und mehrzeilig, Höhen 2,5 / 3,5 / 5 / 7 mm), Leitung, Sammelschiene.
- Raster (Standard 5 mm) und Rasterfang (Standard 2,5 mm), beides einstellbar und abschaltbar.
- Objektfang: Endpunkt, Mittelpunkt, Schnittpunkt, Zentrum, Anschlusspunkt. Anschlusspunkte haben Vorrang, sonst gewinnt der nächste Punkt (bei Gleichstand Endpunkt vor Schnittpunkt vor Mittelpunkt vor Zentrum). Fangradius 10 px, F3 schaltet um, aktive Fangarten unter Ansicht einstellbar. Objektfang hat Vorrang vor Rasterfang und Ortho.
- Ortho-Modus (nur waagerecht/senkrecht), umschaltbar.
- Koordinateneingabe über eine Eingabezeile unter der Zeichenfläche: absolut `x,y`, relativ `@dx,dy` (Bezug: Basispunkt des Befehls, sonst letzter Punkt), Länge bei aktivem Ortho in Richtung des Cursors. Dezimalpunkt; mit Dezimalkomma die Koordinaten mit `;` trennen (`10,5;20`). Ein Komma ohne `;` trennt immer x und y. Ziffern, `@`, `-`, `.`, `,`, `;` auf der Zeichenfläche springen direkt in die Eingabezeile. Leere Eingabe wirkt wie Enter.
- Statusleiste zeigt Cursorposition in mm, Zoom, aktive Ebene, Fang- und Ortho-Zustand.
- Bedienung: Esc bricht ab, Enter oder Rechtsklick beendet, Leertaste wiederholt den letzten Befehl (bei laufendem Befehl wirkt sie wie Enter). Mausrad zoomt auf den Cursor, mittlere Taste verschiebt.
- Tasten: F7 Raster, F8 Ortho, F9 Rasterfang, Pos1 Grenzen zoomen, Entf löscht die Auswahl. Raster, Fang und Ortho sind auch als Knöpfe in der Statusleiste umschaltbar und werden in `QSettings` gemerkt.
- Werkzeugablauf: Linie zeichnet fortlaufend Einzelsegmente; Polylinie schließt beim Klick auf den Startpunkt; Kreis über Mittelpunkt und Umfangspunkt; Bogen über Mittelpunkt, Start- und Endpunkt gegen den Uhrzeigersinn; Text über Einfügepunkt und Dialog, Doppelklick auf einen Text bearbeitet ihn.

### Bearbeiten

- Auswahl per Klick, Fenster (links nach rechts: vollständig innen) und Kreuzen (rechts nach links: berührt). Umschalt+Klick fügt hinzu oder entfernt, Klick ins Leere hebt die Auswahl auf.
- Verschieben, Kopieren (mehrfach bis Enter), Drehen in 90°-Schritten (Richtung per Maus, gegen den Uhrzeigersinn positiv), Spiegeln, Löschen, Ausschneiden/Einfügen, Griffe an Endpunkten.
- Ausgewählte Objekte lassen sich direkt mit der Maus ziehen (Verschieben mit Fang). Ein Klick auf einen Griff startet das Ziehen des Griffs, der nächste Klick setzt ihn. Kreis und Text haben nur einen Griff, der das Objekt verschiebt; Rechteckecken halten die gegenüberliegende Ecke fest; Bogenenden ändern nur den Winkel.
- Ändern-Befehle ohne Auswahl fragen zuerst nach Objekten (wählen, Enter bestätigt).
- Spiegeln ersetzt die Objekte (kein Original bleibt stehen) an einer waagerechten oder senkrechten Achse. Texte behalten ihre Leserichtung.
- Zwischenablage: eigener MIME-Typ `application/x-sldgridy-entities`, Basispunkt ist die linke untere Ecke der Auswahl. Einfügen setzt mit Klick, unbekannte Ebenen werden zu `0`.
- Eigenschaften-Dock für Ebene, Farbe, Linienbreite, Linienart (durchgezogen, gestrichelt, strichpunktiert), Text und Blockattribute.
- Unbegrenztes Rückgängig/Wiederholen.

### Ebenen

- Name, Farbe, Linienbreite, Linienart, sichtbar, gesperrt, druckbar.
- Objekte erben standardmäßig von der Ebene („VonEbene“), Einzelwerte können abweichen.
- Ebene `0` existiert immer und kann nicht gelöscht oder umbenannt werden. Eine Ebene mit Objekten oder die aktuelle Ebene lässt sich nicht löschen. Umbenennen zieht die Objekte mit.
- Die aktuelle Ebene ist Fensterzustand, nicht Dokumentinhalt (wird nicht gespeichert, nach dem Öffnen ist `0` aktuell).
- Unsichtbare Ebenen werden nicht angezeigt, gesperrte lassen sich nicht auswählen; Objektfang wirkt auf gesperrte Ebenen weiter.
- Linienarten nach ISO 128-20 in Vielfachen der Linienbreite d: gestrichelt 12d/3d, strichpunktiert 24d/3d/0,5d/3d.

### Leitungen und Sammelschienen

- Leitung: orthogonaler Linienzug als eigener Objekttyp, fängt auf Anschlusspunkte.
- Endet eine Leitung auf einer anderen Leitung, entsteht automatisch ein Verbindungspunkt. Kreuzungen ohne Punkt sind nicht verbunden.
- Liegt ein Leitungsende auf einem Anschlusspunkt, wandert es beim Verschieben des Blocks mit. Mehr Automatik (Autorouting) gibt es nicht.
- Sammelschiene: breite Linie (Standard 0,7 mm), an beliebiger Stelle anschließbar.
- Leitungen können eine Beschriftung tragen (z. B. Kabeltyp und Querschnitt), die mit der Leitung verschoben wird.

### Blöcke

Kernfunktion. Ein Block ist eine benannte Definition, die beliebig oft als Referenz eingefügt wird.

- **Definition:** eindeutiger Name, Basispunkt, Geometrie in lokalen Koordinaten, Anschlusspunkte (Name, Position, Richtung), Attributdefinitionen (Kennung, Abfragetext, Vorgabewert, Position, Texthöhe, sichtbar ja/nein).
- **Referenz:** Blockname, Einfügepunkt, Drehung 0/90/180/270°, Spiegelung, Attributwerte. Keine Skalierung.
- **Erstellen:** „Block aus Auswahl“ mit Dialog für Name und gepicktem Basispunkt; die Auswahl wird auf Wunsch durch eine Referenz ersetzt.
- **Blockeditor:** Definition isoliert bearbeiten, dort Anschlusspunkte und Attribute setzen. Beim Schließen aktualisieren sich alle Referenzen.
- **Verschachtelung** ist erlaubt, Zirkelbezüge werden abgelehnt.
- **Auflösen** ersetzt eine Referenz durch ihre Einzelobjekte.
- **Attributtexte** bleiben bei gedrehten Blöcken lesbar (nie auf dem Kopf).
- **Bibliothek:** Dock mit Vorschaubildern, Suche und Drag-and-drop in die Zeichnung. Quellen sind die mitgelieferte Bibliothek (`/usr/share/sldgridy/library/`, schreibgeschützt) und die Benutzerbibliothek (`~/.local/share/sldgridy/library/`). Blöcke lassen sich aus der Zeichnung in die Benutzerbibliothek speichern, Bibliotheksdateien importieren und exportieren.
- Beim Einfügen aus der Bibliothek wird die Definition in das Dokument kopiert, damit jede Zeichnungsdatei für sich allein vollständig ist. Bei Namensgleichheit mit abweichendem Inhalt fragen: Dokumentversion behalten, ersetzen oder umbenennen.

### Mitgelieferte Symbolbibliothek

Symbole nach DIN EN 60617 im 2,5-mm-Raster, jeweils mit Anschlusspunkten und den Attributen `BMK` (Betriebsmittelkennzeichen), `TYP` und `WERT`:

- Schalten und Schützen: Leitungsschutzschalter, Schmelzsicherung, NH-Sicherungslasttrenner, Lasttrennschalter, Leistungsschalter, Schütz, Fehlerstromschutzschalter, Überspannungsableiter
- Netz und Messung: Netzanschluss, Hausanschlusskasten, Zähler (Bezug, Lieferung, Zweirichtung), Stromwandler, Spannungswandler, Transformator
- Mittelspannung und Transformatorstation: MS-Leistungsschalter, MS-Lasttrennschalter, Trennschalter, Erdungsschalter, HH-Sicherung, Kabelendverschluss, Schutzrelais, Kurzschlussanzeiger, Ortsnetz- bzw. Kundentransformator (Dreieck/Stern mit Schaltgruppe als Attribut)
- Erzeugung und Speicher: PV-Generator, PV-String, Generatoranschlusskasten, DC-Freischalter, Wechselrichter, Batteriespeicher, Generator, NA-Schutz, Kuppelschalter
- Verbraucher und Sonstiges: Motor, allgemeiner Verbraucher, Ladeeinrichtung, Wärmepumpe, Erdung, Potentialausgleichsschiene

Die Symbole werden als Bibliotheksdatei im eigenen Format gepflegt, nicht im Code erzeugt.

### Drucken und Export

- Gedruckt wird der Zeichnungsrahmen: der aktuelle, eine Auswahl oder alle. Aus dem Modell heraus gibt es zusätzlich einen Schnelldruck, der die Modellgrenzen auf das gewählte Papier einpasst.
- Druckdialog über Qt/CUPS mit drei Modi:
  - **1:1**: Blattformat entspricht dem Papierformat (A0 auf dem Plotter).
  - **Einpassen**: Blatt wird auf das gewählte Papier skaliert (A0 auf A3 oder A4), Linienbreiten skalieren mit.
  - **Kacheln**: 1:1 auf mehrere kleinere Bögen verteilt, mit 10 mm Überlappung, Schnittmarken und Kachelnummer (Zeile/Spalte) im Rand.
- Druckvorschau für alle drei Modi.
- Optionen: Schwarz-weiß (alle Farben werden schwarz), nur druckbare Ebenen.
- Ganzseitig ohne Druckerränder rechnen (`QPageLayout` im Full-Page-Modus), damit der Blattrahmen maßhaltig sitzt. Schneidet der nicht bedruckbare Bereich des Geräts in den Rahmen, in der Vorschau warnen.
- Bietet der Drucker A0 nicht an, 1:1 deaktivieren und Einpassen oder Kacheln vorschlagen.
- **PDF-Export** als Vektor mit exakter Blattgröße; Text bleibt Text. Mehrere Zeichnungsrahmen ergeben ein mehrseitiges PDF.
- SVG-Export, PNG-Export mit wählbarer Auflösung.

### Dateiformat

- Koordinaten: Winkel in Grad gegen den Uhrzeigersinn am Bildschirm, 0° zeigt nach +X. Text: Einfügepunkt ist das linke Ende der ersten Grundlinie, die Texthöhe ist die Versalhöhe, Zeilenabstand 1,6 × Texthöhe.
- Zeichnung: `.sldg`, JSON in UTF-8, mit `format_version`. Enthält Ebenen, alle verwendeten Blockdefinitionen, die Objekte des Modells sowie alle Zeichnungsrahmen mit Format, Schriftfeldwerten, Blattobjekten und Ansichtsfenstern.
- Bibliothek: `.sldglib`, JSON mit einer Liste von Blockdefinitionen.
- Rahmenvorlage: `.sldgframe`, JSON mit einem Zeichnungsrahmen ohne Ansichtsinhalt.
- Speichern atomar: in eine temporäre Datei schreiben, dann umbenennen. Vor dem Überschreiben eine `.bak` behalten (`name.sldg.bak`).
- Automatische Sicherung alle 5 Minuten nach `~/.cache/sldgridy/`, beim Start Wiederherstellung anbieten.
- Fenster- und Programmeinstellungen über `QSettings`.

## Befehle

Einmalig einrichten (Befehle mit `sudo` nicht selbst ausführen, sondern dem Benutzer nennen):

```bash
sudo apt install python3-venv python3-pyqt6 python3-pyqt6.qtsvg lintian
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev]"
```

Das venv nutzt bewusst das PyQt6 des Systems, damit Entwicklung und installiertes Paket dieselbe Version verwenden.

```bash
.venv/bin/python -m sldgridy                     # starten
QT_QPA_PLATFORM=offscreen .venv/bin/pytest       # Tests ohne Display
.venv/bin/ruff check . && .venv/bin/ruff format --check .
./packaging/build-deb.sh                         # erzeugt dist/sldgridy_<version>_all.deb
lintian dist/sldgridy_*.deb
sudo apt install ./dist/sldgridy_*_all.deb       # Installationstest
```

## Debian-Paket

`packaging/build-deb.sh` baut einen Staging-Baum und ruft `dpkg-deb --build --root-owner-group` auf. Die Version kommt aus `sldgridy/__init__.py`.

| Ziel im Paket | Inhalt |
|---|---|
| `/usr/share/sldgridy/sldgridy/` | Python-Modul |
| `/usr/share/sldgridy/library/` | mitgelieferte Symbolbibliothek |
| `/usr/share/sldgridy/templates/` | mitgelieferte Rahmenvorlagen |
| `/usr/bin/sldgridy` | Startskript, setzt den Modulpfad und ruft `main()` auf |
| `/usr/share/applications/sldgridy.desktop` | Menüeintrag, `MimeType=application/x-sldgridy` |
| `/usr/share/mime/packages/sldgridy.xml` | MIME-Typ für `*.sldg` |
| `/usr/share/icons/hicolor/scalable/apps/sldgridy.svg` | Programmsymbol |
| `/usr/share/doc/sldgridy/copyright` | Lizenz |
| `/usr/share/doc/sldgridy/changelog.gz` | wird von `build-deb.sh` erzeugt |
| `/usr/share/man/man1/sldgridy.1.gz` | Manpage |

`DEBIAN/control`:

```
Package: sldgridy
Architecture: all
Section: graphics
Priority: optional
Depends: python3 (>= 3.12), python3-pyqt6, python3-pyqt6.qtsvg
```

- Vor dem Eintragen der Abhängigkeiten unter Ubuntu 24.04 prüfen, welche Pakete die benötigten Qt-Module wirklich liefern (`dpkg -S`, `apt-cache show`).
- Der MIME-Eintrag (`sldgridy.xml`, `MimeType=` in der Desktop-Datei) kommt erst in M8; die Desktop-Datei und das Symbol sind seit M1 enthalten.
- Kein `postinst` nötig: Desktop- und MIME-Datenbank werden über dpkg-Trigger aktualisiert.
- Abnahme: `lintian` ohne Fehler, Installation und Deinstallation sauber, Programm startet aus dem Menü, Doppelklick auf eine `.sldg` öffnet sie.

## Meilensteine

Immer nur einen Meilenstein bearbeiten. Der deb-Build wird in M1 angelegt und bleibt danach in jedem Meilenstein lauffähig. Das Dokumentmodell kennt von Anfang an Modell und Zeichnungsrahmen, auch wenn die Oberfläche dafür erst in M6 entsteht.

1. **Grundgerüst:** Projektstruktur, Hauptfenster, Modellbereich mit Zoom/Pan, Raster und Nullpunkt, Statusleiste, `build-deb.sh` mit installierbarem Paket.
2. **Zeichnen und Speichern:** Grundelemente, Rasterfang, Ortho, Auswahl, Verschieben/Kopieren/Drehen/Löschen, Undo/Redo, Laden und Speichern.
3. **Ebenen und Eigenschaften:** Ebenen-Dock, Eigenschaften-Dock, Linienbreiten und -arten, Objektfang, Koordinateneingabe.
4. **Blöcke:** Definition, Referenz, Block aus Auswahl, Blockeditor, Attribute, Auflösen, Bibliotheks-Dock mit Benutzerbibliothek.
5. **Leitungen und Symbole:** Anschlusspunkte, Leitung, Sammelschiene, Verbindungspunkte, Mitziehen, mitgelieferte Symbolbibliothek (PV, Transformatorstation, Niederspannung).
6. **Zeichnungsrahmen:** Reiter für Modell und Zeichnungsrahmen, Formate, Rahmen, Schriftfeld, Ansichtsfenster mit Maßstab, Blattobjekte, Rahmenvorlagen, Blattumrisse im Modell.
7. **Drucken und Export:** 1:1, Einpassen, Kacheln, Vorschau, PDF, SVG, PNG.
8. **Auslieferung:** Desktop-Integration, MIME-Typ, Icon, automatische Sicherung, lintian sauber, Kurzanleitung in `README.md`.

## Tests

- Modell: Roundtrip speichern/laden für jeden Objekttyp, Migration alter Formatversionen, Blockoperationen (erstellen, verschachteln, Zirkelbezug, auflösen), Transformationen von Referenzen und Anschlusspunkten.
- Fang- und Geometriefunktionen mit festen Zahlenbeispielen.
- Ansichtsfenster: Umrechnung Modell ↔ Blatt für verschiedene Maßstäbe und Ausschnitte, Einpassen der Modellgrenzen.
- Kachelberechnung: Anzahl und Lage der Kacheln für A0 auf A4 und A3 mit Überlappung.
- PDF-Export offscreen: die erzeugte Seite muss für A0 quer 1189 × 841 mm groß sein (MediaBox prüfen); zwei Zeichnungsrahmen ergeben zwei Seiten.
- Jedes Undo-Kommando: ausführen, rückgängig, wiederholen ergibt wieder denselben Modellzustand.

## Arbeitsweise

- Vor jedem Meilenstein kurz den Plan nennen, danach umsetzen.
- Ein Meilenstein ist erst fertig, wenn Tests und `ruff` grün sind und das deb baut.
- Pro Meilenstein mindestens ein Commit mit aussagekräftiger englischer Nachricht.
- Was sich nicht automatisch prüfen lässt (Bedienung, Druckbild auf Papier), als kurze Prüfliste für den Benutzer ausgeben.
- Bei Unklarheiten im Funktionsumfang nachfragen statt raten. Nichts bauen, was hier nicht steht.
- Diese Datei aktuell halten, wenn sich Struktur, Befehle oder Entscheidungen ändern.
