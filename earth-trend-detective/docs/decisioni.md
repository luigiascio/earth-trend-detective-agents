# Registro delle decisioni

Aggiungere una riga a ogni scelta architetturale importante: cosa, perché, alternative scartate.
Stato: **decisa** = confermata; **provvisoria** = da rivedere dopo una verifica indicata.

| Data | Decisione | Stato | Motivo | Alternative scartate |
| --- | --- | --- | --- | --- |
| 2026-11-14 | L'LLM spiega, il codice calcola | decisa | evitare numeri inventati, rendere i risultati verificabili | far calcolare trend all'LLM |
| 2026-11-14 | Sfida: Be An Earth System Trend Detective! | decisa | si adatta al background EO/statistica e a un'architettura ad agenti | Flame in Freefall, Field Shift |
| 2026-11-14 | Agenti con Google ADK | decisa | allinea il progetto alla preparazione per la certificazione Google Cloud | LangGraph, agenti scritti a mano |
| 2026-11-14 | Regione: **Campania**, con 4-5 zone di campionamento (non una mappa continua) | decisa | progetto concreto e locale (criterio Impatto); ambienti diversi in poco spazio (costa, pianure, Appennino) permettono di mostrare trend diversi nella stessa regione | globo mondiale con molte variabili, Italia intera |
| 2026-11-14 | Variabili: prima **temperatura**, poi **precipitazioni** | decisa | la temperatura ha un segnale di trend più chiaro; le precipitazioni sono rumorose e spesso senza trend significativo: caso ideale per mostrare che il guardrail sa dire "nessun trend significativo" | NDVI e altre variabili (file più pesanti, solo se avanza tempo) |
| 2026-11-14 | Fonte dati: **NASA POWER** come scelta di partenza | provvisoria | risorsa NASA con API semplice e senza file pesanti; serve anche a rispettare la regola "almeno un dato NASA" per il Global Award | Giovanni, AppEEARS, CDO (vedi docs/dati.md) |
| 2026-11-14 | Validazione dei risultati con **KNMI Climate Explorer** (almeno un confronto) | decisa | strumento indicato tra le risorse ufficiali della sfida; rafforza il criterio Validità | nessuna verifica esterna |

| 2026-11-14 | Con NASA POWER, le zone vanno trattate come **celle**: 5 zone danno solo 3 serie distinte (Napoli = Caserta, Avellino = Benevento) | provvisoria | verifica in docs/dati.md; due zone con dati identici darebbero un falso confronto | presentare 5 zone come indipendenti |
| 2026-11-14 | Gemini via **Vertex AI** | decisa | allenamento per la certificazione Professional ML Engineer; configurazione da fare insieme prima del Blocco 2 | API key di AI Studio (più rapida) |
| 2026-11-14 | Ordine di lavoro: **Blocco 1 (dati e statistica) prima di tutto**, scritto passo passo insieme all'autore | decisa | non dipende da frontend né da Gemini; è la parte con più rischio di errori scientifici | partire dagli agenti |
| 2026-11-14 | Gestione ambiente e dipendenze con **uv** (`pyproject.toml` + `uv.lock`) | decisa | installazioni rapide, versioni bloccate e riproducibili per i giudici, dipendenze di sviluppo separate | pip + requirements.txt |
| 2026-11-14 | Stagionalità: **Mann-Kendall stagionale** (Hirsch 1982) + pendenza di Sen stagionale | decisa | il test sulla serie mensile grezza perdeva il trend (Salerno p = 0,057 contro 4·10⁻⁸ sulle medie annuali); usa tutti i mesi e dà anche il trend di ogni mese ("quale stagione si scalda di più"); verificabile con `pymannkendall.seasonal_test` | solo medie annuali (tenute come controllo incrociato); anomalie + Hamed-Rao |
| 2026-11-15 | Multi-agente con **`Workflow` a grafo** di ADK 2.x: Pianificatore (LLM) → Analisi (Python) → Spiegazione (LLM) → Guardrail (Python, con route PASS / RETRY / FALLBACK) → Risposta di sicurezza (Python) | decisa | il percorso è garantito dal codice (nessuna risposta senza guardrail); agente dati e statistico diventano un nodo Python perché non c'è nulla da decidere; SequentialAgent / LoopAgent deprecati in ADK 2.x | `sub_agents` con LLM orchestratore (meno controllabile); SequentialAgent (deprecato) |

### Condizione per rivedere la fonte dati
Decisione provvisoria: se un test mostra che AppEEARS, Giovanni o NASA POWER non si possono interrogare da codice per la Campania, o che la risoluzione è troppo grossolana per le zone scelte, cambiare fonte e aggiornare questa riga.

## Regole della sfida che vincolano le scelte (dal Project Submission Guide 2026)
- **Uso della SI:** gli strumenti di intelligenza artificiale sono ammessi, ma vanno dichiarati. Codice e dati: indicazione nel testo descrittivo e nei metadati; immagini e video: filigrana visibile. La SI non dovrebbe servire per trovare l'idea della soluzione. Nel README ci sarà una sezione "Uso della SI" con una descrizione onesta di cosa ha generato l'AI e cosa è stato deciso dall'autore.
- **Demo:** video di massimo 30 secondi (sottotitoli in inglese) oppure massimo 7 slide in inglese, con link pubblico senza login. Oltre i limiti il progetto non è ammesso al Global Judging.
- **Repository pubblico** prima dell'invio, senza chiavi API o credenziali.
- **Tutto in inglese** nel modulo del progetto e nei materiali collegati.
- **Almeno un dato o una risorsa NASA** per l'eleggibilità al Global Award; elencare tutte le risorse usate, comprese quelle open source.
- **Niente loghi o grafica NASA** nei contenuti generati; niente immagini o video di persone sotto i 18 anni.
- **Partecipazione confermata** (non in waitlist) a un evento locale per essere eleggibili ai premi.
- Scadenza invio: domenica 15 novembre, 23:59, ora locale dell'evento.

## Da decidere
- [ ] Frontend: Streamlit oppure pagina web con grafici?

- [ ] Coordinate esatte delle zone di campionamento (vedi docs/dati.md)
- [ ] Deploy su Cloud Run: sì o solo in locale?
- [ ] Demo: video da 30 secondi oppure 7 slide?
