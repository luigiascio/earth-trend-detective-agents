# Earth Trend Detective

**NASA Space Apps Challenge 2026 · Challenge: _Be An Earth System Trend Detective!_**

Ask a question in plain language about climate trends in **Italy**, such as _"Are the Alps
warming faster than Sicily?"_ or _"Where in Italy has rainfall changed significantly?"_.
Earth Trend Detective then:

1. **selects** the variables, places and period that answer it (NASA POWER temperature and
   precipitation);
2. **downloads** the NASA data and **tests** each series for a trend: how big it is, in which
   direction, and whether it is **statistically significant**;
3. **shows** the series with the trend line and its confidence band;
4. **explains** the result in words, after an automatic **guardrail** has checked every
   statement against the computed numbers.

> **Rule number one: the AI decides and explains, the code computes.**
> The language model never writes a number. It writes placeholders such as
> `[napoli.T2M.slope_per_decade]`, and code fills them in with the computed values.
> A deterministic checker then rejects any explanation that contradicts the statistics:
> for example "stable" for a non-significant trend, or "faster" when the confidence
> intervals overlap.

## Why

The challenge asks for a tool that finds **what** is changing, **where**, **by how much**,
and whether the change is **significant** in the scientific sense. Language models are good
at understanding questions and writing clear answers, but they invent and round numbers, and
they over-interpret statistics. This project keeps each part where it is reliable:

| Step | Who does it | Why |
| --- | --- | --- |
| Understand the question, choose zones, variables, period | Gemini (planner) | language understanding, constrained to closed lists |
| Download data, run the trend tests | Python | exact, reproducible, tested |
| Write the explanation | Gemini (explainer) | clear language, but **no digits allowed** |
| Check the explanation against the numbers | Python (guardrail) | deterministic rules, testable |

## How it works

```text
question
   │
   ▼
Planner (Gemini, structured output) ── out of scope? ──► fixed refusal message
   │  plan: [(zone, variable, start_year, end_year), ...]
   ▼
Analysis (Python): NASA POWER download + seasonal Mann-Kendall + Sen slope
   │  results + errors (a failed download does not stop the other analyses)
   ▼
Explainer (Gemini): text with placeholders + structured claims and comparisons
   ▼
Guardrail (Python) ── PASS ──► placeholders filled with the true numbers ──► answer
   │
   ├── RETRY (up to 3 attempts): the list of violations goes back to the explainer
   └── FALLBACK: a fixed template filled with the true numbers
```

The graph is a **Google ADK 2.x `Workflow`** (`src/agents/detective/agent.py`). The route is
enforced by code, so an answer cannot reach the user without passing the guardrail.

### What the guardrail checks (`src/guardrail/checks.py`)

- every placeholder points to a computed result and to an allowed field;
- **no digits** in the text outside placeholders: the model cannot write or round a number;
- the direction stated for each result (increasing / decreasing / no trend) matches the test;
- a zone is called "faster" only if the confidence intervals **do not overlap**, and never
  when two zones share the same grid cell (identical data);
- forbidden phrases: "stable" or "unchanged" for a non-significant trend, and causal claims
  ("due to", "caused by") that the data cannot support.

Every violation is reported to the user in the **Guardrail** tab, together with the raw
explanation and its placeholders.

## Statistics

- **Seasonal Mann-Kendall test** (Hirsch, Slack & Smith, 1982) on monthly data: each month is
  compared only with the same month of other years, so the seasonal cycle does not hide the
  trend. Significance level 0.05.
- **Seasonal Sen slope** (Sen, 1968) with a 95% confidence interval: the median of the
  pairwise slopes, robust to outliers. Reported per decade.
- **Benjamini-Hochberg correction** (1995) for multiple tests: each p-value is corrected
  against all 20 zones for the same variable and period, and significance is decided on the
  corrected **q-value** (false discovery rate 5%). The family is fixed, so a trend gets the
  same verdict whatever else the user asks about.
- At least 10 years of data are required. Missing values are removed and counted, never
  filled in.
- The interpretation rules are written into the explainer and enforced by the guardrail:
  not significant ≠ stable; significant ≠ large; a p-value is not the probability that the
  trend is real; a confidence interval that contains 0 means the direction is uncertain;
  overlapping intervals mean the difference cannot be established.
- Implemented from scratch in `src/stats/` and cross-checked against `pymannkendall` in the
  tests.

### Limitations

- NASA POWER is based on the **MERRA-2 reanalysis**, on a grid of about 0.5° × 0.625°.
  Nearby zones can fall in the same cell: the app detects this and says that their data are
  identical.
- No correction yet for serial correlation between years (Hamed-Rao).
- Confidence intervals are not adjusted for multiple tests: an interval can exclude 0 while the
  q-value is not significant.
- The charts show annual means; the test runs on monthly data. The caption under each chart
  says so.
- Each question is answered on its own: follow-up questions do not use the previous one.

## Data

**NASA POWER** (Prediction Of Worldwide Energy Resources), monthly point API, community
"AG", 1981-2024:

- `T2M`: air temperature at 2 m (°C);
- `PRECTOTCORR`: precipitation, bias-corrected (mm/day).

> These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded
> through the NASA Earth Science/Applied Science Program. <https://power.larc.nasa.gov>

