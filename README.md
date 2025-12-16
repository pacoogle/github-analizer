# GitHub Analytics Tools

Raccolta di script Python per analizzare attività su GitHub, inclusi Pull Request e Issues.

## Script Disponibili

### 1. `pr_analytics.py` - Analisi Pull Request

Script per analizzare le Pull Request mergiate di un autore specifico in un'organizzazione GitHub, distinguendo tra PR approvate senza bocciature e PR bocciate e poi approvate.

### 2. `bug_analytics.py` - Analisi Bug e Non-Bug

Script per ottenere il numero di "bug" e "non-bug" aperti e risolti su GitHub per un'organizzazione in un determinato periodo di tempo.

---

## `pr_analytics.py` - Descrizione

Questo script utilizza l'API di GitHub per:
- Cercare tutte le PR mergiate di un autore specifico in un'organizzazione
- Analizzare le review di ciascuna PR
- Classificare le PR in due categorie:
  - **PR approvate senza bocciature**: PR che sono state approvate senza mai ricevere una review con stato `CHANGES_REQUESTED`
  - **PR bocciate e poi approvate**: PR che hanno ricevuto almeno una review con stato `CHANGES_REQUESTED` prima di essere approvate

## Prerequisiti

- Python 3.x
- Un token di accesso personale GitHub con i permessi necessari per leggere le informazioni dell'organizzazione

## Installazione

1. Clona o scarica questo repository
2. Installa le dipendenze richieste:

```bash
pip install -r requirements.txt
```

Oppure installa manualmente:

```bash
pip install requests click rich
```

## Configurazione

Prima di utilizzare lo script, devi configurare un token di accesso GitHub:

