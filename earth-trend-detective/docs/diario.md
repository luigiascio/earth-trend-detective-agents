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

### Passo 2: download con cache e nuovi tentativi
- Aggiunta `fetch_power_monthly(lat, lon, start_year, end_year, cache_file)` in
  `src/data/power.py`: legge dalla cache se il file esiste, altrimenti scarica con `requests`;
  ritenta solo su timeout ed errori di connessione (backoff 1, 2, 4 s), non sugli errori HTTP.
- Separata apposta da `parse_power_monthly`: il download fa I/O, il lettore resta puro e
  testabile senza internet.
- Prova: cache su Napoli in 0,00 s; download nuovo (40.25, 15.25, 2020-2024) in 4,9 s,
  120 righe; seconda chiamata servita dalla cache in 0,01 s.

### Passo 3: Mann-Kendall
- `src/stats/mann_kendall.py`: il calcolo di S (doppio ciclo sulle coppie) l'ha scritto
  l'autore; aggiunti varianza con correzione per i pareggi, Z con correzione di continuità,
  p-value bilaterale, tau di Kendall, gestione dei NaN e `InsufficientDataError` sotto
  10 osservazioni.
- Confronto con `pymannkendall.original_test` su 3 celle × 2 variabili × (medie annuali,
  serie mensile): S, varianza, Z e p-value **identici in tutti i 12 casi**. 50 ms per 528 mesi.
- **Scoperta importante:** la temperatura è fortemente significativa sulle medie annuali
  (z ≈ 5,5-5,8, p < 1e-7 in tutte le celle), ma sulla serie mensile grezza diventa debole o
  non significativa (Salerno p = 0,057, Avellino p = 0,055). Il ciclo delle stagioni copre il
  trend: confrontare gennaio con luglio non dice nulla sul riscaldamento. Motiva il passo 5
  (anomalie o Mann-Kendall stagionale).
- Precipitazioni: nessun trend significativo in nessuna cella, come previsto.

### Passo 3b: Theil-Sen
- `src/stats/theil_sen.py`: `pairwise_slopes` scritta dall'autore. Prima versione con
  `np.empty((n, n))`: le celle non riempite contenevano valori spazzatura che sarebbero finiti
  nella mediana. Corretta con una lista (`append`) e un controllo sulla lunghezza degli input.
- Aggiunti mediana delle pendenze, intercetta e intervallo di confidenza di Sen (1968), che
  riusa `mann_kendall_variance`. Tempi espliciti (anni) invece delle posizioni: la pendenza
  ha unità reali e gli anni mancanti sono gestiti.
- Confronto con `scipy.stats.theilslopes` su 3 celle × 2 variabili (medie annuali):
  pendenza, intercetta e intervallo **identici in tutti i casi**.
- Risultati (medie annuali 1981-2024): temperatura +0,35 °C/decennio a Napoli
  [0,26; 0,46], +0,29 a Salerno [0,20; 0,40], +0,36 ad Avellino [0,25; 0,48].
  Precipitazioni: tutti gli intervalli contengono lo zero.
- Aggiunta a `docs/statistica.md` una spiegazione semplice con un esempio di 6 anni fatto a mano
  (S, p-value con le "carte", pendenze, intervallo) e 5 regole di interpretazione.

### Passo 4: test automatici
- `tests/test_mann_kendall.py`, `tests/test_theil_sen.py`, `tests/test_power.py`: **39 test**,
  tutti passano in circa 3 s (`uv run pytest`). Configurazione pytest in `pyproject.toml`.
- Coprono: esempio fatto a mano, serie troppo corte, NaN, serie costanti, tasso di falsi
  positivi su rumore puro (< 10% con alpha 0,05), confronto con pymannkendall e scipy su serie
  con pareggi, resistenza agli outlier, schema del lettore, cache senza rete (`monkeypatch`).
- Un test è fallito al primo giro per una soglia scelta male nel test (non un bug del codice):
  con un outlier la regressione passa da 0,030 a 0,072, Theil-Sen da 0,0297 a 0,0317. Il test
  ora confronta gli spostamenti invece di usare un numero fisso.

### Passo 5: stagionalità
- Scelta la strada B: Mann-Kendall stagionale (vedi `decisioni.md`).
- Scritto `src/stats/seasonal.py`: `seasonal_mann_kendall` (S e varianza calcolati dentro ogni
  mese e sommati, riusando `mann_kendall_s` e `mann_kendall_variance`), `seasonal_sen_slope`
  (mediana delle pendenze tra stessi mesi, con intervallo di confidenza) e `trends_by_month`
  (Mann-Kendall e Theil-Sen per ogni singolo mese).
- Confronto con `pymannkendall.seasonal_test` e `seasonal_sens_slope` sui dati veri
  (3 celle × 2 variabili): **identici**.
- Corretto il calcolo del p-value in entrambi i moduli: `2 * (1 - norm.cdf(z))` dava **0,0** per
  Napoli (arrotondamento in virgola mobile); ora `2 * norm.sf(z)` dà 2,6·10⁻¹⁷.
- `tests/test_seasonal.py`: 18 test, **57 test in totale, tutti passano**. Un test è fallito al
  primo giro per parametri scelti male nel test; ora confronta z (stagionale 11,7 contro 2,1).
- Risultati, temperatura 1981-2024, test stagionale: Napoli +0,375 °C/decennio [0,30; 0,46],
  Salerno +0,32 [0,25; 0,40], Avellino +0,37 [0,28; 0,47], tutti p < 1e-14.
  Precipitazioni: nessun trend in nessuna cella.
