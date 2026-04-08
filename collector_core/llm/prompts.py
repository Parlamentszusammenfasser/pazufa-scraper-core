"""German-language prompt templates for LLM enrichment.

Each constant is a str.format() template. Use the documented format variables.
Ported from the BB scraper and generalized for all Landtage.
"""

from .sachgebiete_taxonomy import SACHGEBIETE_NAMES

KURZTITEL_PROMPT = """\
Erstelle einen kurzen, verständlichen Titel (5-10 Wörter) für den folgenden \
parlamentarischen Vorgang. Der Kurztitel soll das Thema des Vorgangs auf einen \
Blick erfassbar machen — ohne juristische Formalsprache, ohne "Gesetz zur...", \
ohne Artikelverweise.

Beispiele guter Kurztitel:
- "Stärkung der Kinderrechte in der Landesverfassung"
- "Anhebung der Grunderwerbsteuer"
- "Digitalisierung der Schulverwaltung"

Titel: {titel}
Abstract: {abstract}"""
"""Format vars: ``titel``, ``abstract``."""

ZUSAMMENFASSUNG_PROMPT = """\
Du bist ein parlamentarischer Analyst. Fasse das folgende parlamentarische \
Dokument zusammen. Schreibe einen kompakten Fließtext in sachlicher, \
allgemeinverständlicher Sprache — vermeide juristische Fachsprache wo möglich.

Gehe auf folgende Aspekte ein, sofern sie im Text erkennbar sind:
- Ziel: Was will der Entwurf / Antrag erreichen? Welches Problem wird adressiert?
- Wesentliche Maßnahmen: Was wird konkret geregelt oder geändert?
- Geänderte Vorschriften: Welche Gesetze oder Artikel werden geändert, \
aufgehoben oder ergänzt? Nenne die konkreten Bezeichnungen.
- Kosten: Entstehen Kosten für den Landeshaushalt oder die Kommunen?
- Inkrafttreten: Wann soll die Regelung in Kraft treten?
- Hintergrund: Gibt es einen genannten Anlass oder Kontext?

Lasse Aspekte weg, zu denen der Text keine Angaben macht — erfinde nichts. \
Verwende keine Zwischenüberschriften, sondern einen zusammenhängenden Text.

Titel: {titel}

Text:
{text}"""
"""Format vars: ``titel``, ``text``."""

SCHLAGWORTE_PROMPT = """\
Du bist ein parlamentarischer Analyst. Klassifiziere dieses Dokument \
thematisch bezüglich des genannten Vorgangs.

AUFGABE 1 — SACHGEBIETE:
Wähle aus der folgenden Liste alle Sachgebiete, die auf dieses Dokument \
zutreffen. Verwende die Bezeichnungen EXAKT wie angegeben (mit Großschreibung).

{sachgebiete_list}

AUFGABE 2 — ZUSÄTZLICHE SCHLAGWORTE:
Extrahiere 3-7 zusätzliche Schlagworte für spezifische Themen, die nicht \
durch die Sachgebiete abgedeckt sind. Schlagworte immer in Kleinbuchstaben \
(z.B. "bildungspolitik", "mindestlohn").

REGELN:
- Nur Themen, die sich auf den genannten Vorgang beziehen
- Was passiert an dieser Station? Welche Aspekte werden behandelt?
- Bei Gesetzentwürfen: Welche Regelungsbereiche werden adressiert?
- Bei Ausschussprotokollen: Was wurde konkret diskutiert oder beschlossen?
- Bei Plenarprotokollen: Welche Aspekte wurden in der Debatte betont? \
Ignoriere andere Tagesordnungspunkte.
- Wenn der Vorgang im Text nicht auffindbar ist: leere Listen zurückgeben

Vorgang: {vorgang_titel} ({vorgang_vnr})
Dokumenttyp: {dok_typ}
Titel: {titel}

Text (Auszug):
{text}"""
"""Format vars: ``sachgebiete_list``, ``vorgang_titel``, ``vorgang_vnr``,
``dok_typ``, ``titel``, ``text``."""

