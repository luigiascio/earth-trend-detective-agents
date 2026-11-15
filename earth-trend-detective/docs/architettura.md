# Architettura

Principio: **l'LLM decide e spiega, il codice calcola.** Ogni componente ha input e output
tipizzati (pydantic) in `src/contracts.py`, così si vede dove finisce un pezzo e inizia
l'altro.

## Flusso
```
Domanda utente
   │
   ▼
[Orchestratore] ── piano (variabile, regione, periodo) ──┐
   │                                                     │
   ├─► [Agente dati]        → serie temporale pulita (DataResult)
   ├─► [Agente statistico]  → trend, pendenza, p-value, significatività (TrendResult)
   ├─► [Agente visualizzazione] → grafici/mappe (VizResult)
   │
   ▼
[Agente spiegazione] → testo in linguaggio naturale (Explanation)
   │
   ▼
[Guardrail] → verifica ogni affermazione contro i numeri (GuardrailReport)
   │
   ▼
Risposta mostrata all'utente (solo se il guardrail passa)
```

## Componenti

### 1. Orchestratore
- Riceve la domanda ("cosa sta cambiando nelle temperature del Sud Italia?").
- Produce un `Plan`: variabile, regione (bounding box o punto), periodo, test da usare.
- Delega ai sotto-agenti nell'ordine giusto. Non calcola nulla.

### 2. Agente dati
- Sceglie il dataset adatto alla variabile (vedi @docs/dati.md) e chiama il tool di download.
- Il download e la pulizia sono codice Python (`src/agents/data_tools.py`), non LLM.
- Output: `DataResult` con serie temporale, unità, fonte, periodo coperto, buchi nei dati.

### 3. Agente statistico
- Chiama funzioni pure in `src/stats/` (vedi @docs/statistica.md).
- Output: `TrendResult` con pendenza, unità, intervallo di confidenza, p-value, esito
  "significativo sì/no", metodo usato, numero di osservazioni.
- L'LLM sceglie quale test usare e con quali parametri; non scrive mai i valori.

### 4. Agente di visualizzazione
- Produce grafico della serie con retta di trend; se c'è più di una regione, mostra anche
  dove il trend va in direzione opposta (è il punto centrale della sfida).

### 5. Agente di spiegazione
- Riceve solo `TrendResult` e `DataResult` e scrive il testo. Deve citare i numeri così come
  sono, senza arrotondamenti non dichiarati.

### 6. Guardrail
- Vedi @docs/guardrail.md. Blocca o corregge la spiegazione se non corrisponde ai numeri.

## Mappatura su Google ADK (verificata il 2026-11-14 su adk.dev)
- Orchestratore = agente principale con sotto-agenti.
- Tool = funzioni Python con type hints e docstring chiare.
- Modello: Gemini via Vertex AI (decisione in decisioni.md).
- Prima di scrivere codice ADK, leggere la documentazione attuale: le API cambiano.

### Cosa dice la documentazione oggi
- **Sito:** la documentazione è passata da google.github.io/adk-docs a **https://adk.dev**.
  Vertex AI ora si chiama "Google Cloud Agent Platform".
- **Pacchetto:** `google-adk` (Python 3.10+). Con uv: `uv add google-adk`.
- **Variabili d'ambiente per Vertex** (file `.env` dentro la cartella dell'agente):
  - `GOOGLE_GENAI_USE_ENTERPRISE=TRUE` (nuovo nome; prima era `GOOGLE_GENAI_USE_VERTEXAI`,
    equivalente: usare il vecchio solo con versioni vecchie di ADK)
  - `GOOGLE_CLOUD_PROJECT=<id-progetto>`
  - `GOOGLE_CLOUD_LOCATION=<regione>` (esempio nei documenti: `us-central1`)
  - non usare `GOOGLE_API_KEY`: è la strada di AI Studio.
- **Autenticazione locale:** gcloud CLI installato, API `aiplatform.googleapis.com` attiva sul
  progetto, poi `gcloud auth application-default login`. In produzione: service account con
  ruolo "Agent Platform User".
- **Struttura:** `adk create <nome>` crea `<nome>/agent.py`, `<nome>/__init__.py`, `<nome>/.env`.
  `agent.py` deve definire `root_agent` (unico elemento obbligatorio).
