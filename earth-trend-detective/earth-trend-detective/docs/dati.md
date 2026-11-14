# Dati

> Regola: non inventare dettagli sulle API. Tutto ciò che è marcato "DA VERIFICARE" va
> controllato nella documentazione ufficiale e poi scritto qui.

## Candidato principale: NASA POWER
- Fornisce parametri meteorologici e solari (temperatura superficiale, precipitazioni) per
  qualsiasi coordinata, con serie lunghe dal 1981. API gratuita, senza chiave (DA VERIFICARE).
- Sito: https://power.larc.nasa.gov/
- Motivo: semplice da scaricare per punto o piccola area, ideale per un prototipo in 48 ore.
- DA VERIFICARE: endpoint esatto, parametri (es. temperatura a 2 m, precipitazione),
  risoluzione temporale (giornaliera/mensile), limiti di richiesta, formato di risposta.

## Altri dataset (solo dopo che la catena funziona)
| Dataset | Variabile | Note |
| --- | --- | --- |
| NSIDC Sea Ice Index | estensione ghiaccio marino | serie dal 1979 |
| NASA/JPL PODAAC | anomalia livello del mare | serie dal 1993 |
| MERRA-2 | rianalisi atmosferica | serie lunghe, file più pesanti |
| GPM IMERG | precipitazioni | richiede account Earthdata |
| MODIS NDVI | vegetazione | file pesanti |
| SMAP | umidità del suolo | file pesanti, copertura più recente |

## Risorse ufficiali della sfida
Le risorse e i dataset suggeriti per ogni sfida sono pubblicati su spaceappschallenge.org
(pagina della sfida, accessibile con login). DA FARE: leggerli e riportare qui i dataset
ufficiali consigliati.

## Schema dati interno (bozza)
Serie temporale: colonne `date` (ISO), `value` (float), `variable`, `unit`, `lat`, `lon`,
`source`. Valori mancanti esplicitati come NaN, mai riempiti in silenzio.

## Cache
Scaricare in `data/raw/` (ignorata da git) e salvare i dati puliti in `data/processed/`.
Non rifare download inutili: controllare prima se il file esiste.

## Citazioni
Ogni dataset usato va citato nell'interfaccia e nel README con nome, ente e URL.
