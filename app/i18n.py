"""Interface strings in English and Italian.

The solver modules stay English-only: they are read by whoever maintains the
physics. Only what a visitor sees is translated. `warning_text` additionally
translates the messages the engines emit, matching on a stable fragment of the
English text so the engines need no knowledge of the interface language.
"""
from __future__ import annotations

LANGUAGES = {"English": "en", "Italiano": "it"}

STRINGS: dict[str, dict[str, str]] = {
    # --- chrome -----------------------------------------------------------
    "title": {
        "en": "Pipeline Drying Simulator",
        "it": "Simulatore di asciugatura delle tubazioni"},
    "subtitle": {
        "en": "Dry-air convection and vacuum drying engines - research prototype",
        "it": "Motori di asciugatura ad aria secca e a vuoto - prototipo di ricerca"},
    "language": {"en": "Language", "it": "Lingua"},
    "process": {"en": "Process", "it": "Metodo"},
    "dry_air": {"en": "Dry air", "it": "Aria secca"},
    "vacuum": {"en": "Vacuum", "it": "Vuoto"},
    "run": {"en": "Run simulation", "it": "Avvia simulazione"},
    "running_air": {"en": "Running dry-air drying simulation...",
                    "it": "Simulazione ad aria secca in corso..."},
    "running_vacuum": {"en": "Running vacuum drying simulation...",
                       "it": "Simulazione a vuoto in corso..."},
    "running_detail_air": {
        "en": "Integrating {cells} cells over {hours:g} h of campaign. "
              "A fine grid over a long horizon can take minutes.",
        "it": "Integrazione di {cells} fette su {hours:g} h di campagna. "
              "Una griglia fitta su un orizzonte lungo può richiedere minuti."},
    "running_detail_vacuum": {
        "en": "Integrating the draw-down and soak sequence.",
        "it": "Integrazione della sequenza di discesa e isolamento."},
    "done": {"en": "Done in {seconds:.1f} s", "it": "Completata in {seconds:.1f} s"},
    "idle": {
        "en": "Pick a process, set the inputs on the left and press **Run simulation**.",
        "it": "Scegli il metodo, imposta i dati a sinistra e premi **Avvia simulazione**."},

    # --- section headers --------------------------------------------------
    "h_pipeline": {"en": "1. Pipeline", "it": "1. Tubazione"},
    "h_water": {"en": "2. Initial water", "it": "2. Acqua iniziale"},
    "h_air_equipment": {"en": "3. Dry-air equipment", "it": "3. Impianto aria secca"},
    "h_vac_equipment": {"en": "3. Vacuum equipment", "it": "3. Impianto a vuoto"},
    "h_heat": {"en": "3b. Heat supply", "it": "3b. Apporto di calore"},
    "h_acceptance": {"en": "4. Acceptance", "it": "4. Criterio di accettazione"},
    "h_comparison": {"en": "5. Target comparison", "it": "5. Confronto fra obiettivi"},

    # --- pipeline ---------------------------------------------------------
    "length": {"en": "Length (km)", "it": "Lunghezza (km)"},
    "diameter": {"en": "Internal diameter (mm)", "it": "Diametro interno (mm)"},
    "cells": {"en": "Number of cells", "it": "Numero di fette di calcolo"},
    "cells_help": {
        "en": "How many slices the pipe is divided into. 60 is enough for the "
              "trends; above 100 the answer stops changing and the run gets slow.",
        "it": "In quante fette viene diviso il tubo. 60 bastano per gli andamenti; "
              "oltre 100 il risultato non cambia piu' e il calcolo rallenta."},
    "wall_thickness": {"en": "Wall thickness (mm)", "it": "Spessore della parete (mm)"},
    "wall_thickness_help": {
        "en": "Steel thickness. It sets the heat reserve the evaporating water "
              "draws on, so it matters for vacuum drying.",
        "it": "Spessore dell'acciaio. E' la riserva di calore da cui attinge "
              "l'acqua che evapora, quindi conta nel vuoto."},
    "wall_temp": {"en": "Wall / ambient temperature (C)",
                  "it": "Temperatura del tubo / ambiente (C)"},

    # --- water ------------------------------------------------------------
    "film": {"en": "Equivalent film thickness (micron)",
             "it": "Spessore equivalente del velo d'acqua (micron)"},
    "film_help": {
        "en": "Residual water spread as a film over the whole wall. 30-50 micron "
              "is typical after pigging. This is the most uncertain input of all.",
        "it": "Acqua residua distribuita come velo su tutta la parete. Dopo il "
              "passaggio del pig sono tipici 30-50 micron. E' il dato piu' incerto."},
    "ambient_dew": {"en": "Initial ambient dew point (C)",
                    "it": "Punto di rugiada iniziale dell'aria intrappolata (C)"},
    "trapped": {"en": "Trapped water (% of total)",
                "it": "Acqua in punti nascosti (% del totale)"},
    "trapped_help": {
        "en": "Water in low points, valve cavities and dead legs, where the gas "
              "barely reaches. It drains far more slowly than the film and is "
              "what creates the tail of a campaign. At 0% every acceptance "
              "target costs the same time, which is not what happens in practice.",
        "it": "Acqua in punti bassi, valvole e tratti morti, dove il gas arriva "
              "male. Si libera molto piu' lentamente del velo ed e' cio' che crea "
              "la coda finale. A 0% tutti gli obiettivi costano lo stesso tempo, "
              "cosa che nella realta' non succede."},
    "release": {"en": "Trapped release rate (fraction of film rate)",
                "it": "Velocita' di rilascio (frazione di quella del velo)"},
    "release_help": {
        "en": "Slower is not always longer: water slow enough to go unnoticed at "
              "the outlet lets the line pass its test while still holding water.",
        "it": "Piu' lento non vuol dire sempre piu' lungo: acqua cosi' lenta da "
              "non farsi notare all'uscita fa superare il collaudo con l'acqua "
              "ancora dentro."},

    "trapped_vacuum_note": {
        "en": "Trapped water is modelled in the dry-air engine only. The vacuum "
              "engine still holds all residual water in one inventory, so these "
              "two settings do not apply here.",
        "it": "L'acqua in punti nascosti è modellata solo nel motore ad aria "
              "secca. Il motore a vuoto tiene ancora tutta l'acqua residua in un "
              "unico serbatoio, quindi queste due impostazioni non si applicano."},

    # --- dry-air equipment ------------------------------------------------
    "flow": {"en": "Dry-air flow (Nm3/h)", "it": "Portata d'aria secca (Nm3/h)"},
    "pressure": {"en": "Operating pressure (bar a)", "it": "Pressione di esercizio (bar a)"},
    "inlet_temp": {"en": "Dry-air inlet temperature (C)",
                   "it": "Temperatura dell'aria immessa (C)"},
    "inlet_dew": {"en": "Dryer outlet dew point (C)",
                  "it": "Punto di rugiada in uscita dall'essiccatore (C)"},
    "inlet_dew_help": {
        "en": "The outlet can never be drier than this. A target below it is "
              "unreachable at any flow and any duration.",
        "it": "L'uscita non puo' mai essere piu' secca di questo valore. Un "
              "obiettivo piu' basso e' irraggiungibile, con qualsiasi portata e "
              "qualsiasi durata."},

    # --- vacuum equipment -------------------------------------------------
    "pump_curve_note": {
        "en": "Pump curves are read from examples/literature_vacuum.yaml. Replace "
              "them with real manufacturer data before drawing conclusions.",
        "it": "Le curve delle pompe sono lette da examples/literature_vacuum.yaml. "
              "Vanno sostituite con dati reali del costruttore prima di trarre "
              "conclusioni."},
    "n_pumps": {"en": "Number of pumps", "it": "Numero di pompe"},
    "use_booster": {"en": "Use booster train", "it": "Usa il gruppo booster"},
    "booster_activation": {"en": "Booster activation pressure (mbar)",
                           "it": "Pressione di attivazione del booster (mbar)"},
    "derating": {"en": "Pump derating factor", "it": "Fattore di riduzione resa pompe"},
    "external_temp": {"en": "External temperature (C)", "it": "Temperatura esterna (C)"},
    "u_value": {"en": "Overall U (W/m2K)", "it": "Coefficiente di scambio U (W/m2K)"},
    "u_value_help": {
        "en": "How easily heat reaches the pipe: low if exposed, higher if buried "
              "or submerged. Evaporation needs that heat.",
        "it": "Quanto facilmente il calore raggiunge il tubo: basso se esposto, "
              "piu' alto se interrato o sommerso. L'evaporazione ha bisogno di "
              "quel calore."},

    # --- acceptance -------------------------------------------------------
    "target": {"en": "Target (C)", "it": "Obiettivo (C)"},
    "target_custom": {"en": "custom", "it": "altro"},
    "target_custom_value": {"en": "Custom target (C)", "it": "Obiettivo personalizzato (C)"},
    "hold": {"en": "Hold / soak duration (h)", "it": "Durata del mantenimento (h)"},
    "quoted_atm": {"en": "Target quoted at atmospheric pressure",
                   "it": "Obiettivo riferito alla pressione atmosferica"},
    "quoted_atm_help": {
        "en": "A target read at 1 atm is a weaker requirement than the same number "
              "read at line pressure, because expanding the gas lowers its vapour "
              "partial pressure.",
        "it": "Un obiettivo letto a 1 atm e' meno severo dello stesso numero letto "
              "alla pressione di linea, perche' espandendo il gas la pressione "
              "parziale del vapore diminuisce."},
    "dryer_atm": {"en": "Dryer dew point quoted at atmospheric pressure",
                  "it": "Dato dell'essiccatore riferito alla pressione atmosferica"},
    "dryer_atm_help": {
        "en": "A datasheet '-40 C at atmospheric pressure' is much wetter air once "
              "compressed into the line.",
        "it": "Una scheda tecnica che dice '-40 C a pressione atmosferica' descrive "
              "aria molto piu' umida una volta compressa nella linea."},
    "target_pressure": {"en": "Target pressure (mbar a)", "it": "Pressione obiettivo (mbar a)"},
    "use_frost_target": {"en": "Also require a frost-point target",
                         "it": "Richiedi anche un obiettivo di punto di brina"},
    "frost_target": {"en": "Frost-point target (C)", "it": "Obiettivo di punto di brina (C)"},
    "drawdown": {"en": "Draw-down margin (fraction of target)",
                 "it": "Margine di discesa (frazione dell'obiettivo)"},
    "drawdown_help": {
        "en": "Pumping down to exactly the target always fails the check that "
              "follows, so real procedures over-pump.",
        "it": "Scendere esattamente all'obiettivo fa sempre fallire la verifica "
              "successiva: le procedure reali scendono piu' in basso."},
    "soak": {"en": "Soak duration (h)", "it": "Durata dell'isolamento (h)"},
    "max_rise": {"en": "Max soak pressure rise (mbar)",
                 "it": "Risalita di pressione ammessa (mbar)"},
    "reference_pressure": {"en": "Reference (backfill) pressure (bar a)",
                           "it": "Pressione di riempimento successivo (bar a)"},
    "evaporation_closure": {"en": "Evaporation closure", "it": "Formula di evaporazione"},
    "horizon": {"en": "Simulation horizon (h)", "it": "Orizzonte di simulazione (h)"},

    # --- comparison -------------------------------------------------------
    "compare_targets": {"en": "Compare these targets", "it": "Obiettivi da confrontare"},
    "compare_help": {"en": "All of them are evaluated from the same single simulation.",
                     "it": "Vengono valutati tutti dalla stessa singola simulazione."},
    "energy_price": {"en": "Energy price (EUR/kWh)", "it": "Prezzo dell'energia (EUR/kWh)"},
    "rental": {"en": "Spread rental (EUR/h)", "it": "Noleggio mezzi e personale (EUR/h)"},
    "dryer_energy": {"en": "Dryer regeneration (kWh per 1000 Nm3)",
                     "it": "Consumo dell'essiccatore (kWh ogni 1000 Nm3)"},

    # --- results ----------------------------------------------------------
    "m_time_target": {"en": "Time to target", "it": "Tempo per l'obiettivo"},
    "m_time_acceptance": {"en": "Time to acceptance", "it": "Tempo per l'accettazione"},
    "m_not_reached": {"en": "not reached", "it": "non raggiunto"},
    "m_not_accepted": {"en": "not accepted", "it": "non accettato"},
    "m_outlet_final": {"en": "Outlet dew/frost point (final)",
                       "it": "Umidita' finale in uscita"},
    "m_mass_error": {"en": "Mass-balance error", "it": "Errore di bilancio di massa"},
    "m_final_pressure": {"en": "Final pressure", "it": "Pressione finale"},
    "m_frost_inline": {"en": "In-line frost point", "it": "Punto di brina in linea"},
    "m_min_temp": {"en": "Minimum film temperature",
                   "it": "Temperatura minima dell'acqua"},

    "c_outlet": {"en": "Outlet dew/frost point vs time",
                 "it": "Umidita' in uscita nel tempo"},
    "c_dew_water": {"en": "Dew point (water)", "it": "Punto di rugiada (acqua)"},
    "c_frost_ice": {"en": "Frost point (ice)", "it": "Punto di brina (ghiaccio)"},
    "c_target_line": {"en": "target", "it": "obiettivo"},
    "c_time_h": {"en": "Time (h)", "it": "Tempo (ore)"},
    "c_temp_c": {"en": "Temperature (C)", "it": "Temperatura (C)"},
    "c_liquid": {"en": "Total residual liquid water vs time",
                 "it": "Acqua liquida residua nel tempo"},
    "c_liquid_name": {"en": "Residual liquid water", "it": "Acqua liquida residua"},
    "c_trapped_name": {"en": "of which trapped", "it": "di cui in punti nascosti"},
    "c_kg": {"en": "kg", "it": "kg"},
    "c_axial": {"en": "Axial profile at final time",
                "it": "Distribuzione lungo il tubo alla fine"},
    "c_axial_x": {"en": "Distance along pipeline (km)",
                  "it": "Distanza lungo la tubazione (km)"},
    "c_axial_y": {"en": "kg per cell", "it": "kg per fetta"},
    "c_pressure": {"en": "Pressure vs time (shaded = isolated soak)",
                   "it": "Pressione nel tempo (in ombra = linea isolata)"},
    "c_total_pressure": {"en": "Total pressure", "it": "Pressione totale"},
    "c_vapour_pressure": {"en": "Water vapour partial pressure",
                          "it": "Pressione parziale del vapore"},
    "c_soak": {"en": "Isolated soak", "it": "Linea isolata"},
    "c_pressure_y": {"en": "Pressure (mbar a)", "it": "Pressione (mbar a)"},
    "c_water_inventory": {"en": "Water inventory vs time",
                          "it": "Bilancio dell'acqua nel tempo"},
    "c_removed": {"en": "Water removed by pumps", "it": "Acqua rimossa dalle pompe"},
    "c_cooling": {"en": "Evaporative cooling", "it": "Raffreddamento da evaporazione"},
    "c_film_temp": {"en": "Film / wall temperature",
                    "it": "Temperatura dell'acqua e della parete"},
    "c_freezing": {"en": "freezing", "it": "congelamento"},

    "s_convention": {"en": "Acceptance convention", "it": "Convenzione di misura"},
    "s_convention_note": {
        "en": "The same residual water, quoted three ways. Which one a "
              "specification means is worth settling before the campaign.",
        "it": "La stessa acqua residua, espressa in tre modi. Quale intenda la "
              "specifica conviene chiarirlo prima della campagna."},
    "s_after_backfill": {"en": "Atmospheric, after backfill to {p:g} bar",
                         "it": "Atmosferico, dopo riempimento a {p:g} bar"},
    "s_water_content": {"en": "Water content at that pressure",
                        "it": "Contenuto d'acqua a quella pressione"},
    "s_cost": {"en": "What the acceptance target costs",
               "it": "Quanto costa l'obiettivo richiesto"},
    "s_cost_note": {
        "en": "All rows come from the one simulation above: an acceptance target "
              "is a crossing of the outlet curve, not a separate campaign.",
        "it": "Tutte le righe vengono dalla simulazione qui sopra: un obiettivo e' "
              "un attraversamento della stessa curva, non una campagna a parte."},
    "t_target": {"en": "Target (C)", "it": "Obiettivo (C)"},
    "t_time": {"en": "Time (h)", "it": "Tempo (h)"},
    "t_energy": {"en": "Energy (MWh)", "it": "Energia (MWh)"},
    "t_cost": {"en": "Cost (EUR)", "it": "Costo (EUR)"},
    "t_vs": {"en": "vs loosest", "it": "rispetto al piu' blando"},
    "c_cost_chart": {"en": "Cost of drying further",
                     "it": "Costo di asciugare ulteriormente"},
    "c_cost_y": {"en": "Cost (EUR)", "it": "Costo (EUR)"},
    "s_summary": {"en": "Summary", "it": "Riepilogo"},
    "no_trapped_note": {
        "en": "Trapped water is set to 0%, so the wall film empties all at once "
              "and every target is reached at almost the same moment. Raise it to "
              "see the tail that makes a stricter target cost real time.",
        "it": "L'acqua in punti nascosti e' a 0%, quindi il velo si esaurisce tutto "
              "insieme e ogni obiettivo viene raggiunto quasi nello stesso istante. "
              "Alzala per vedere la coda che rende davvero piu' caro un obiettivo "
              "severo."},
    "slow_warning": {
        "en": "This combination of cells and horizon may take several minutes. "
              "For a quick look, try 60 cells.",
        "it": "Questa combinazione di fette e orizzonte puo' richiedere diversi "
              "minuti. Per una prova rapida usa 60 fette."},

    "process_help": {
        "en": 'Which process to simulate. The two engines need different data, so the fields below change with this choice. Vacuum answers in under a second; dry air takes seconds to minutes.',
        "it": "Quale metodo simulare. I due motori hanno bisogno di dati diversi, quindi i campi qui sotto cambiano con questa scelta. Il vuoto risponde in meno di un secondo, l'aria secca da secondi a minuti."},
    "length_help": {
        "en": 'Length of the section being dried. Together with the diameter it fixes both the wetted area water evaporates from and the gas volume to be flushed.',
        "it": "Lunghezza della tratta da asciugare. Insieme al diametro determina sia la superficie bagnata da cui evapora l'acqua sia il volume di gas da lavare."},
    "diameter_help": {
        "en": 'Internal diameter. Doubling it doubles the wetted area, hence the residual water for a given film thickness, and quadruples the gas volume.',
        "it": "Diametro interno. Raddoppiarlo raddoppia la superficie bagnata, quindi l'acqua residua a parità di spessore del velo, e quadruplica il volume di gas."},
    "wall_temp_help": {
        "en": 'Temperature of the pipe and its surroundings. It sets the saturation pressure at the wall, which is the driving force for evaporation: a colder line dries substantially more slowly.',
        "it": "Temperatura del tubo e di ciò che lo circonda. Determina la pressione di saturazione alla parete, che è la forza motrice dell'evaporazione: una linea più fredda si asciuga molto più lentamente."},
    "ambient_dew_help": {
        "en": 'How wet the air trapped in the line is at the start. It only matters for the first few minutes, until that air is flushed out.',
        "it": "Quanto è umida l'aria intrappolata nella linea all'inizio. Conta solo per i primi minuti, finché quell'aria non viene spazzata via."},
    "flow_help": {
        "en": 'Compressor throughput. Doubling it roughly halves the time but also doubles the power, so the energy used barely changes and only the rental bill falls.',
        "it": "Portata del compressore. Raddoppiarla dimezza all'incirca il tempo ma raddoppia anche la potenza: l'energia consumata cambia poco e a calare è solo il costo di noleggio."},
    "pressure_help": {
        "en": 'Pressure at which the air circulates. At higher pressure the same dew point corresponds to far fewer ppm of water, which is why the reference pressure of the acceptance target matters so much.',
        "it": "Pressione a cui circola l'aria. A pressione più alta lo stesso punto di rugiada corrisponde a molte meno ppm d'acqua: è il motivo per cui la pressione di riferimento dell'obiettivo conta così tanto."},
    "inlet_temp_help": {
        "en": 'Temperature of the air entering the line. It affects compressor power and, mildly, how much moisture the air can carry.',
        "it": "Temperatura dell'aria immessa. Influenza la potenza del compressore e, in misura minore, quanta umidità l'aria può trasportare."},
    "target_help": {
        "en": 'The dryness the client requires, expressed as a dew or frost point. Each 10 °C step down is roughly a factor of three less water allowed.',
        "it": 'La secchezza richiesta dal cliente, espressa come punto di rugiada o di brina. Ogni gradino di 10 °C verso il basso ammette circa tre volte meno acqua.'},
    "target_custom_value_help": {
        "en": 'Any target, if the standard −20 or −30 °C do not apply.',
        "it": 'Un obiettivo qualsiasi, se i valori standard di −20 o −30 °C non si applicano.'},
    "hold_help": {
        "en": 'How long the outlet must stay below the target before it counts as reached. Without a hold, a brief dip during a transient would be enough.',
        "it": "Per quanto tempo l'uscita deve restare sotto l'obiettivo perché sia considerato raggiunto. Senza mantenimento basterebbe un calo momentaneo durante un transitorio."},
    "energy_price_help": {
        "en": 'Electricity tariff, used with the computed compressor power.',
        "it": "Tariffa dell'energia elettrica, usata con la potenza calcolata del compressore."},
    "rental_help": {
        "en": 'All-in hourly rate for equipment and crew. On typical figures this dominates the total, which is what makes shortening the campaign worth paying for.',
        "it": 'Costo orario complessivo di mezzi e personale. Con valori tipici domina il totale: è ciò che rende conveniente pagare per accorciare la campagna.'},
    "dryer_energy_help": {
        "en": 'Regeneration energy of the air dryer, from its datasheet. Left at zero it is simply omitted — it varies tenfold between heatless, heated and blower-purge units, so guessing would be worse than leaving it out.',
        "it": "Energia di rigenerazione dell'essiccatore, dalla sua scheda tecnica. Se resta a zero viene semplicemente omessa: varia di dieci volte fra unità heatless, riscaldate e a blower-purge, quindi tirare a indovinare sarebbe peggio che ometterla."},
    "n_pumps_help": {
        "en": 'Pumps working in parallel. Returns diminish quickly: what matters is capacity at low pressure, which is what a booster provides.',
        "it": 'Pompe in parallelo. I benefici calano in fretta: ciò che conta è la capacità alle basse pressioni, che è quella fornita dal booster.'},
    "use_booster_help": {
        "en": 'A booster train reaches far lower pressures than backing pumps alone. On the example case it saves more time than doubling the number of pumps.',
        "it": 'Un gruppo booster raggiunge pressioni molto più basse delle sole pompe di base. Nel caso di esempio fa guadagnare più tempo che raddoppiare il numero di pompe.'},
    "booster_activation_help": {
        "en": 'Suction pressure at which the booster takes over from the backing pumps.',
        "it": 'Pressione di aspirazione alla quale il booster subentra alle pompe di base.'},
    "derating_help": {
        "en": 'Capacity actually delivered as a fraction of the datasheet curve. Real pumps rarely meet their rating once worn or with leaks in the connection.',
        "it": 'Capacità realmente erogata come frazione della curva di catalogo. Le pompe reali raramente raggiungono il dato nominale, per usura o perdite nei collegamenti.'},
    "external_temp_help": {
        "en": 'Temperature of the ground, sea or air around the line. It is the source of the heat that evaporation consumes.',
        "it": "Temperatura del terreno, del mare o dell'aria attorno alla linea. È la sorgente del calore che l'evaporazione consuma."},
    "target_pressure_help": {
        "en": 'Absolute pressure to reach before isolating the line. Once the line is evacuated it is almost pure water vapour, so this pressure is effectively a dryness target in itself.',
        "it": 'Pressione assoluta da raggiungere prima di isolare la linea. A linea evacuata il gas è quasi solo vapore acqueo, quindi questa pressione è di fatto già un obiettivo di secchezza.'},
    "use_frost_target_help": {
        "en": 'Adds a frost-point requirement on top of the pressure one. Draw-down then continues until whichever of the two binds is satisfied.',
        "it": 'Aggiunge un requisito sul punto di brina oltre a quello di pressione. La discesa prosegue finché non è soddisfatto il più stringente dei due.'},
    "frost_target_help": {
        "en": 'Frost point the residual vapour must reach, measured in the line under vacuum.',
        "it": 'Punto di brina che il vapore residuo deve raggiungere, misurato in linea sotto vuoto.'},
    "soak_help": {
        "en": 'How long the line stays isolated with the pumps off. This is the test itself: water still present reveals itself by pushing the pressure back up.',
        "it": "Per quanto tempo la linea resta isolata con le pompe ferme. È il collaudo vero e proprio: l'acqua ancora presente si rivela facendo risalire la pressione."},
    "max_rise_help": {
        "en": 'Pressure rebound tolerated during the soak. Tighten it and more water must be gone before the line passes.',
        "it": "Risalita di pressione tollerata durante l'isolamento. Restringendola, deve essere stata rimossa più acqua perché la linea superi il collaudo."},
    "reference_pressure_help": {
        "en": 'Pressure the line will be filled to afterwards. Filling with dry gas leaves the water unchanged but dilutes it, so the same residual water reads a very different dew point — which is reported below.',
        "it": "Pressione a cui la linea verrà riempita in seguito. Riempire con gas secco non cambia l'acqua presente ma la diluisce, quindi la stessa acqua residua si legge come un punto di rugiada molto diverso — riportato più sotto."},
    "evaporation_closure_help": {
        "en": 'Which interfacial evaporation law to use. In practice they agree to within 1%, because the pump, not the interface, sets the pace.',
        "it": "Quale legge di evaporazione all'interfaccia usare. In pratica concordano entro l'1%, perché a dettare il ritmo è la pompa, non l'interfaccia."},
    "horizon_help": {
        "en": 'How far ahead to simulate — a limit on the calculation, not a prediction of the duration. If the target is reached earlier the run stops there; if the horizon is too short the answer is "not reached", which means extend it rather than that the target is impossible.',
        "it": 'Fin dove spingere la simulazione: è un limite del calcolo, non una previsione della durata. Se l\'obiettivo viene raggiunto prima, il calcolo si ferma lì; se l\'orizzonte è troppo corto la risposta è "non raggiunto", che significa allungarlo, non che l\'obiettivo sia impossibile.'},

    # --- contact ----------------------------------------------------------
    "contact_header": {
        "en": "Custom versions and optimisation",
        "it": "Versioni personalizzate e ottimizzazione"},
    "contact_text": {
        "en": "This prototype can be tailored to a specific pipeline and "
              "operating context, and extended with an **optimisation layer** "
              "that selects equipment and operating strategy to meet a dryness "
              "target at minimum time or cost — rather than only answering how "
              "long a chosen strategy takes.\n\n"
              "For custom versions, calibration against your own campaign data, "
              "or optimisation features, get in touch:",
        "it": "Questo prototipo può essere adattato a una specifica tubazione e "
              "al suo contesto operativo, ed esteso con un **livello di "
              "ottimizzazione** che sceglie attrezzature e strategia operativa "
              "per raggiungere l'obiettivo di secchezza nel minor tempo o al "
              "minor costo — invece di limitarsi a dire quanto dura una "
              "strategia già scelta.\n\n"
              "Per versioni personalizzate, taratura sui vostri dati di "
              "campagna o funzionalità di ottimizzazione, scrivete a:"},
    "contact_name": {"en": "Fabio Furini", "it": "Fabio Furini"},
    "contact_role": {
        "en": "Professor at Sapienza University of Rome, with a track record of "
              "applied research projects carried out with industry. "
              "Optimisation and decision support are his research area — which "
              "is exactly what the planned optimisation layer draws on.",
        "it": "Professore alla Sapienza Università di Roma, con esperienza di "
              "progetti di ricerca applicata svolti con le aziende. "
              "L'ottimizzazione e il supporto alle decisioni sono il suo ambito "
              "di ricerca, ed è esattamente ciò su cui si basa il livello di "
              "ottimizzazione previsto."},

    # --- about ------------------------------------------------------------
    "about": {"en": "About this tool", "it": "Che cos'e' questo strumento"},
    "about_text": {
        "en": "A research prototype that simulates pipeline drying after "
              "hydrostatic testing, by dry air or by vacuum, and estimates how "
              "long a campaign takes and what it costs. The physics follows "
              "published models; the conservation properties are verified to "
              "round-off. **Nothing here is calibrated against measured data**, "
              "so treat the outputs as physically consistent scenarios rather "
              "than predictions.",
        "it": "Un prototipo di ricerca che simula l'asciugatura di una tubazione "
              "dopo il collaudo idraulico, ad aria secca o a vuoto, e stima quanto "
              "dura una campagna e quanto costa. La fisica segue modelli "
              "pubblicati e i bilanci sono verificati alla precisione di macchina. "
              "**Nulla qui e' tarato su dati misurati**: i risultati vanno letti "
              "come scenari fisicamente coerenti, non come previsioni."},
}

