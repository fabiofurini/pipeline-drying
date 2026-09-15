# `app` — the web interface

```bash
streamlit run app/streamlit_app.py
```

Opens at http://localhost:8501. Inputs on the left, results on the right.

| File | Role |
|---|---|
| [`streamlit_app.py`](streamlit_app.py) | The whole page: widgets, both engines, charts, cost table |
| [`i18n.py`](i18n.py) | Every visitor-facing string, in English and Italian |

## How it is organised

One script, three parts:

1. **sidebar** — language, process selector, then the input groups. Which
   groups appear depends on the process: the two engines need different data.
2. **dry-air branch** — builds an `AirDryingCaseConfig`, runs it, draws the
   outlet curve, the water inventory, the axial profile, and the cost table.
3. **vacuum branch** — builds a `VacuumDryingCaseConfig`, runs it, draws
   pressure with the soak shaded, the water inventory, the cooling curve, and
   the three dew-point conventions side by side.

Nothing is computed until **Run** is pressed. Streamlit re-runs the whole
script on every widget change, and a dry-air case on a fine grid takes minutes;
recomputing on each keystroke would make the page unusable.

Each engine starts from its own example file. The dry-air example is a 50 km
line — no realistic vacuum spread would dry that in a horizon anyone waits for,
so switching process also switches the defaults.

## Translation

`i18n.py` holds `STRINGS[key][lang]` and two helpers:

- `t(key, lang, **fmt)` — an interface string, falling back to English;
- `warning_text(message, lang)` — translates a warning emitted by an engine,
  matching on a stable fragment of the English text.

That last indirection keeps the engines language-agnostic: they emit English,
and the interface translates at the edge. Solver modules are **not** translated
— they are read by whoever maintains the physics.

To add a language: add its code to `LANGUAGES` and a value under each key. A
missing key falls back to English rather than crashing.

## Performance notes

- Dry-air cost scales steeply with cell count. 60 cells is enough for the
  trends; the interface warns when cells × horizon gets large.
- The vacuum engine solves in well under a second at any setting.
- Comparing several acceptance targets is free: they are crossings of one
  outlet curve, evaluated from a single solve.