MEINUNG_PROMPT = """\
Du bist ein parlamentarischer Analyst. Bewerte das Meinungsbild des folgenden \
Dokuments auf einer Skala von 1 bis 5.

SKALA:
1 = ABLEHNUNG — Das Dokument lehnt den Vorgang grundsätzlich ab oder empfiehlt \
die Ablehnung. Fundamentale Kritik, keine Zustimmung erkennbar.
2 = ÜBERWIEGEND KRITISCH — Das Dokument äußert erhebliche Bedenken oder fordert \
wesentliche Änderungen. Der Grundtenor ist ablehnend, auch wenn einzelne Aspekte \
positiv bewertet werden.
3 = GEMISCHT / NEUTRAL — Das Dokument wägt Vor- und Nachteile ab, ohne eine \
klare Richtung. Oder: Das Dokument ist sachlich-neutral ohne erkennbare Wertung.
4 = ÜBERWIEGEND ZUSTIMMEND — Das Dokument unterstützt den Vorgang im Grundsatz, \
nennt aber kleinere Änderungswünsche oder Vorbehalte.
5 = ZUSTIMMUNG — Das Dokument befürwortet den Vorgang ausdrücklich oder empfiehlt \
die Annahme. Positiver Grundtenor ohne wesentliche Einschränkungen.

WICHTIG:
- Bewerte nur das Meinungsbild des Dokuments selbst, nicht den zugrundeliegenden \
Gesetzentwurf.
- Bei Beschlussempfehlungen: Was empfiehlt der Ausschuss dem Plenum?
- Bei Stellungnahmen: Wie steht der Verfasser zum Vorgang?
- Wenn das Dokument keine erkennbare Meinung enthält (z.B. rein beschreibend), \
wähle 3.

Dokumenttyp: {dok_typ}
Titel: {titel}

Text (Auszug):
{text}"""
"""Format vars: ``dok_typ``, ``titel``, ``text``."""

VERFASSUNGSAENDERND_PROMPT = """\
Du bist ein juristischer Analyst für den Landtag {land}.

Bestimme, ob der folgende Gesetzentwurf die **Verfassung des Landes {land}** \
(Landesverfassung) ändert.

ENTSCHEIDUNGSREGEL:
→ ist_verfassungsaendernd=true NUR wenn der Gesetzentwurf explizit einen oder \
mehrere **Artikel der Verfassung des Landes {land}** ändert, aufhebt oder \
ergänzt. Der Text muss konkret auf Artikel der Landesverfassung Bezug nehmen \
(z.B. "Artikel 22 der Verfassung wird wie folgt geändert").

→ ist_verfassungsaendernd=false in ALLEN anderen Fällen, insbesondere:
- **Kommunalverfassung** — Das ist ein einfaches Landesgesetz, KEINE Verfassung. \
Änderungen an der Kommunalverfassung sind NICHT verfassungsändernd, auch wenn \
"Verfassung" im Namen steht.
- **Grundgesetz** — Ein Landtag kann das Grundgesetz nicht ändern.
- **Andere Gesetze mit "Verfassung" oder "verfassungsrechtlich" im Namen** — \
z.B. "kommunalverfassungsrechtliche Vorschriften" sind einfache Gesetze.

Titel: {titel}
Schlagworte: {schlagworte}

Text (Auszug):
{text}"""
"""Format vars: ``land``, ``titel``, ``schlagworte``, ``text``."""


EXPERTEN_PROMPT = """\
Du bist ein parlamentarischer Analyst. Extrahiere aus dem folgenden Dokument \
alle Personen und Organisationen, die das Dokument verfasst oder eingereicht haben.

AUFGABE:
Identifiziere die Autor(en) oder einreichende(n) Partei(en) dieses Dokuments — \
also wer das Dokument erstellt oder offiziell eingereicht hat. \
Gib nur Personen/Organisationen an, die direkt als Verfasser oder Einreicher \
des Dokuments erkennbar sind. Personen, die lediglich im Text erwähnt werden \
(z.B. zitierte Politiker, referenzierte Gesetzesverfasser), sind NICHT aufzunehmen.

FELDER:
- person: Name der Person falls genannt (z.B. "Prof. Dr. Susanne Meyer"), sonst null
- organisation: Organisation oder Kontext (Pflichtfeld; bei Einzelpersonen z.B. \
"Sachverständiger" oder "Privatperson")
- fachgebiet: Fachgebiet/Expertise falls erkennbar, sonst null
- lobbyregister: Lobbyregister-URL oder -Nummer falls im Dokument angegeben, sonst null

REGELN:
- Halluziniere keine Informationen
- Wenn ein Feld nicht erkennbar ist: null
- Wenn keine Autoren erkennbar sind: eine Organisation "Unbekannt" zurückgeben

Dokumenttyp: {dok_typ}
Titel: {titel}

Text (Auszug):
{text}"""
"""Format vars: ``dok_typ``, ``titel``, ``text``."""


