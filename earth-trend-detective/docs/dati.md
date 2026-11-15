# Dati

> Regola: non inventare dettagli sulle API. Tutto ciò che è marcato "DA VERIFICARE" va
> controllato nella documentazione ufficiale e poi scritto qui.

## Ambito scelto
- **Regione:** Campania, con 4-5 zone di campionamento (vedi sotto).
- **Variabili:** prima temperatura, poi precipitazioni.
- **Motivo del campionamento a punti:** la Campania è piccola; con dati a griglia grossolana cadrebbero in regione pochissime celle e il contrasto spaziale sparirebbe. Scegliere i punti tenendo conto della risoluzione del dataset (DA VERIFICARE per ogni fonte).

### Zone di campionamento (bozza)
Le coordinate sono **approssimate** e corrispondono ai capoluoghi o ai centri principali: servono come punto di partenza. Scegliere i punti definitivi in base alla risoluzione del dataset e a quanto rappresentano costa o interno.

| Zona | Ambiente | Coordinate approssimative (lat, lon) |
| --- | --- | --- |
| Costa napoletana | costa, urbano | 40.85, 14.27 |
| Salernitano | costa meridionale | 40.68, 14.77 |
| Irpinia (Avellino) | Appennino interno | 40.91, 14.79 |
| Sannio (Benevento) | interno, collinare | 41.13, 14.78 |
| Casertano | pianura interna | 41.07, 14.33 |

## Risorse ufficiali della sfida (dalla pagina della sfida, 2026-11-14)

NASA non garantisce i siti non governativi USA: per questi vanno rispettate le condizioni d'uso del sito.

### Dati e strumenti NASA
| Risorsa | Cosa offre | Accesso da codice |
| --- | --- | --- |
| Giovanni (giovanni.gsfc.nasa.gov) | menu di molte variabili, generazione e download di serie temporali | DA VERIFICARE: di solito serve un account Earthdata gratuito; interfaccia web, non è chiaro se interrogabile da programma |
| Hydrology Time Series (disc.gsfc.nasa.gov) | serie temporali di dati idrologici | DA VERIFICARE |
| AppEEARS (appeears.earthdatacloud.nasa.gov) | accesso e trasformazione di dati geospaziali da vari archivi federali, con serie temporali | DA VERIFICARE: probabilmente il più adatto a un agente se offre un'API; serve account Earthdata |
| Climate Data Online, NOAA (ncei.noaa.gov/cdo-web) | archivio di dati storici di meteo e clima globale, informazioni sulle stazioni, mappa | DA VERIFICARE: di solito serve un token gratuito |
| Articolo SeaWiFS (ntrs.nasa.gov) | creazione di serie temporali e test di significatività su clorofilla costiera | solo riferimento bibliografico |

### Risorse delle agenzie partner
| Risorsa | Uso nel progetto |
| --- | --- |
| KNMI Climate Explorer (climexp.knmi.nl) | **verifica incrociata** dei nostri trend con uno strumento riconosciuto (parte "validità") |
| Articolo sui metodi statistici per trend | riferimento per docs/statistica.md |
| Guida alla significatività statistica (statsig.com) | riferimento per docs/statistica.md |
| CSA: RCM (dati radar), Geo.ca, missione SWOT, tutorial SAR in Python | riferimenti, non necessari per l'ambito scelto (Canada e dati radar) |

## Fonte di partenza (provvisoria): NASA POWER
- Fornisce parametri meteorologici e solari (temperatura superficiale, precipitazioni) per qualsiasi coordinata, con serie lunghe dal 1981. API gratuita, senza chiave (DA VERIFICARE).
- Sito: https://power.larc.nasa.gov/
- Non compare nell'elenco ufficiale ma è una risorsa NASA: va bene per la regola "almeno un dato NASA".
- **Primo controllo da fare (30-45 minuti):** verificare se POWER, AppEEARS o Giovanni si possono interrogare da codice per le zone della Campania, con quale risoluzione, formato e limiti. Scrivere qui i risultati.
- DA VERIFICARE per POWER: limiti di richiesta ufficiali, risoluzione nominale della griglia nella documentazione.

