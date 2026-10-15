# One suite, one aesthetic

**Status: adopted.** The laptop-livecam viewer is the authority. Everything
else in the suite — ELE Messenger, the node home page, cambrian-perception's
HUD — takes its surfaces, type and colour from here rather than inventing its
own. Where a project already disagrees, the viewer wins and the project moves.

This is not a style preference written down after the fact. Every rule below
was paid for by a specific failure in this fleet, and the failure is recorded
with it, because a rule without its cause gets "simplified" away.

---

## 0. The one-line version

A machined instrument housing, with engraved labels, backlit glass displays
and lamps that are **only** allowed where something was measured.

---

## 1. Tokens

Lift these by name and value. Do not re-derive them, and do not introduce a
second palette for a second app — an app is identified by its accent, not by
its own colour system.

```css
:root {
  --bg: #111113;  --panel: #1c1c1e;  --panel-2: #242426;
  --border: #38383a;  --border-strong: #48484a;
  --text: #f5f5f7;  --text-dim: #98989d;
  --text-muted: #6e6e73;      /* DECORATION ONLY -- 3.36:1, fails as text */
  --text-dim-bg: #98989d;     /* small text on --bg, not on a panel */
  --accent: #0a84ff;          /* ELE Messenger */
  --success: #30d158;         /* laptop-livecam */
  --danger: #ff453a;  --warn: #ff9f0a;
  --radius: 12px;  --radius-sm: 8px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
html[data-theme="light"] {       /* Solarized, throughout */
  --bg: #e7e6df;  --panel: #fcfbf7;  --panel-2: #f0efe9;
  --border: #dcdad0;  --border-strong: #cbc9bd;
  --text: #073642;  --text-dim: #586e75;
  --text-muted: #93a1a1;      /* 2.58:1 -- decoration only */
  --text-dim-bg: #4e6269;
  --accent: #0a62c9;          /* darkened: #0a84ff is under 3:1 on #fcfbf7 */
  --success: #1b7a46;
}
```

**Measured contrast**, because a palette without ratios is a palette that will
fail somewhere nobody checked:

| token | on `--panel` dark | on `--panel` light |
|---|---|---|
| `--text` | 15.63 | 12.56 |
| `--text-dim` | 5.93 | 5.20 |
| `--accent` | 4.66 | 5.63 |
| `--success` | 8.42 | 5.18 |
| `--text-muted` | **3.36 — fails** | **2.58 — fails** |

`--text-dim` is only **4.30:1 on the light `--bg`**, which is why
`--text-dim-bg` exists: the same text needs a different value depending on
whether it sits on a panel or on the page. `--accent` is 4.25 on `--panel-2`,
so accent text never goes on `--panel-2`.

## 2. Theme

One switch for the whole suite: `localStorage['lightTheme'] === 'true'` sets
`data-theme="light"` on `<html>`. Read it in the `<head>`, before first paint,
or the page flashes the wrong theme on the way in.

Never use `prefers-color-scheme` alone. The home page did, while the viewer
used the switch, so on a light-set browser the two disagreed on every node.
A suite with two theme mechanisms is two products.

## 3. Surfaces

Three, and only three:

- **Housing** — the machined case. `--panel` / `--panel-2`, `--radius`,
  `--shadow`, 1px `--border`. Everything sits in or on it.
- **Glass** (`.vfd`) — a backlit display. `--glass-a`/`--glass-b` gradient
  with `--phos` text. What makes glass read as *lit* is not brightness, it is
  **hue separation**: a near-neutral case around a distinctly warmer, greener
  glow. Matching the housing to the glass kills the effect.
- **Engraving** (`.eng`) — a label cut into the metal: `--emboss` with a light
  shadow above and a dark one below. Engraved text can never light up.

## 4. Type

Monospace throughout. Wide tracking belongs to **labels**; a **name** is a
literal string and gets almost none.

