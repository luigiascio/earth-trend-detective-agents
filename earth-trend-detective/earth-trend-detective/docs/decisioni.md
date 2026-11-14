# Registro delle decisioni

Aggiungere una riga a ogni scelta architetturale importante: cosa, perché, alternative scartate.

| Data | Decisione | Motivo | Alternative scartate |
| --- | --- | --- | --- |
| 2026-11-14 | L'LLM spiega, il codice calcola | evitare numeri inventati, rendere i risultati verificabili | far calcolare trend all'LLM |
| 2026-11-14 | Sfida scelta: Be An Earth System Trend Detective! | si adatta al background EO/statistica e a un'architettura ad agenti | Flame in Freefall, Field Shift |
| 2026-11-14 | Primo dataset: NASA POWER | API semplice, serie lunghe, niente file pesanti | MERRA-2, GPM, MODIS |
| 2026-11-14 | Agenti con Google ADK | allinea il progetto alla preparazione per la certificazione Google Cloud | LangGraph, agenti scritti a mano |

## Da decidere
- [ ] Frontend: Streamlit oppure pagina web con grafici?
- [ ] Gemini via Vertex AI o via API key?
- [ ] Test stagionale: Mann-Kendall stagionale o anomalie rispetto alla climatologia?
- [ ] Regione di partenza (es. Italia meridionale?)
- [ ] Deploy su Cloud Run: sì o solo in locale?
