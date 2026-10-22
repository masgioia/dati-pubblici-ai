# Dati pubblici spiegati dall'AI

Assistente AI per interrogare dati statistici ufficiali con fonti verificabili.

## Prototipo iniziale: popolazione residente

La prima pipeline scarica osservazioni SDMX dell'ISTAT e calcola la variazione assoluta e percentuale della popolazione tra due anni per le regioni italiane (codici NUTS-2).

### Esecuzione in GitHub Codespaces

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.istat_population --start-year 2014 --end-year 2024
```

I risultati vengono salvati in:
- `data/istat_population_raw.csv`: osservazioni originali ricevute dall'API.
- `data/regional_population_change.csv`: confronto regionale calcolato.

Per usare altri anni, cambia `--start-year` e `--end-year`. L'anno finale deve essere presente nei dati resi disponibili dal servizio.

## Fonte e limiti

- Dataset: ISTAT, **Popolazione residente al 1° gennaio**, dataflow `22_289`, struttura `DCIS_POPRES1`.
- [Pagina ISTAT sui Web Services SDMX](https://www.istat.it/classificazioni-e-strumenti/web-services-sdmx/).
- [Documentazione e note operative sull'endpoint](https://ondata.github.io/guida-api-istat/processing/note-endpoint-esploradati/).
- Endpoint di download configurato nello script: `https://esploradati.istat.it/SDMXWS/rest/data/IT1,22_289/A..JAN.9.TOTAL.99/`.
- Workaround documentato per il filtro temporale: l'endpoint restituisce un anno in più rispetto a `endPeriod`; lo script richiede `endPeriod = anno finale - 1` e poi filtra localmente gli anni richiesti. La chiamata può richiedere alcuni minuti.

La guida tecnica segnala che il servizio può essere lento e che il filtro `endPeriod` ha un bug noto; lo script applica il workaround documentato. Il servizio può comunque cambiare schema o comportamento; lo script controlla le colonne minime e si interrompe con un messaggio esplicito se la risposta non è compatibile. Il prototipo salva anche la risposta grezza per rendere verificabili i dati di partenza. La pipeline non genera risposte narrative con AI: è il primo componente di acquisizione e calcolo riproducibile del progetto.