- Per mese (Napoli): giugno, luglio, agosto e novembre circa +0,5 °C/decennio; gennaio +0,17
  con intervallo che contiene lo zero. Da non affermare prima della correzione per test multipli.

### Passo 6: grafico
- `src/viz/plots.py`: `plot_trend` disegna le medie annuali, la retta di trend (pendenza di Sen
  stagionale, passante per anno e valore mediani) e la fascia dell'intervallo al 95%, con
  etichetta diretta e fonte. Palette di riferimento delle linee guida dataviz.
- Prova su Napoli: grafico leggibile, +0,38 °C/decennio [0,30; 0,46]. 1 test aggiunto
  (58 in totale, tutti passano). **Blocco 1 completato.**

### Blocco 2: preparazione di Vertex AI
- Letta la documentazione attuale di ADK (ora su adk.dev): nuovo nome della variabile
  `GOOGLE_GENAI_USE_ENTERPRISE`, Vertex AI rinominato "Agent Platform". Riassunto in
  `docs/architettura.md`.
- gcloud CLI non installato sul PC: da installare.
- Configurato Google Cloud (autore): gcloud installato, progetto `earth-trend-detective-2026`
  creato da terminale (l'ID `earth-trend-detective` era già preso da altri: gli ID sono unici
  nel mondo), fatturazione collegata, API Vertex attiva, credenziali ADC.
  Problema: il primo login ADC è fallito perché nella pagina di consenso non era spuntato il
  permesso `cloud-platform`.
- Installato `google-adk` 2.14.1 con uv.
- Prima chiamata a Gemini via Vertex: 404 per `gemini-flash-latest`, serie 2.5 e regione
  `us-central1`; **funziona `gemini-3.8-flash` su `global`**. Dettagli in `docs/architettura.md`.

### Primo agente (sera del giorno 1)
- Discussione su cosa decide l'LLM: zona e variabile da liste chiuse, anni entro limiti
  controllati dal codice; soglia, confidenza, metodo e fonte fissati nel codice (idea dell'autore:
  "l'LLM sceglie regione e anni, non può toccare i calcoli").
- `src/agents/tools.py`: `analyze_trend(zone, variable, start_year, end_year)`. Valida gli input e
  in caso di errore restituisce `{"status": "error", ...}` invece di sollevare eccezioni; usa la
  cache per zona; restituisce un dict con trend, p-value (cifre significative, mai 0), pendenza e
  intervallo per decennio, osservazioni, fonte, cella condivisa.
- `src/agents/earth_trend/agent.py`: `LlmAgent` con `gemini-3.8-flash` e un solo tool; istruzioni
  con le regole di interpretazione di statistica.md. `.env` nella cartella (ignorato da git).
- Prova con una domanda su 3 casi: l'agente ha fatto **3 chiamate al tool in parallelo** e la
  risposta riporta solo numeri presenti nei risultati, con la nota corretta sugli intervalli
  sovrapposti di Napoli e Avellino.
- `tests/test_tools.py`: 11 test (validazione, maiuscole, filtro anni, errore di rete simulato).
  **69 test in totale, tutti passano.**

## 2026-11-15 (domenica, giorno 2)

### Orchestratore e sotto-agenti: scelta dell'architettura
- Letta la documentazione di ADK 2.x: SequentialAgent / LoopAgent deprecati, raccomandato il
  `Workflow` a grafo. Scelto il grafo (vedi `decisioni.md`), anche per restare aggiornati.
- Prova minima (grafo con un nodo LLM, due nodi Python e un bivio): funziona. API verificate
  scritte in `docs/architettura.md`.

### Passo 1 del grafo: contratto del piano
- `src/contracts.py`: `PlanItem` (zona, variabile, anni 1981-2024) e `Plan` (da 1 a 10 analisi).
  Zone e variabili sono `Literal` con gli stessi valori di `tools.py` (minuscolo per le zone,
  codici POWER per le variabili): diventano `enum` nello schema JSON e Gemini non può uscirne.
- Verificato: un piano valido prende gli anni di default; `'roma'` dà un errore di validazione.
- Aggiunti a `Plan` i campi `out_of_scope` (bool) e `reason` (frase per i log); `items` può
  essere vuota. Domande fuori ambito: l'LLM alza solo il flag, il ramo del grafo lo sceglie il
  codice e il messaggio all'utente è un testo fisso. Niente validatore "flag ⇒ lista vuota":
  Gemini non lo vedrebbe nello schema e un rifiuto di pydantic fermerebbe il grafo.
- Ogni campo ha una `description`, che finisce nello schema JSON letto da Gemini.

### Passo 2 del grafo: nodo Pianificatore
- `src/agents/nodes.py`: `planner` = `Agent` con `output_schema=Plan`, `output_key="plan"`.
  Le istruzioni elencano zone e variabili prese da `tools.py` (una sola fonte di verità).
- Scelta: se l'utente nomina due zone nella stessa cella (Napoli e Caserta), il Pianificatore
  le pianifica entrambe; il fatto che i dati sono identici arriva da `analyze_trend`
  (`same_grid_cell_as`) e lo controllerà il guardrail.
- Prova su 6 domande, tutte corrette: "ultimi 20 anni" → 2005-2024; "costa" → Napoli e
  Salerno con entrambe le variabili; "Campania" → tutte le zone; Roma e vento → `out_of_scope`.