| role | phone | desktop | tracking |
|---|---|---|---|
| node / page name | 34px | 44px | `.04em`, not uppercased |
| caption | 10.5px | — | `.14em` upper |
| section label | 9.5px/700 | — | `.15em` upper |
| field label | 10.5px | — | `.07em` upper |
| field value | 12.5px | 13px | `.02em`, tabular-nums |
| door / card name | 17px | 18px | `.12em` upper |
| body text | 12.5px | 13px | — |

A hostname at `.22em` shreds into loose glyphs. Names are not labels.

## 5. Colour grammar — the rule, not a preference

Three colours, three jobs, and **nothing else on a panel is tinted**:

| | |
|---|---|
| **red** | withdraws a signal — Hide, Stop |
| **amber** | interrupts everyone — BUZZ |
| **green** | opens a channel — CALL |

One tinted key among machined ones is decoration; three keys obeying a stated
grammar is an instrument. That is the whole argument, and it is why a key may
not be coloured just because it feels important.

A `false` that is simply a fact — "this node has no TLS offline" — is **not**
red. Red means concealment here, not badness.

**Per-app accent**, used for identity only (a 3px stripe, a card title), never
as a status colour: laptop-livecam `--success` green, ELE Messenger `--accent`
blue. Cambrian keeps its own HUD state colours (SCAN cyan, TRACK yellow, LOCK
red, SLEEP violet) because those are *in the picture*, not on the housing.

## 6. Lamps, and when you may not use one

A lamp means: **a measured binary stage of a live pipeline**. `--led-on`,
`--led-off`, `--led-bad`, with glow.

You may **not** use a lamp for:

- **provenance** — four provenance states are not four hues of a dot. Use four
  different *media* (see §7).
- **anything not measured now** — `reported` and `unknown` get no lamp at all.
- **non-binary values** — a battery percentage, a byte count, an interface
  name. A lamp beside a number is decoration.
- **non-interactive state**, if you are reaching for `.pinled` — that is a
  *button*. Using it for read-only status is an affordance lie.

> A lamp that cannot fail is indistinguishable from a broken one.

This rule is the fleet's most expensive lesson. A microphone lamp read "ok"
for months while the audible band sat at **-81.9 dB** — an empty jack reading
DC offset, expanded by a normalisation filter until a meter moved.

## 7. Provenance — four media, never four colours

Every measured claim in the suite carries `{value, source}`:

| source | meaning | treatment |
|---|---|---|
| `measured` | probed just now, on this hardware | unmarked — the trustworthy case must not shout |
| `remembered` | measured earlier here, read from disk | dimmed, **and it states its own age** |
| `reported` | the OS says it EXISTS, not that it WORKS | dotted underline — the universal "caveat here" |
| `unknown` | nobody has checked | **no value at all** — print its own `why` string |

`unknown` is never `false`, and an **absent key is `unknown`, never false**.
A grey dot for unknown beside a grey dot for false is the dead-microphone bug
reimplemented in CSS.

**Nothing renders without its age.** `measured` means "measured at
`probed_at`", not "now". A value older than twice its refresh cadence is
stale; well past that, the value is withheld rather than greyed.

**A `note` is part of the value, not metadata.** A battery reading 102% is
shown as `full (sensor reads 102% — calibration drift)`. Clamping it to 100
destroys the evidence that this sensor cannot be trusted the next time it
reads 40.

## 8. Status, never scored

No aggregate health number, no single green/amber/red badge for a node. Any
figure that averages a measured `false` with an `unknown` is a lie with a
decimal point, and a badge would have to choose a colour for "nobody checked".

## 9. The e% rule (already fleet-wide)

HUD cap height = **e% of the displayed picture height**, identical on every
host, with offsets expressed as multiples of cap height rather than pixels.
cambrian's `fishbowl/hud.py` already defers to this and calls it "the
livecam's rule". It stays.

## 10. What this forbids

- A second palette for a second app.
- `prefers-color-scheme` as the theme source.
- A lamp next to anything unmeasured.
- A value shown without its age.
- Grey-for-unknown.
- A health score.
- Red for a `false` that is merely a fact.
