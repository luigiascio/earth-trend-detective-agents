# Earth Trend Detective: contesto del progetto

Progetto per la NASA Space Apps Challenge 2026 (14-15 novembre), sfida
**"Be An Earth System Trend Detective!"** (livello avanzato).
Obiettivo secondario dell'autore: capire a fondo l'architettura di un sistema multi-agente
(Google ADK su Google Cloud, in preparazione alla certificazione Professional ML Engineer).

## Regola numero uno
**L'LLM decide e spiega, il codice calcola.** Nessun numero, trend o p-value
può essere prodotto dall'LLM: arriva sempre da una funzione Python in `src/stats/`.
Ogni affermazione nella spiegazione finale deve essere verificata dal guardrail
(vedi @docs/guardrail.md) prima di essere mostrata.

## Mappa dei documenti (leggi solo quello che serve al compito)
- @docs/sfida.md: testo della sfida, cosa va consegnato, criteri di giudizio
- @docs/architettura.md: orchestratore, sotto-agenti, interfacce tra componenti
- @docs/dati.md: dataset, come scaricarli, schema dei dati
- @docs/statistica.md: metodi statistici e quando usarli
- @docs/guardrail.md: verifica "spiegazione contro numeri"
- @docs/decisioni.md: registro delle scelte e dei motivi (aggiornalo!)
- @docs/todo.md: stato dei lavori e priorità per la demo

## Vincoli
- Tempo: 48 ore. Priorità: prototipo piccolo che funziona end to end, non completo.
- Scope iniziale: 1-2 variabili, 1 regione. Allargare solo dopo che la catena funziona.
- Il progetto va sviluppato durante i due giorni dell'hackathon (verifica il Project
  Submission Guide ufficiale per le regole esatte).
- Citare sempre le fonti dei dati NASA nell'interfaccia e nel README.
- Non copiare codice da altri progetti della stessa sfida.

## Stack
- Python 3.11+, FastAPI, pandas/numpy/xarray, scipy, pymannkendall (o implementazione propria)
- Agenti: Google ADK con Gemini (Vertex AI o API key). Verifica sempre la documentazione
  ufficiale aggiornata di ADK prima di scrivere codice: le API cambiano.
- Frontend: semplice (Streamlit oppure pagina web con grafici). Scegliere in docs/decisioni.md.
- Deploy opzionale a fine progetto: Cloud Run / Firebase Hosting.

## Convenzioni
- Codice e commenti in inglese; documentazione in italiano.
- Ogni sotto-agente ha input e output tipizzati (pydantic) definiti in `src/contracts.py`.
- Funzioni statistiche pure, con test in `tests/`.
- Dopo ogni scelta architetturale importante, aggiungi una riga a docs/decisioni.md.
- Aggiorna docs/todo.md a fine di ogni blocco di lavoro.

## Come lavorare
1. Prima di scrivere codice nuovo, leggi @docs/architettura.md e @docs/todo.md.
2. Se un'informazione sui dati o sulle API non è nei documenti, verificala (non inventarla)
   e poi scrivila nel documento giusto.
3. Se una scelta è ambigua e cambia l'architettura, chiedi prima di procedere.
