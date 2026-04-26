# Release-Prozess

Dieses Dokument beschreibt, wie ein neues Release von `pazufa-corelib` erstellt und auf PyPI veröffentlicht wird.

---

## Voraussetzungen

- Schreibrechte auf das Repository
- Die Woodpecker-Secrets `pypi_token` und `testpypi_token` sind in den Repo-Einstellungen konfiguriert
- Alle CI-Checks auf `main` sind grün

---

## Release erstellen

### 1. Version in `pyproject.toml` aktualisieren

```toml
version = "0.2.0"
```

### 2. CHANGELOG.md ergänzen

Neuen Abschnitt für die Version anlegen und Änderungen dokumentieren.

### 3. Commit und Merge

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: prepare release 0.2.0"
```

PR erstellen, Review abwarten, in `main` mergen.

### 4. Tag setzen

Das Tag-Format bestimmt das Veröffentlichungsziel:

| Tag-Format        | Ziel      | Beispiel       |
|-------------------|-----------|----------------|
| `vX.Y.Z`         | PyPI      | `v0.2.0`       |
| `vX.Y.Z-rcN`     | TestPyPI  | `v0.2.0-rc1`   |

```bash
git tag v0.2.0
git push origin v0.2.0
```

Woodpecker startet automatisch die Publish-Pipeline.

---

## TestPyPI-Release

Ein TestPyPI-Release eignet sich, um die Veröffentlichung vorab zu prüfen, ohne das offizielle Paket zu beeinflussen.

```bash
git tag v0.2.0-rc1
git push origin v0.2.0-rc1
```

Das Paket ist anschliessend unter
`https://test.pypi.org/project/pazufa-corelib/` einsehbar.

Installation aus TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ pazufa-corelib
```

---

## Pipeline-Ablauf

Die Publish-Pipeline (`.woodpecker/publish.yml`) wird nur bei Tag-Push ausgelöst und besteht aus drei Schritten:

| Schritt             | Aufgabe                                       |
|---------------------|-----------------------------------------------|
| `build`             | `poetry build` — erzeugt Wheel und Sdist      |
| `check`             | `twine check dist/*` — validiert die Metadaten |
| `publish-testpypi`  | Upload auf TestPyPI (nur bei `-rc`-Tags)      |
| `publish-pypi`      | Upload auf PyPI (nur bei sauberen Semver-Tags) |

Die Schritte `publish-testpypi` und `publish-pypi` schliessen sich gegenseitig aus — pro Tag wird nur eines der beiden ausgeführt.

---

## Secrets einrichten

Beide Tokens werden in den Woodpecker-Repo-Einstellungen als Secrets hinterlegt:

| Secret-Name       | Quelle                                        |
|--------------------|-----------------------------------------------|
| `pypi_token`       | https://pypi.org/manage/account/token/        |
| `testpypi_token`   | https://test.pypi.org/manage/account/token/   |

Tokens werden mit dem Benutzernamen `__token__` verwendet (PyPI-Token-Authentifizierung).

---

## Fehlerbehebung

### `twine check` schlägt fehl

Die README wird nicht korrekt als reStructuredText oder Markdown erkannt. Sicherstellen, dass `readme = "README.md"` in `pyproject.toml` gesetzt ist.

### Upload schlägt fehl mit „403 Forbidden"

- Token abgelaufen oder falsch — in den Woodpecker-Secrets prüfen
- Paketname bereits von einem anderen Projekt belegt — auf PyPI prüfen

### Version existiert bereits

PyPI erlaubt kein erneutes Hochladen derselben Version. Die Versionsnummer in `pyproject.toml` muss erhöht werden.