# Spezifikation: `normalise_volltext`

## Zweck

`normalise_volltext` bereinigt deutschen Volltext, der aus PDFs oder HTML-Quellen
extrahiert wurde. Die Funktion entfernt Artefakte aus fehlerhafter PDF-Textextraktion,
dekodiert HTML-Entitäten, normalisiert Zeichenkodierung und Whitespace und filtert
qualitativ minderwertige Absätze heraus.

---

## Signatur

```python
def normalise_volltext(text: str) -> str
```

**Eingabe:** Rohtext als `str`, aus einem PDF-Parser oder einer HTML-Quelle.
**Ausgabe:** Bereinigter `str`. Leerer String, wenn der Eingabetext leer ist oder
alle Absätze herausgefiltert werden.

---

## Verarbeitungsschritte

Die Schritte werden in dieser Reihenfolge angewendet.

### 1. HTML-Entitäten dekodieren

HTML-Entitäten werden mittels `html.unescape()` dekodiert:

- Benannte Entitäten: `&amp;` → `&`, `&uuml;` → `ü`, `&lt;` → `<`
- Numerische Entitäten: `&#160;` → U+00A0, `&#8203;` → U+200B

Dieser Schritt ist für reinen Plaintext (z. B. aus PDF-Parsern) ein No-op, da
Zeichenfolgen der Form `&name;` in deutschen Parlamentsdokumenten nicht natürlich
auftreten. Es gibt daher keine Seiteneffekte auf bestehende PDF-basierte Verarbeitung.

> **Hinweis:** Da `html.unescape()` vor der NFKC-Normalisierung läuft, werden
> dekodierte Unicode-Leerzeichen (z. B. U+00A0 aus `&nbsp;`) im nächsten Schritt
> automatisch zu normalen Leerzeichen.

### 2. NFKC-Unicode-Normalisierung

Alle Zeichen werden in die NFKC-Normalform überführt (`unicodedata.normalize("NFKC", …)`).

- Ligaturen werden aufgelöst (z. B. `ﬁ` → `fi`, `ﬀ` → `ff`)
- Hochgestellte Ziffern werden normalisiert (z. B. `m²` → `m2`)
- Vollbreite-Zeichen werden auf ASCII zurückgeführt (z. B. `Ａ` → `A`)
- Unicode-Leerzeichen (z. B. U+00A0 NBSP, U+202F schmales geschütztes Leerzeichen)
  werden zu normalen Leerzeichen

### 3. Unsichtbare Zeichen entfernen

Folgende Zeichen werden vollständig entfernt:

| Zeichen | Unicode | Bezeichnung |
|---------|---------|-------------|
| `­` | U+00AD | Weiches Trennzeichen (Soft Hyphen) |
| `​` | U+200B | Nullbreite-Leerzeichen (Zero-Width Space) |
| `‌` | U+200C | Nullbreite-Nicht-Verbinder (ZWNJ) |
| `‍` | U+200D | Nullbreite-Verbinder (ZWJ) |
| `﻿` | U+FEFF | Byte Order Mark (BOM) |

### 4. C1-Steuerzeichen entfernen

Alle Zeichen im Bereich U+0080–U+009F werden entfernt. Diese entstehen bei
fehlerhafter PDF-Fontverarbeitung durch einen ASCII+29-Zeichensatz-Shift.

### 5. Zeilenenden normalisieren

- `\r\n` (Windows CRLF) → `\n`
- `\r` (altes Mac CR) → `\n`

### 6. Silbentrennungs-Zeilenumbrüche zusammenführen

Wörter, die durch einen Trennstrich am Zeilenende aufgeteilt wurden, werden
wieder zusammengefügt.

**Muster:** `\w-\n\w`

**Beispiel:** `Landes-\nregierung` → `Landesregierung`

> **Hinweis:** Das Muster feuert nur, wenn auf beiden Seiten des Trennzeichens
> ein Wortzeichen steht. Absatzgrenzen (getrennt durch `\n\s*\n`) werden nicht
> überbrückt.