EXPERTEN_PROMPT_NO_LOBBYREGISTER = """\
Du bist ein parlamentarischer Analyst. Extrahiere aus dem folgenden Dokument \
alle Personen und Organisationen, die das Dokument verfasst oder eingereicht haben.

AUFGABE:
Identifiziere die Autor(en) oder einreichende(n) Partei(en) dieses Dokuments — \
also wer das Dokument erstellt oder offiziell eingereicht hat. \
Gib nur Personen/Organisationen an, die direkt als Verfasser oder Einreicher \
des Dokuments erkennbar sind. Personen, die lediglich im Text erwähnt werden \
(z.B. zitierte Politiker, referenzierte Gesetzesverfasser), sind NICHT aufzunehmen.

FELDER:
- person: Name der Person falls genannt (z.B. "Prof. Dr. Susanne Meyer"), sonst null
- organisation: Organisation oder Kontext (Pflichtfeld; bei Einzelpersonen z.B. \
"Sachverständiger" oder "Privatperson")
- fachgebiet: Fachgebiet/Expertise falls erkennbar, sonst null

REGELN:
- Halluziniere keine Informationen
- Wenn ein Feld nicht erkennbar ist: null
- Wenn keine Autoren erkennbar sind: eine Organisation "Unbekannt" zurückgeben
- Lobbyregister-Informationen NICHT ausfüllen oder erfassen — auch nicht wenn sie \
im Text vorkommen

Dokumenttyp: {dok_typ}
Titel: {titel}

Text (Auszug):
{text}"""
"""Format vars: ``dok_typ``, ``titel``, ``text``.

Use this prompt with ExtractedExpertNoLobbyregister to prevent hallucination
of lobby register entries in scrapers where the register is not applicable."""


SECTION_EXTRACTION_PROMPT = """\
Du bist ein parlamentarischer Analyst. Deine Aufgabe ist es, in einem \
Textabschnitt eines Parlamentsprotokolls die Zeilen zu identifizieren, \
die sich auf einen bestimmten Vorgang beziehen.

VORGANG: {vorgang_titel}{vorgang_vnr_part}

AUFGABE:
- Jede Zeile im Text ist mit einer Zeilennummer in eckigen Klammern \
markiert, z.B. [42].
- Gib die Zeilennummern der relevanten Abschnitte als start/end-Bereiche an.
- Ein Bereich umfasst alle Zeilen von start bis end (inklusive).

ENTSCHEIDUNG — RELEVANT ODER NICHT:
Prüfe, ob der Vorgang im Text behandelt wird. Der Titel kann über \
mehrere Zeilen umbrochen sein — das ist normal. Entscheidend ist, dass \
der Vorgang inhaltlich gemeint ist, nicht ob der Titel zeichengenau \
in einer einzelnen Zeile steht.
- "Gesetz zur Änderung des Spielbankgesetzes" ist NICHT dasselbe wie \
"Gesetz zur Änderung der Verfassung" — achte auf den spezifischen \
Regelungsgegenstand.
- Wenn der Vorgang im Text nicht behandelt wird, \
setze is_relevant=false und relevant_lines=[].

GRENZEN EINES TAGESORDNUNGSPUNKTS:
- Beginn: "TOP X:" oder "Tagesordnungspunkt X" mit dem Vorgang
- Ende: "Ich schließe Tagesordnungspunkt X", "Ich rufe \
Tagesordnungspunkt Y auf", oder der nächste "TOP Y:" — \
was zuerst kommt.
- NACH der Schließung eines TOP ist NICHTS mehr relevant, \
auch wenn es direkt anschließt.

CHECKLISTE VOR DER ANTWORT:
1. Kommt der Vorgang namentlich oder per Drucksachennummer im Text vor?
   Nein → is_relevant=false, relevant_lines=[]
2. Welche Zeilen gehören zum TOP des Vorgangs (zwischen Beginn und Ende)?
3. Gibt es eine Erwähnung in der Tagesordnung/Inhaltsverzeichnis?
4. Sind ALLE angegebenen Zeilennummern tatsächlich im Text vorhanden?

- Gib die Zeilennummern EXAKT so an, wie sie im Text stehen. \
Erfinde keine Zeilennummern.

TEXT:
{text}"""
"""Format vars: ``vorgang_titel``, ``vorgang_vnr_part``, ``text``.

``vorgang_vnr_part`` should be either ``" (Drucksache X/Y)"`` or ``""``."""


def format_sachgebiete_list() -> str:
    """Format the taxonomy as a bulleted list for prompt formatting."""
    return "\n".join(f"- {name}" for name in SACHGEBIETE_NAMES)
