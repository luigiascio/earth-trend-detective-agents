# Earth Trend Detective

Progetto per la **NASA Space Apps Challenge 2026**, sfida *Be An Earth System Trend Detective!*

Un sistema multi-agente che, data una domanda in linguaggio naturale, sceglie una variabile
di Earth science, scarica i dati NASA, calcola trend con test statistici e spiega il risultato.
Un guardrail verifica che la spiegazione corrisponda ai numeri calcolati.

**Principio:** l'LLM decide e spiega, il codice calcola.

## Stato
Progetto in sviluppo durante l'hackathon (14-15 novembre 2026). Vedi `docs/todo.md`.

## Struttura
```
CLAUDE.md          contesto per Claude Code (radice dei documenti)
docs/              sfida, architettura, dati, statistica, guardrail, decisioni, todo
src/stats/         funzioni statistiche pure
src/agents/        orchestratore e sotto-agenti
src/contracts.py   modelli pydantic (da creare)
tests/             test
data/raw/          dati scaricati (ignorati da git)
data/processed/    dati puliti (ignorati da git)
```

## Avvio rapido
Da completare quando esiste il codice (ambiente virtuale, installazione dipendenze,
variabili d'ambiente per Gemini, comando per avviare l'app).

## Fonti dei dati
Da completare con le citazioni dei dataset NASA usati (nome, ente, URL).

## Licenza
MIT, vedi `LICENSE`.
