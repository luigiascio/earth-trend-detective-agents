# Diario di lavoro

Registro cronologico di cosa è stato fatto, in ordine. Le **scelte** e i loro motivi vanno in
`decisioni.md`, lo **stato** dei lavori in `todo.md`: qui solo cosa è successo, in breve,
con il riferimento al commit quando c'è.

Formato: `### AAAA-MM-GG HH:MM` seguito da punti brevi.

## 2026-11-14 (sabato, giorno 1)

### Mattina: preparazione
- Riorganizzata la cartella del progetto: i file erano annidati in
  `earth-trend-detective/earth-trend-detective/`, spostati un livello più in alto; eliminato lo zip.
- Riportate le risorse ufficiali della sfida in `docs/dati.md`.
- Discussa la scelta della regione: Campania confermata, ma la risoluzione dei dati va verificata.

### Verifica di NASA POWER
- Scaricate le serie mensili 1981-2024 di temperatura (`T2M`) e precipitazione (`PRECTOTCORR`)
  per le 5 zone in `data/raw/power_monthly_<zona>.json`. Nessuna chiave richiesta; alcune
  richieste sono andate in timeout e sono riuscite al secondo tentativo.
- Risultato: 5 zone → **3 serie distinte** (Napoli = Caserta, Avellino = Benevento): la griglia
  MERRA-2 è troppo grossolana. Dettagli in `docs/dati.md`.
- Il mese `13` nel JSON è la media annuale: da scartare.

### Decisioni prese
- Gemini via Vertex AI (per allenarsi alla certificazione).
- Prima il Blocco 1 (dati e statistica), scritto passo passo insieme.
- Ambiente gestito con uv invece di pip.

### Passo 0: ambiente
- Installato uv con winget. Problema: il terminale di VS Code non vedeva `uv` perché era stato
  aperto prima dell'installazione (va riavviato VS Code, non solo il terminale).
- `uv init --bare` lanciato per errore nella cartella superiore: `pyproject.toml` spostato in
  `earth-trend-detective/` e rinominato il progetto.
- Creato questo diario.
- Aggiunte le dipendenze con `uv add` (numpy, pandas, scipy, requests, pydantic, matplotlib)
  e `uv add --dev` (pytest, pymannkendall). Ambiente verificato: Python 3.11.9,
  pandas 3.1.1, numpy 2.4.6. `pyproject.toml` e `uv.lock` su git. **Passo 0 completato.**

### Passo 1: lettore dei JSON di POWER
- Scelto il formato lungo (una riga per mese e variabile): colonne fisse, fonti con date
  diverse senza buchi artificiali, unità e fonte su ogni riga.
- Scritto `src/data/power.py`: `parse_power_monthly(payload, zone)` con l'helper
  `_parse_month_key` (idea dell'autore: separare anno e mese, scartare il mese 13).
  Il file era stato creato in `data/`, spostato in `src/data/`.
- Nota: in `geometry.coordinates` l'ordine è GeoJSON, cioè **longitudine prima**.
- Prova su Napoli: 1056 righe (528 mesi × 2 variabili), mese 13 scartato, nessun NaN,
  1981-01 → 2024-12.
