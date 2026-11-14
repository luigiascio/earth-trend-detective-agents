# Statistica

Questo è il cuore scientifico del progetto: separa un bel grafico da un'analisi seria.
Tutte le funzioni sono **pure**, in `src/stats/`, con test in `tests/`.

## Metodi
| Domanda | Metodo | Note |
| --- | --- | --- |
| C'è un trend monotono? | Test di **Mann-Kendall** | non parametrico, robusto a outlier e non normalità |
| Quanto vale la pendenza? | **Theil-Sen** (pendenza di Sen) | robusta; riportare unità per anno o per decennio |
| Stagionalità | Mann-Kendall stagionale oppure deseasonalizzare (anomalie rispetto alla climatologia) | decidere e scrivere in decisioni.md |
| Autocorrelazione | correzione (es. prewhitening o variante di Hamed-Rao) | senza correzione i p-value sono troppo ottimisti |
| Tanti punti/regioni | correzione per test multipli (**FDR**, Benjamini-Hochberg) | necessaria se si mappa su più celle |
| Incertezza | intervallo di confidenza della pendenza | mostrarlo sempre |

## Definizione di "significativo"
Soglia di partenza: p < 0.05 dopo le correzioni appropriate. Scrivere sempre nel risultato
quale test, quale soglia, quante osservazioni e quale correzione sono stati usati.

## Regole
- Mai dichiarare un trend da serie troppo corte: fissare un minimo di anni/osservazioni
  e restituire "dati insufficienti" sotto quel minimo.
- Non confondere stagionalità con trend di lungo periodo.
- Riportare la pendenza con unità (es. °C/decennio) e il periodo esatto.
- Il risultato deve poter dire anche "nessun trend significativo": è una risposta valida.

## Implementazione
Si può usare `pymannkendall` oppure scrivere il test a mano con numpy/scipy. Se si usa la
libreria, verificare nella sua documentazione cosa restituisce e che correzioni offre. Se si
scrive a mano, confrontare i risultati con la libreria nei test.

## Test da scrivere (`tests/`)
- Serie sintetica con trend noto: pendenza recuperata entro tolleranza.
- Serie casuale senza trend: non significativa nella grande maggioranza dei casi.
- Serie con valori mancanti: gestita senza errori e dichiarata.
- Serie troppo corta: restituisce "dati insufficienti".