# Engine warnings are produced in English; match a stable fragment.
WARNINGS = [
    ("unreachable at any flow",
     "Uno o piu' obiettivi sono piu' secchi dell'aria prodotta dall'essiccatore: "
     "sono irraggiungibili con qualsiasi portata e durata. Serve un essiccatore "
     "piu' spinto."),
    ("still in the line",
     "Il criterio e' stato soddisfatto con una quantita' non trascurabile di acqua "
     "ancora nella linea: rilascia troppo lentamente per farsi vedere al punto di "
     "misura. Conviene allungare il mantenimento o misurare piu' vicino all'acqua."),
    ("not reached within max_time_s",
     "L'obiettivo non e' stato raggiunto entro l'orizzonte di simulazione: "
     "allunga l'orizzonte o rivedi il dimensionamento dell'impianto."),
    ("not completed within max_time_s",
     "La sequenza di accettazione non e' stata completata entro l'orizzonte di "
     "simulazione: allunga l'orizzonte o rivedi il dimensionamento delle pompe."),
    ("no longer falling",
     "I cicli di pompaggio e isolamento non fanno piu' progressi: il criterio non "
     "e' raggiungibile con questa configurazione di pompe e questo apporto di calore."),
    ("ice forms",
     "Il raffreddamento da evaporazione porta l'acqua sotto zero: si forma "
     "ghiaccio e il modello passa alla sublimazione. Il calore di fusione non e' "
     "modellato, quindi il raffreddamento previsto e' prudenziale."),
    ("Wall temperature below 0 C",
     "Temperatura della parete sotto 0 C: l'equilibrio e' calcolato sulla curva "
     "del ghiaccio."),
    ("max_cycles",
     "Criterio non soddisfatto dopo il numero massimo di cicli di pompaggio e "
     "isolamento consentiti."),
]


def t(key: str, lang: str, **fmt) -> str:
    """Look up an interface string; falls back to English, then to the key."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry["en"]
    return text.format(**fmt) if fmt else text


def warning_text(message: str, lang: str) -> str:
    """Translate an engine warning, keeping the English text as the fallback."""
    if lang == "en":
        return message
    for fragment, italian in WARNINGS:
        if fragment in message:
            return italian
    return message
