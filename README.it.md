# Simulatore di asciugatura delle tubazioni

*[English](README.md)*

Un simulatore fisico dell'asciugatura di una tubazione dopo il collaudo
idraulico. Copre entrambi i metodi usati industrialmente — **aria secca** e
**vuoto** — e risponde alla domanda attorno a cui si pianifica una campagna:
quanto tempo serve, e quanto costa?

> **Prototipo di ricerca.** I bilanci sono verificati alla precisione di
> macchina e gli andamenti sono sensati, ma **nulla qui è tarato su dati
> misurati**. I risultati vanno letti come scenari fisicamente coerenti, non
> come previsioni. Vedi le [assunzioni](docs/assumptions.md).

## Per iniziare

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                              # 106 test, circa 2 minuti
streamlit run app/streamlit_app.py  # interfaccia interattiva, italiano / inglese
```

Da codice:

```python
from pipeline_drying import (AirDryingCaseConfig, run_air_drying,
                             CostModel, air_campaign_cost)

cfg = AirDryingCaseConfig.from_yaml("examples/literature_air.yaml")
res = run_air_drying(cfg)

print(res.time_to_target_s / 3600)       # ore per l'obiettivo principale
print(res.additional_target_times_s)     # altri obiettivi, stessa simulazione

cost = air_campaign_cost(cfg, res, CostModel(energy_cost_per_kwh=0.25,
                                             rental_cost_per_hour=150.0))
print(cost.total_cost, cost.energy_kwh)
```

## Che cosa fa

- **Motore ad aria secca** — volumi finiti 1-D, trasporto più evaporazione dalla
  parete con chiusura di Sherwood, temperatura imposta. L'acqua residua è divisa
  fra velo sulle pareti e acqua in punti poco raggiungibili.
- **Motore a vuoto** — bilanci di massa *e di energia*, curve delle pompe
  tabulate con booster, calore latente e congelamento, sequenza di
  discesa/isolamento per il collaudo.
- **Costi di campagna** — potenza di compressori e pompe, energia e noleggio,
  così gli obiettivi si confrontano sul costo e non solo sulla durata.
- **Convenzioni di misura esplicite** — la pressione di riferimento
  dell'obiettivo, quella dell'essiccatore e la convenzione acqua/ghiaccio.
  Ciascuna vale più tempo di campagna della maggior parte delle scelte
  impiantistiche.

## Tre cose che il modello dice

**Dove sta l'acqua conta più di quanta ce n'è.** Spostare il 15% della stessa
acqua residua in punti poco raggiungibili allunga la campagna da 71 a 112 ore,
senza aggiungere un grammo.

**Si può superare il collaudo con la linea ancora bagnata.** Acqua che si libera
abbastanza lentamente non alza mai l'umidità misurata all'uscita quanto basta
per farsi notare. In un caso simulato l'obiettivo di −20 °C è stato raggiunto
con il 73% dell'acqua nascosta ancora presente. Il programma lo segnala.

**La definizione conta più dell'impianto.** Leggere lo stesso −30 °C a pressione
atmosferica invece che a pressione di linea cambia la campagna da 130 a 87 ore:
un terzo del lavoro, deciso da come è scritta la specifica.

## Documentazione

La documentazione tecnica è in inglese, una pagina per argomento:

| | |
|---|---|
| [Indice della documentazione](docs/README.md) | Equazioni, chiusure, assunzioni |
| [Struttura del pacchetto](src/pipeline_drying/README.md) | Cosa fa ogni file e come scorre una simulazione |
| [Interfaccia web](app/README.md) | La pagina Streamlit e come è tradotta |
| [Test](tests/README.md) | Cosa viene verificato, e cosa i test non stabiliscono |
| [Esempi](examples/README.md) | Le due configurazioni pronte all'uso |

Parti dalle [assunzioni](docs/assumptions.md) se devi decidere se fidarti di un
numero, e dalla [verifica](docs/verification.md) se devi decidere se fidarti del
codice.

## Non implementato

Sequenza ibrida aria-vuoto; taratura su campagne misurate; un livello di
ottimizzazione su portata, pressione e scelta dell'impianto; e un modello a
vuoto 1-D con gradiente assiale di pressione — che è la ragione principale per
cui il motore a vuoto non va estrapolato alle tubazioni lunghe.

## Licenza

MIT — vedi [LICENSE](LICENSE).