- **Esecuzione:** `adk run <nome>` (terminale) oppure `adk web --port 8000` lanciato dalla cartella
  che contiene `<nome>/` (interfaccia web solo per sviluppo).
- **Agente con tool:** `from google.adk.agents import LlmAgent` (il quickstart usa
  `from google.adk.agents.llm_agent import Agent`); il tool è una funzione tipizzata con
  docstring che restituisce un `dict`; si passa con `tools=[funzione]`.
- **Modello:** gli esempi usano `gemini-flash-latest`, ma su un endpoint regionale (es.
  `us-central1`) l'alias può non funzionare: usare una versione precisa. DA VERIFICARE quale.
- **Multi-agente:** `LlmAgent(..., sub_agents=[a, b])` (trasferimento deciso dall'LLM). Per un
  sotto-agente usato come "strumento", la documentazione consiglia `mode='single_turn'` sul
  sotto-agente più `sub_agents`, invece di `AgentTool(agent=...)`. In ADK 2.0 i workflow basati
  su `BaseAgent` sono superati dai workflow a grafo (https://adk.dev/graphs/): DA VALUTARE.
- DA VERIFICARE: contenuto di `__init__.py` generato da `adk create`.

### Configurazione verificata sul nostro progetto (2026-11-14)
- Installato `google-adk` **2.14.1** (porta con sé `google-genai` 2.34.0).
- Progetto Google Cloud: `earth-trend-detective-2026`, fatturazione attiva, API
  `aiplatform.googleapis.com` attiva, credenziali ADC con quota project impostato.
- **Località: `global`.** Su `us-central1` tutti i modelli provati rispondono 404.
- **Modello: `gemini-3.8-flash`** (risponde su `global`; funzionano anche `gemini-3.5-flash` e
  `gemini-3.1-flash-lite`). `gemini-flash-latest` e la serie 2.5 rispondono 404 "not found or
  your project does not have access", anche se `gemini-2.5-flash` compare in `models.list()`:
  la lista non garantisce l'accesso, va sempre fatta una chiamata di prova.
- Prova minima (fuori da ADK): `genai.Client(vertexai=True, project=..., location="global")`
  e `client.models.generate_content(model="gemini-3.8-flash", contents=...)`.

## Contratti (bozza)
Definire in `src/contracts.py` con pydantic: `Plan`, `DataResult`, `TrendResult`,
`VizResult`, `Explanation`, `GuardrailReport`. Aggiornare questo file se cambiano.

## Cosa NON fare
- Niente numeri prodotti dall'LLM.
- Niente agenti che chiamano altri agenti senza passare dall'orchestratore.
- Niente scope creep: prima 1 variabile e 1 regione end to end.

### Workflow a grafo: API verificate su ADK 2.14.1 (prova minima, 2026-11-15)
- Import: `from google.adk import Agent, Event, Workflow` (`Agent` = `LlmAgent`).
- Grafo: `Workflow(name=..., edges=[("START", a, b, c), (c, {"PASS": d, "FAIL": e})])`.
  Una tupla è una catena di nodi; un dizionario a destra mappa il valore del route sul nodo.
- **Nodo LLM con output strutturato:** `Agent(..., output_schema=ModelloPydantic, output_key="plan")`
  → il risultato finisce nello stato come **dict** (`state["plan"]`) ed è anche l'output del nodo.
- **Nodo Python:** una funzione normale. I parametri con il nome di una chiave dello stato vengono
  riempiti dallo stato (es. `def analyze(plan: dict)` riceve `state["plan"]`); il parametro
  `node_input` riceve l'output del nodo precedente; `ctx` riceve il contesto.
- **Cosa restituisce un nodo Python:** `Event(output=..., state={...}, route="...", message="...")`.
  `state` aggiorna lo stato della sessione, `route` sceglie l'arco, `message` è il testo per l'utente.
- Esecuzione: `InMemoryRunner(agent=root_agent, app_name=...)`, come per un agente singolo.
- **Limite di Gemini (Vertex AI):** uno schema di output con `maxItems` > 32 viene rifiutato con
  400 INVALID_ARGUMENT (verificato: 32 funziona, 33 no). Per questo `Plan.items` non ha
  `max_length` e il limite di analisi è applicato nel nodo Analisi.
