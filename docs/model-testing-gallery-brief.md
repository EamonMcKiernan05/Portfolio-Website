# Model testing gallery — dev brief

Rebuild the demo gallery as a model-indexed catalogue of every build, replacing the current
prompt-indexed one.

## What changes

- Page title: **Model testing gallery** (also `<title>`, og:title, h1).
- Cards grouped under **model** headings, not benchmark/prompt headings.
- **One card per build.** No build counts, no "3 builds" cards.
- Each card links to a build page showing the prompt it came from, with the demo runnable.

## Where the files are

`demos/model-testing/<model>/<file>.html` — **19 builds**. Machine-readable inventory:
`docs/model-testing-cards.json` (model, file, rel, kb, title).

Excluded by the owner: everything sitting loose at the root of `Model Testing` (no model folder),
the whole Ripple 65B and ornith-1.5-122b folders, and any build whose prompt cannot be named. That last rule is why the
2026-10-20 MiniMax v2-era runs are absent — cloth-lab, neon-drift, pulse-engine, NOCTURNE (city) and
the first sky-temple were made from the retired v2 prompts.

## Card inventory (19)

| Model | Cards | Builds |
|---|---|---|
| DeepSeek V4.1 Flash | 3 | `THE-CASTLE.html`, `sky-temple-DeepSeek-V4.1-Flash-1017.html`, `test1-deepseek-v4.1-flash-1017.html` (Nightfall — moved here from the MiniMax folder) |
| Qwen 4 Preview | 4 | `medieval-village.html`, `the-pagoda.html`, `torchlight-depths.html`, `liberty-1886.html` |
| Qwen3.8-27B | 4 | `pagoda.html` (DFlash2), `THE-PAGODA.html` (DSpine), `sky-temple.html` (MTP), `pagoda.html` (Plain) — four serving configs |
| Qwen Code (Qwen 4 Max Preview) | 4 | `sky-temple.html`, `medieval-village.html`, `liberty-1886.html`, `lbuild/baseline-gap.html` |
| MiniMax M3.1 Flash | 2 | `sky-temple-minimax-m3-1-flash.html` (v3-era, 21 Oct), `dusk-cityline-minimax-m3.1-flash.html` (v3-era) |
| HY4 | 1 | `THE-CASTLE.html` |
| LongCat 2.5 | 1 | `sky-temple.html` |

## Prompts

`docs/model-testing-prompts.json`:

- `spec_prompts` — the canonical build prompt for the five benchmarks that have session logs:
  castle 4,018 chars, pagoda 4,838, liberty 3,267, village 1,956, torchlight 4,881.
- `sessions` — all 23 live sessions keyed by short id: model, workspace, first prompt, `is_spec`,
  up to six follow-up prompts, counts.

Rules for the prompt block on each build page:

1. Show the **first prompt verbatim**. Never summarise, never reformat, keep escapes intact in a
   scrollable `<pre>`.
2. If the session opened with a fix/iteration instruction rather than a full spec (most Qwen3.8-27B
   runs), show that instruction verbatim and link the base spec underneath.
3. Sessions that began with a "continue this session" wrapper are **follow-up prompts**, not fresh
   builds — label them follow-up. Qwen3.8-27B hit its context limit and was restarted that way;
   five exist.
4. MiniMax builds predate DeepSeek Harness, so they have no session log. Their prompts
   come from the bench prompt pack instead — `docs/model-testing-prompt-pack-v3.md` (v3.4), which
   holds the six tests: Sky Temple, Dusk Cityline, Red Canyon, Cloth Lab, Neon Drift, Pulse Engine.
   Quote the prompt for the matching test. Where the build predates v3.4, say so in the card meta
   ("prompt v3.1" etc.) rather than presenting the current text as the one used.

## Constraints

- No tok/s, no benchmark numbers, no timing claims anywhere.
- Nothing about the inference stack beyond the model name; hardware lives on the portfolio's
  Local AI section.
- Demos are single-file HTML — link them relatively so they work on GitHub Pages.

## Done means

- Page loads at 1440 px and 390 px, cards readable, no horizontal scroll.
- Every one of the 19 cards opens its build page, and the build renders in a real browser with no
  console errors.
- The five old top-level cards (Sky Temple, Living City, Neon Drift, Pulse Engine, Cloth Lab) are
  gone from the gallery. They are Qwen3.8-Flash-Next runs of 4–6 Oct, and their prompts are kept in
  `docs/legacy-gallery.json`. They are not MiniMax builds — the 2026-10-20 MiniMax v2-era files that
  share those prompt names were never in this repo.