1. Crea un [Personal Access Token](https://github.com/settings/tokens) su GitHub con i permessi necessari per leggere le informazioni dell'organizzazione
2. Imposta la variabile d'ambiente `GITHUB_TOKEN`:

```bash
export GITHUB_TOKEN=tuo_token_personale
```

Per rendere la variabile permanente, aggiungi la riga al tuo file `~/.zshrc` o `~/.bashrc`.

**Alternativa**: Puoi passare il token direttamente come parametro CLI con `--token`.

---

## `bug_analytics.py` - Descrizione

Questo script utilizza l'API di GitHub per:
- Cercare tutte le issues (non Pull Request) create in un'organizzazione nel periodo specificato
- Classificare le issues come "bug" (se hanno la label `bug`) o "non-bug" (se non hanno la label `bug`)
- Contare le issues aperte e risolte nel periodo specificato
- Fornire statistiche aggregate per bug e non-bug

### Classificazione Bug/Non-Bug

Le issues sono classificate come:
- **Bug**: Issues che hanno la label `bug` su GitHub
- **Non-Bug**: Issues che non hanno la label `bug` (tutte le altre issues)

### Stati delle Issues

- **Aperte**: Issues create nel periodo specificato che risultano ancora aperte
- **Risolte**: Issues chiuse nel periodo specificato (indipendentemente da quando sono state create)

---

## Utilizzo

### `pr_analytics.py`

Esegui lo script con i seguenti parametri obbligatori:

```bash
python pr_analytics.py --org ORGANIZZAZIONE --author AUTORE --from-date YYYY-MM-DD --to-date YYYY-MM-DD
```

### Parametri Obbligatori

- `--org`: Nome dell'organizzazione GitHub (es. `Gamindo`)
- `--author`: Username GitHub dell'autore delle PR (es. `pacoogle`)
- `--from-date`: Data di inizio del periodo da analizzare (formato: `YYYY-MM-DD`)
- `--to-date`: Data di fine del periodo da analizzare (formato: `YYYY-MM-DD`)

### Opzioni Opzionali

- `--token`: Token GitHub (alternativa a `GITHUB_TOKEN` env var)
- `--output`: Formato di output (`table`, `json`, `csv`) - default: `table`
- `--export`: File di esportazione per JSON/CSV (es. `results.json`, `results.csv`)
- `--verbose` / `-v`: Mostra informazioni dettagliate durante l'esecuzione
- `--no-details`: Non mostrare il dettaglio delle singole PR (solo statistiche)

### Esempi

**Esempio base con output tabella:**
```bash
python pr_analytics.py --org Gamindo --author pacoogle --from-date 2024-01-01 --to-date 2024-12-31
```

**Esempio con output JSON:**
```bash
python pr_analytics.py --org Gamindo --author pacoogle --from-date 2024-01-01 --to-date 2024-12-31 --output json
```

**Esempio con esportazione CSV:**
```bash
python pr_analytics.py --org Gamindo --author pacoogle --from-date 2024-01-01 --to-date 2024-12-31 --output csv --export risultati.csv
```

**Esempio con modalità verbose:**
```bash
python pr_analytics.py --org Gamindo --author pacoogle --from-date 2024-01-01 --to-date 2024-12-31 --verbose
```

**Esempio senza dettagli (solo statistiche):**
```bash
python pr_analytics.py --org Gamindo --author pacoogle --from-date 2024-01-01 --to-date 2024-12-31 --no-details
```

**Esempio con token passato come parametro:**
```bash
python pr_analytics.py --org Gamindo --author pacoogle --from-date 2024-01-01 --to-date 2024-12-31 --token ghp_tuo_token_qui
```

## Output

Lo script supporta tre formati di output:

### Output Tabella (default)

Mostra una tabella formattata con:
- Statistiche riassuntive (numero di PR per categoria)
- Dettaglio delle PR divise per categoria (se `--no-details` non è specificato)
- Formattazione colorata e leggibile grazie a Rich

### Output JSON

Formato strutturato JSON con tutte le informazioni:
- Lista completa delle PR con dettagli (numero, titolo, URL, repository, data merge)
- Statistiche aggregate

### Output CSV

File CSV esportabile con colonne:
- Categoria
- Numero PR
- Titolo
- Repository
- URL
- Data Merge

## Funzionalità CLI

La CLI moderna include:

- ✅ **Validazione automatica delle date** - Verifica che le date siano nel formato corretto
- ✅ **Progress bar** - Indicatori di avanzamento durante l'elaborazione (con `--verbose`)
- ✅ **Gestione errori migliorata** - Messaggi di errore chiari e informativi
- ✅ **Output formattato** - Tabelle colorate e leggibili con Rich
- ✅ **Export multipli** - Supporto per JSON e CSV
- ✅ **Verbosity configurabile** - Controllo dettaglio output
- ✅ **Help integrato** - `python pr_analytics.py --help` per vedere tutte le opzioni

### `bug_analytics.py`

Esegui lo script con i seguenti parametri obbligatori:

```bash
python bug_analytics.py --org ORGANIZZAZIONE --from-date YYYY-MM-DD --to-date YYYY-MM-DD
```

#### Parametri Obbligatori

- `--org`: Nome dell'organizzazione GitHub (es. `Gamindo`)
- `--from-date`: Data di inizio del periodo da analizzare (formato: `YYYY-MM-DD`)
- `--to-date`: Data di fine del periodo da analizzare (formato: `YYYY-MM-DD`)

#### Opzioni Opzionali

- `--token`: Token GitHub (alternativa a `GITHUB_TOKEN` env var)
- `--output`: Formato di output (`table`, `json`, `csv`) - default: `table`
- `--export`: File di esportazione per JSON/CSV (es. `bug_results.json`, `bug_results.csv`)
- `--verbose` / `-v`: Mostra informazioni dettagliate durante l'esecuzione
- `--no-details`: Non mostrare il dettaglio delle singole issues (solo statistiche)

#### Esempi

**Esempio base con output tabella:**
```bash
python bug_analytics.py --org Gamindo --from-date 2024-01-01 --to-date 2024-12-31
```

**Esempio con output JSON:**
```bash
python bug_analytics.py --org Gamindo --from-date 2024-01-01 --to-date 2024-12-31 --output json
```

**Esempio con esportazione CSV:**
```bash
python bug_analytics.py --org Gamindo --from-date 2024-01-01 --to-date 2024-12-31 --output csv --export bug_risultati.csv
```

**Esempio con modalità verbose:**
```bash
python bug_analytics.py --org Gamindo --from-date 2024-01-01 --to-date 2024-12-31 --verbose
```

**Esempio senza dettagli (solo statistiche):**
```bash
python bug_analytics.py --org Gamindo --from-date 2024-01-01 --to-date 2024-12-31 --no-details
```

---

## Output

### `pr_analytics.py` Output

Lo script supporta tre formati di output:

#### Output Tabella (default)

Mostra una tabella formattata con:
- Statistiche riassuntive (numero di PR per categoria)
- Dettaglio delle PR divise per categoria (se `--no-details` non è specificato)
- Formattazione colorata e leggibile grazie a Rich

#### Output JSON

Formato strutturato JSON con tutte le informazioni:
- Lista completa delle PR con dettagli (numero, titolo, URL, repository, data merge)
- Statistiche aggregate

#### Output CSV

File CSV esportabile con colonne:
- Categoria
- Numero PR
- Titolo
- Repository
- URL
- Data Merge

### `bug_analytics.py` Output

Lo script supporta tre formati di output:

#### Output Tabella (default)

Mostra una tabella formattata con:
- Statistiche riassuntive per Bug e Non-Bug
- Colonne separate per "Aperti" e "Risolti"
- Dettaglio delle issues divise per categoria e stato (se `--no-details` non è specificato)
- Formattazione colorata e leggibile grazie a Rich

#### Output JSON

Formato strutturato JSON con tutte le informazioni:
- Lista completa delle issues con dettagli (numero, titolo, URL, repository, stato, date, labels)
- Statistiche aggregate per bug e non-bug
- Informazioni sul periodo analizzato

#### Output CSV

File CSV esportabile con colonne:
- Tipo (Bug/Non-Bug)
- Stato (Aperto/Risolto)
- Numero Issue
- Titolo
- Repository
- URL
- Data Creazione
- Data Chiusura
- Labels

---

## Note

- Entrambi gli script utilizzano la GitHub Search API che ha limiti di rate limiting
- Le date devono essere nel formato `YYYY-MM-DD`
- `pr_analytics.py` analizza solo le PR che sono state effettivamente mergiate nel periodo specificato
- `bug_analytics.py` classifica le issues come bug se hanno la label `bug` su GitHub. Assicurati che le issues siano etichettate correttamente nell'organizzazione
- `bug_analytics.py` conta le issues aperte create nel periodo e le issues chiuse nel periodo (indipendentemente da quando sono state create)

