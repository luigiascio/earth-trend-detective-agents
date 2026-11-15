# Todo

Aggiornare a fine di ogni blocco di lavoro. Priorità: catena end to end prima di tutto.

## Prima di iniziare
- [ ] Leggere il Project Submission Guide e il Judging and Awards Guide ufficiali
- [x] Leggere le risorse della sfida e riportare i dataset in docs/dati.md
- [ ] Verificare nella documentazione ufficiale le API attuali di Google ADK
- [x] Verificare l'API di NASA POWER (parametri, formato, limiti): vedi docs/dati.md
- [ ] Decidere: 3 celle POWER oppure aggiungere MODIS LST (AppEEARS) o GPM IMERG per avere più zone
- [ ] Decidere frontend, accesso a Gemini, regione (docs/decisioni.md)

## Blocco 1: dati e statistica (nessun LLM)
- [x] Download e pulizia di una variabile per una regione (NASA POWER)
- [x] Mann-Kendall + Theil-Sen + intervallo di confidenza, con test (39 test)
- [x] Gestione di stagionalità e dati mancanti (Mann-Kendall stagionale, NaN tolti e contati)
- [ ] Correzione per test multipli (Benjamini-Hochberg) sui 12 trend mensili e sulle celle
- [ ] Controllare l'autocorrelazione tra anni (Hamed-Rao sulle medie annuali come verifica)
- [x] Grafico della serie con retta di trend (src/viz/plots.py)

## Blocco 2: agenti
- [ ] `src/contracts.py` con i modelli pydantic
- [x] Tool Python esposti agli agenti: `analyze_trend` (manca il tool del grafico)
- [ ] Orchestratore + sotto-agenti con Google ADK (fatto: primo agente singolo con un tool, funzionante)
- [ ] Agente di spiegazione che restituisce testo e lista di Claim

## Blocco 3: guardrail
- [ ] Controlli deterministici (numeri, segno, significatività, unità)
- [ ] Rigenerazione o template di sicurezza se non passa
- [ ] Piccolo set di valutazione e metriche

## Blocco 4: interfaccia e demo
- [ ] Interfaccia semplice: domanda, piano dell'agente, grafici, spiegazione, esito guardrail
- [ ] Fonti NASA citate a schermo
- [ ] README con architettura, istruzioni e citazioni
- [ ] Video o demo come richiesto dal Project Submission Guide

## Se resta tempo
- [ ] Seconda variabile o seconda regione (mostrare trend opposti)
- [ ] Deploy su Cloud Run / Firebase Hosting
- [ ] BigQuery per le serie temporali

## Invio
- [ ] Inviare entro il 15 novembre alle 23:59 (ora locale)
- [ ] Compilare il sondaggio partecipanti entro il 30 novembre
