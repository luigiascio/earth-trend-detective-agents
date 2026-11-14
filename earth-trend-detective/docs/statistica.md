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

## Spiegazione semplice, con un esempio fatto a mano

I numeri di questa sezione sono stati verificati con `src/stats/`. Utile anche per README e demo.

### L'esempio: 6 anni di temperature (inventate)

| Anno | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
| --- | --- | --- | --- | --- | --- | --- |
| °C | 15,0 | 15,4 | 15,1 | 15,6 | 15,5 | 16,0 |

Tre domande: sale davvero o è un caso? Di quanto? Quanto siamo sicuri?

### 1. Mann-Kendall: "sale davvero?"

Si confronta ogni anno con tutti i successivi e si segna solo +1 (sale) o −1 (scende).

| Da \ a | 2020 | 2021 | 2022 | 2023 | 2024 | Somma |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 (15,0) | + | + | + | + | + | +5 |
| 2020 (15,4) | | − | + | + | + | +2 |
| 2021 (15,1) | | | + | + | + | +3 |
| 2022 (15,6) | | | | − | + | 0 |
| 2023 (15,5) | | | | | + | +1 |

15 coppie, 13 in salita e 2 in discesa: **S = 11** (massimo possibile 15; senza trend, vicino a 0).
Tau di Kendall = 11/15 = 0,73 (scala da −1 a +1).

**Il p-value con le carte.** Si scrivono le 6 temperature su 6 carte, si mescolano e si rimettono
in fila: per costruzione non c'è nessun trend. Su tutti i 720 ordinamenti possibili, 40 danno un
|S| ≥ 11: 40/720 = 5,6%. Il p-value è questo: *se non ci fosse nessun trend, con quale probabilità
vedremmo per caso un andamento così netto?* La formula (varianza → Z → p) fa lo stesso conto senza
provare tutti gli ordinamenti e dà p = 0,060.

**Verdetto:** 6% > 5%, quindi **non significativo**, anche se a occhio sembrava ovvio. Con 44 anni
(Napoli) S = 578 e p = 5·10⁻⁹: più anni non rendono la salita più ripida, ma rendono molto meno
credibile che sia un caso. (Il codice rifiuta serie sotto le 10 osservazioni.)

### 2. Theil-Sen: "di quanto sale?"

Per ogni coppia: (differenza di temperatura) / (anni trascorsi). Esempi: 2019 → 2024 =
(16,0 − 15,0)/5 = +0,20; 2020 → 2021 = −0,30; 2021 → 2022 = +0,50. Le 15 pendenze ordinate:

```
−0,30  −0,10  0,03  0,05  0,10  0,125  0,15  [0,20]  0,20  0,20  0,20  0,30  0,40  0,50  0,50
```

La mediana (ottavo valore) è **0,20 °C/anno = 2 °C per decennio**.

**Prova dell'outlier:** se nel 2024 un errore registra 30 °C invece di 16:

| Metodo | Dati normali | Con l'errore |
| --- | --- | --- |
| Mann-Kendall, S | 11 | 11 |
| Theil-Sen | 0,20 °C/anno | 0,20 °C/anno |
| Regressione lineare | 0,17 °C/anno | 2,17 °C/anno |

### 3. Intervallo di confidenza: "quanto siamo sicuri?"

Partendo dalle pendenze ordinate, ci si allontana dalla mediana di un numero di posizioni deciso
dalla varianza di S (meno dati, più ci si allontana). Nell'esempio l'intervallo al 95% è
**[−0,10; +0,50] °C/anno**: contiene lo zero, coerente con p = 0,06. A Napoli (44 anni):
**[+0,26; +0,46] °C/decennio**, stretto e tutto sopra lo zero.

### 4. Cinque regole di interpretazione (le stesse che il guardrail deve far rispettare)

1. **"Non significativo" ≠ "non cambia".** Significa "prove insufficienti". Dire "nessun trend
   statisticamente significativo", mai "la temperatura è stabile".
2. **"Significativo" ≠ "grande".** Il p-value dice *se*, pendenza e intervallo dicono *quanto*:
   riportarli sempre insieme.
3. **Il p-value non è la probabilità che il trend sia vero.** È la probabilità di vedere un
   andamento così netto *se il trend non ci fosse*.
4. **Intervallo che contiene lo zero = direzione incerta** (es. le precipitazioni in Campania).
5. **Intervalli sovrapposti = non si può dire che uno sia maggiore.** Avellino +0,36 [0,25; 0,48]
   e Salerno +0,29 [0,20; 0,40] °C/decennio: "l'interno si scalda più della costa" non è supportato.

### 5. Perché la serie mensile inganna

Esempio con riscaldamento di 1 °C all'anno: Gen 2020 = 8, Lug 2020 = 25, Gen 2021 = 9, Lug 2021 = 26.
Gen 2020 → Gen 2021 dà "+" (utile); Lug 2020 → Gen 2021 dà "−" (dice solo che l'inverno è più
freddo dell'estate). Con 12 mesi la maggior parte delle coppie confronta stagioni diverse e il
trend sparisce nel rumore: a Salerno p = 0,057 sulla serie mensile grezza contro p = 4·10⁻⁸ sulle
medie annuali. Soluzione (passo 5): confrontare ogni mese solo con lo stesso mese degli altri anni.