**20 sampling zones: the regional capitals of Italy**, from Aosta and Trento in the Alps to
Palermo and Cagliari on the islands. Coordinates are in `src/agents/tools.py`. The 20 zones
were checked to fall in 20 different MERRA-2 grid cells. The method works for any point on
Earth: NASA POWER is global.

## What it found

1981-2024, seasonal Mann-Kendall test and Sen slope, 95% confidence intervals, significance
on the Benjamini-Hochberg q-value:

- **Temperature is rising significantly in all 20 regional capitals, but not at the same
  rate.** It rises fastest in the north: Bologna **+0.52 °C per decade** [0.42, 0.62], Trento,
  Aosta and Milano about +0.48. It rises slowest in the south and on the islands: Palermo
  **+0.22 °C per decade** [0.15, 0.28]. The intervals do not overlap, so the north-south
  difference is supported by the data.
- **Rainfall shows no significant trend in 19 of 20 capitals.** The exception is **Bologna,
  where it decreases**: -0.12 mm/day per decade [-0.19, -0.05], q = 0.015. Without the
  correction, Bari, L'Aquila and Perugia would also have shown "significant" increases
  (p = 0.015-0.034). After the correction their q-values are 0.15 or more: they are likely
  false discoveries. This is the kind of error the guardrail and the statistics are designed
  to prevent.

## Run it

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), and a Google Cloud project
with the Vertex AI API (`aiplatform.googleapis.com`) enabled.

```bash
git clone https://github.com/luigiascio/hackaton-nasa.git
cd hackaton-nasa/earth-trend-detective
uv sync
gcloud auth application-default login
```

Create `src/agents/detective/.env` (it is git-ignored):

```text
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=<your-project-id>
GOOGLE_CLOUD_LOCATION=global
```

Then start the web app:

```bash
uv run streamlit run app.py          # http://localhost:8501
```

Other ways to run it:

```bash
uv run adk web src/agents            # ADK developer UI, choose "detective"
uv run pytest                        # 115 tests, no network and no LLM needed
```

The model is `gemini-3.8-flash` on location `global` (`src/agents/nodes.py`).

## Project structure

```text
app.py                     Streamlit web app (chat, charts, plan and guardrail tabs)
src/contracts.py           pydantic contracts between nodes (Plan, Explanation, GuardrailReport)
src/agents/nodes.py        graph nodes: planner, analyze, explainer, guardrail, fallbacks
src/agents/detective/      the ADK Workflow (root_agent)
src/agents/tools.py        analyze_trend: zones, variables, download, tests
src/data/power.py          NASA POWER client (cache, retries) and parser
src/stats/                 Mann-Kendall, Sen slope, seasonal versions (pure functions)
src/guardrail/checks.py    deterministic checks and placeholder filling
src/viz/plots.py           trend charts (matplotlib)
tests/                     pytest suite
docs/                      design notes and decision log (in Italian)
```

## Use of AI

AI tools were used in two different ways, and both are declared here as the Space Apps rules
require.

**Inside the product.** Gemini (`gemini-3.8-flash`, Google Vertex AI) is a component of the
app. It plans the analyses and writes the explanation. It never produces numbers, and its
output is checked by deterministic code before it is shown.

**During development.** The author built the project with **Claude Code** (Anthropic) as a
pair-programming assistant:

- **Decided by the author:** the challenge, the idea of an agent system with a numeric
  guardrail, the area (first Campania, then the 20 regional capitals of Italy), the
  correction for multiple tests and the variables, and the main design decisions recorded in
  `docs/decisioni.md`. These include the graph workflow, placeholders instead of numbers,
  the out-of-scope flag, continuing when one analysis fails, and planning every zone the user
  names even when two share a grid cell.
- **Written with the assistant:** a large part of the code, the tests and the documentation
  was written by Claude Code under the author's direction, step by step, as a learning
  exercise. Some parts were written by the author: the data parser logic, the Mann-Kendall S
  statistic and the pairwise slopes. All code was reviewed and run by the author.
- **Checks on AI-written code:** 115 automated tests; the statistics are cross-checked
  against the independent `pymannkendall` package; the agents were tested end to end with
  real questions.

No AI-generated images or videos are used in the app. Any AI-generated media in the demo
carries a visible watermark.

## References

- Hirsch, R. M., Slack, J. R., & Smith, R. A. (1982). Techniques of trend analysis for monthly
  water quality data. _Water Resources Research_, 18(1), 107-121.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau.
  _Journal of the American Statistical Association_, 63(324), 1379-1389.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: a practical and
  powerful approach to multiple testing. _Journal of the Royal Statistical Society B_, 57(1),
  289-300.
- Mann, H. B. (1945). Nonparametric tests against trend. _Econometrica_, 13(3), 245-259.
- Kendall, M. G. (1975). _Rank Correlation Methods_. Griffin, London.
- Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and
  Applications, Version 2 (MERRA-2). _Journal of Climate_, 30(14), 5419-5454.

**Open-source software:** Google Agent Development Kit (`google-adk`), `google-genai`,
Streamlit, pandas, NumPy, SciPy, matplotlib, pydantic, requests, pytest, `pymannkendall`
(tests only), uv.

## License

MIT, see `LICENSE`.