### 7. Mehrfaches Whitespace innerhalb einer Zeile zusammenführen

Aufeinanderfolgende Leerzeichen oder Tabulatoren (`[ \t]{2,}`) werden zu einem
einzelnen Leerzeichen reduziert. Zeilenumbrüche werden nicht verändert.

### 8. Absätze nach Qualitätsscore filtern

Der Text wird an Leerzeilen aufgeteilt (`\n\s*\n`). Jeder Absatz erhält einen
Qualitätsscore (0,0–1,0). Absätze mit einem Score unter **0,5** werden entfernt.

#### Scoring-Logik (`_paragraph_quality_score`)

Der Score berechnet sich als `1,0 − (Summe aller Strafwerte)`, abschließend
auf [0,0; 1,0] begrenzt. Jeder Strafwert ist individuell auf maximal 1,0
begrenzt.

| # | Signal | Berechnung |
|---|--------|------------|
| 1 | C1-Steuerzeichen-Anteil | Anzahl C1-Zeichen / Gesamtlänge |
| 2 | Latin-Extended-B-Anteil | Anzahl Zeichen U+0180–U+024F / Anzahl Buchstaben |
| 3 | Vokalloses-Wort-Verhältnis | Wörter ≥ 5 Zeichen ohne deutschen Vokal / Gesamtwortanzahl |
| 4 | Übermäßige Großschreibung | Skalierter Strafwert für Großbuchstabenanteile über 60 % |

**Ausnahme:** Absätze mit weniger als 4 Wörtern sind von Strafwert 4 (Großschreibung)
ausgenommen, um gültige Überschriften in Großbuchstaben (z. B. `EINLEITUNG`) nicht
zu entfernen.

**Deutsche Vokale** umfassen: `a e i o u ä ö ü` (groß und klein)

### 9. Spitze Klammern ersetzen

`<` wird durch `‹` (U+2039) und `>` durch `›` (U+203A) ersetzt, um
XSS-Angriffsvektoren zu neutralisieren.

> **Hinweis:** Da HTML-Tags in diesem Schritt **nicht** entfernt, sondern nur
> maskiert werden, eignet sich die Funktion nicht als vollständiger HTML-Stripper.
> Verbleibende Tags erscheinen im Ausgabetext als `‹tag›`.

---

## Rückgabewert

Der bereinigte Text als `str`. Führende und nachfolgende Leerzeichen werden
entfernt. Mehrere saubere Absätze werden durch `\n\n` getrennt.

---

## Beispiele

### HTML-Entität aus extrahiertem Text

```
Eingabe:  "Titel &amp; Inhalt &uuml;ber alles"
Ausgabe:  "Titel & Inhalt über alles"
```

### `&nbsp;` wird zu normalem Leerzeichen

```
Eingabe:  "Wort&nbsp;Wort"
Ausgabe:  "Wort Wort"
```

### Silbentrennungs-Zeilenumbruch

```
Eingabe:  "Die Landes-\nregierung hat beschlossen."
Ausgabe:  "Die Landesregierung hat beschlossen."
```

### Garbled-Absatz wird entfernt

```
Eingabe:  "Sauberer Absatz.\n\nĚĞƌ&ƌĂŬƚŝŽŶ ǁćŚƌůĞŝƐƚƵŶŐ ŝƚĞůůƚ"
Ausgabe:  "Sauberer Absatz."
```

### Spitze Klammern

```
Eingabe:  "<poststelle@lfdi.bwl.de>"
Ausgabe:  "‹poststelle@lfdi.bwl.de›"
```

---

## Nicht im Scope

- HTML-Tags werden **nicht** entfernt — sie werden lediglich durch Guillemets
  maskiert. Für vollständiges HTML-Stripping ist Vorverarbeitung außerhalb dieser
  Funktion erforderlich.
- Die Funktion führt keine inhaltliche Analyse oder Zusammenfassung durch.
- Rechtschreibfehler oder OCR-Fehler werden nicht korrigiert.