### Verifica di NASA POWER (fatta il 2026-11-14)
- **Endpoint usato:** `https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M,PRECTOTCORR&community=AG&latitude=<lat>&longitude=<lon>&start=1981&end=2024&format=JSON`
- **Accesso:** nessuna chiave né account. Risposta in circa 1-2 minuti per punto. Alcune richieste sono andate in timeout (`curl` senza risposta) e sono riuscite al secondo tentativo: il codice deve prevedere **retry e cache**.
- **Risposta:** API v2.10.0, fonte `MERRA2`, `fill_value` -999 (nessun valore mancante nelle 5 serie), orario LST.
- **Parametri:** `T2M` (temperatura a 2 m, °C), `PRECTOTCORR` (precipitazione corretta, mm/giorno).
- **Formato:** `properties.parameter.<VAR>` è un dizionario `"AAAAMM": valore`. Il mese **`13` è la media annuale** (es. `202413`): va scartato prima di analizzare la serie mensile. 1981-2024 dà 572 chiavi (528 mesi + 44 annuali).
- **La terza coordinata in `geometry`** è la quota media della cella (264, 295, 496 m), non quella del punto: conferma che il dato è per cella.
- **Risoluzione spaziale: troppo grossolana per 5 zone.** Le 5 zone danno solo **3 serie distinte** (identiche valore per valore):

| Cella | Zone | T2M annuale 1981 → 2024 |
| --- | --- | --- |
| A, costa e pianura nord (quota 264 m) | Napoli, Caserta | 14,59 → 17,43 °C |
| B, costa sud (quota 295 m) | Salerno | 15,14 → 17,62 °C |
| C, interno appenninico (quota 496 m) | Avellino, Benevento | 13,07 → 16,05 °C |

- File grezzi: `data/raw/power_monthly_<zona>.json`.

## Dataset non confermati
Un indice di terzi (Space Data Atlas) elenca per questa sfida sei dataset, con titoli troncati: MERRA-2 (diagnostiche mensili), Giovanni, GISTEMP, GRACE e GRACE-FO (mascon), GLDAS Noah (mensile), Aqua AIRS (livello 3 mensile). **Non confermati** dalla pagina ufficiale. MERRA-2, GLDAS e AIRS di solito richiedono un account Earthdata gratuito (DA VERIFICARE). Usarli solo dopo aver verificato accesso e risoluzione.

## Schema dati interno (bozza)
Serie temporale: colonne `date` (ISO), `value` (float), `variable`, `unit`, `lat`, `lon`, `zone`, `source`. Valori mancanti esplicitati come NaN, mai riempiti in silenzio.

## Cache
Scaricare in `data/raw/` (ignorata da git) e salvare i dati puliti in `data/processed/`. Non rifare download inutili: controllare prima se il file esiste.

## Citazioni (da riportare in interfaccia e README)
Ogni dataset usato va citato con nome, ente e URL. L'elenco di **tutte** le risorse usate (dati, codice, testi, immagini, anche open source) va nel campo di riferimento del modulo di invio. Per ora: NASA POWER (NASA Langley Research Center), KNMI Climate Explorer (KNMI) per la verifica, e gli articoli sui metodi statistici.


## Zone in Italia (2026-11-15)
13 zone, una per area climatica (coordinate in `src/agents/tools.py`). Verifica: le serie T2M
delle 13 zone sono tutte diverse tra loro, quindi nessuna coppia condivide una cella MERRA-2.
Attenzione: le coordinate restituite dall'API sono quelle richieste, non il centro della cella;
per sapere se due punti sono nella stessa cella bisogna confrontare le serie.

Trend 1981-2024 (Mann-Kendall stagionale, pendenza di Sen per decennio, IC 95%):

| Zona | T2M (°C/decennio) | PRECTOTCORR (mm/giorno/decennio) |
| --- | --- | --- |
| aosta | +0.481 [0.373; 0.589] | nessun trend |
| milano | +0.481 [0.380; 0.575] | nessun trend |
| firenze | +0.467 [0.374; 0.576] | nessun trend |
| bolzano | +0.448 [0.342; 0.556] | +0.090 [0.027; 0.150] |
| genova | +0.418 [0.338; 0.508] | nessun trend |
| venezia | +0.405 [0.319; 0.490] | nessun trend |
| roma | +0.400 [0.320; 0.486] | nessun trend |
| aquila | +0.400 [0.300; 0.500] | +0.081 [0.006; 0.153] |
| napoli | +0.375 [0.297; 0.462] | nessun trend |
| bari | +0.339 [0.262; 0.419] | +0.067 [0.013; 0.122] |
| cagliari | +0.311 [0.258; 0.369] | nessun trend |
| cosenza | +0.232 [0.144; 0.316] | +0.161 [0.094; 0.230] |
| palermo | +0.218 [0.152; 0.283] | +0.030 [0.000; 0.071], p ≈ 0.05 |

Nessun test corretto per confronti multipli: da presentare come risultati esplorativi.
Le zone campane precedenti (Caserta, Salerno, Avellino, Benevento) sono state tolte.
