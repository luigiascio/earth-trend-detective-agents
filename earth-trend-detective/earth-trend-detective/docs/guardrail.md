# Guardrail: spiegazione contro numeri

Obiettivo: nessuna frase mostrata all'utente può contraddire i numeri calcolati dal codice.

## Come funziona
1. L'agente di spiegazione produce il testo **e** una lista strutturata di affermazioni
   (`Claim`): per ciascuna indica quale campo di `TrendResult` la sostiene.
2. Il guardrail confronta ogni `Claim` con il valore reale, in codice.
3. Esito: `GuardrailReport` con `passed`, elenco di violazioni e correzioni suggerite.
4. Se non passa: si rigenera la spiegazione (massimo 2 tentativi) oppure si mostra una
   spiegazione di sicurezza costruita da un template con i numeri veri.

## Controlli minimi
- **Numeri:** ogni valore citato (pendenza, p-value, periodo, n. osservazioni) coincide con
  `TrendResult`, entro la precisione dichiarata.
- **Significatività:** non si scrive "significativo" se il test dice di no; non si scrive
  "nessun trend" se il test è significativo.
- **Direzione:** "in aumento"/"in calo" coerente con il segno della pendenza.
- **Unità e periodo:** presenti e corretti.
- **Causalità:** vietato attribuire cause ("a causa di...") se non sono nei dati o in una
  fonte citata; descrivere il cambiamento, non spiegarlo.
- **Incertezza:** se i dati sono pochi o l'intervallo di confidenza è largo, la spiegazione
  deve dirlo.

## Implementazione
- Controlli deterministici in Python per numeri, segno, soglia di significatività.
- Per le affermazioni testuali libere si può aggiungere un controllo con LLM, ma solo come
  secondo livello: il primo è sempre quello deterministico.
- Metriche da mostrare nella demo: percentuale di spiegazioni che passano al primo
  tentativo, tipi di violazioni trovate, esempi prima/dopo la correzione.

## Valutazione
Costruire un piccolo set di casi di test (anche 10-20): risultati veri più spiegazioni
corrette e spiegazioni volutamente sbagliate. Misurare quante violazioni il guardrail
intercetta. È la parte che rende il progetto diverso da un semplice "grafico con testo".

## Bozza di contratti
`Claim` (testo, campo di riferimento, valore dichiarato), `GuardrailReport`
(passed, violations, attempts). Definirli in `src/contracts.py`.
