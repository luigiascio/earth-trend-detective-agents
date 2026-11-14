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

## Mappatura su Google ADK (da verificare nella documentazione ufficiale aggiornata)
- Orchestratore = agente principale con sotto-agenti.
- Tool = funzioni Python con type hints e docstring chiare.
- Modello: Gemini via Vertex AI o API key.
- Prima di scrivere codice ADK, leggere la documentazione attuale: le API cambiano.

## Contratti (bozza)
Definire in `src/contracts.py` con pydantic: `Plan`, `DataResult`, `TrendResult`,
`VizResult`, `Explanation`, `GuardrailReport`. Aggiornare questo file se cambiano.

## Cosa NON fare
- Niente numeri prodotti dall'LLM.
- Niente agenti che chiamano altri agenti senza passare dall'orchestratore.
- Niente scope creep: prima 1 variabile e 1 regione end to end.
