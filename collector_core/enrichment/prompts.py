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


def format_sachgebiete_list() -> str:
    """Format the taxonomy as a bulleted list for prompt formatting."""
    return "\n".join(f"- {name}" for name in SACHGEBIETE_NAMES)
