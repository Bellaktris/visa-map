# Visa requirements by travel document

An interactive world map comparing entry requirements for short tourist visits across
a U.S. passport, a Russian passport, and the two Israeli travel documents — the
*darkon* and the *teudat ma'avar* laissez-passer. Tick the documents a traveller
holds and the map shows the easiest way in to each of 235 destinations.

**[View the map →](https://GITHUB_USER.github.io/REPO_NAME/)**

> **Planning aid, not advice.** The U.S., Russian and Israeli-passport layers come
> from Wikipedia. The laissez-passer layer largely does not — no country-by-country
> source for that document exists, so 142 of its 231 destinations fall back to a
> documented general rule and are drawn with diagonal stripes. Confirm with the
> embassy before booking.

## Two builds

| File | Use |
|---|---|
| `index.html` | What GitHub Pages serves. 37 KB shell + cached `vendor/` assets, so a data update re-fetches ~7 KB rather than 342 KB. Needs http(s) — `fetch` is blocked on `file://`. |
| `visa-map.html` | Everything inlined, 1.16 MB. Open it straight off disk; works offline. |

Both are generated from `template.html` by `assemble.py`.

## What it shows

Four layers, one per travel document:

| Layer | Source |
|---|---|
| U.S. passport | Wikipedia, *Visa requirements for United States citizens* |
| Russian passport | Wikipedia, *Visa requirements for Russian citizens* |
| Israeli passport (*darkon*) | Wikipedia, *Visa requirements for Israeli citizens* |
| Israeli laissez-passer (*teudat ma'avar*) | hand-built — see below |

One control row drives everything: tick the U.S. and/or Russian passport, and pick
**one** Israeli document — laissez-passer, passport, or neither, since you can only
travel on one of them. The map always shows the best option across whatever is
ticked; tick a single document to get a single-document map.

Above the map, **"show where only one document helps"** spotlights the destinations a
given document reaches more easily than any other document ticked: those countries keep
their fill and gain a ring, everything else drops to 20% opacity. Click again to clear.
It appears only when two or more documents are ticked, and clears itself if you untick
the document being spotlit.

Entry requirements are collapsed to five ordered tiers — visa not required, travel
authorisation, visa on arrival, eVisa, visa required — plus *admission refused* and
*no data*. The exact wording from the source is kept and shown in the tooltip and
the table view.

## ETIAS is modelled as already in force

It isn't yet — this is a deliberate assumption, applied in `build.py` via
`ETIAS_STATES`. The 30 participating countries are shown as *travel authorisation*
rather than *visa not required*, for every document that enters them visa-free.

- **Ireland is excluded** — outside Schengen, not an ETIAS country.
- **The Russian passport is untouched** — ETIAS does not replace a visa, and Russians
  need a Schengen visa.
- **The laissez-passer gets ETIAS, not a visa.** This is the one place the general
  rule is overridden. ESTA, the Canadian eTA, NZeTA and the UK ETA all reject the
  teudat ma'avar, so the rule would predict a visa — but the European Commission
  register explicitly recognises the document, and ETIAS keys off visa-exempt
  *nationality* rather than document type. If that turns out to be wrong, those 30
  countries become visa-required, which would gut the document's main advantage.

To go back to the present-day world, empty `ETIAS_STATES` and rerun.

## The laissez-passer layer is approximate

There is no country-by-country table for the *teudat ma'avar*. The Wikipedia article
this project parses says so itself: its table covers "holders of ordinary passports",
and requirements for the Teudat Maavar "may vary". Searching for a per-country source
returns nothing systematic — so this layer is hand-built at four confidence levels,
and the tooltip names which one applies to every country.

| Level | Count | Where it comes from |
|---|---:|---|
| **sourced** | 48 | [Israeli travel document in lieu of national passport](https://en.wikipedia.org/wiki/Israeli_travel_document_in_lieu_of_national_passport) (rev. Aug 2026), citing the European Commission register of recognised third-country travel documents, plus the [Henley Global Mobility Report, Jan 2026](https://www.henleyglobal.com/publications/global-mobility-report/2026-january/one-citizenship-two-travel-documents-israels-distinct-mobility-framework-and-its-global-significance) |
| **confirmed** | 1 | first-hand from the traveller (Taiwan: document accepted, visa required) |
| **reported** | 40 | compilations of embassy replies (`pravoisrael.us`, `welcome-israel.com`). These contradict each other on Albania, Belarus, Costa Rica and Uruguay; resolved pessimistically and flagged as disputed |
| **general rule** | 142 | no country-specific source — derived from the darkon row by `LP_RULE` |

`LP_RULE` is not a shrug, it is the default practice, and it is deliberately
pessimistic:

- a visa waiver written for *passport holders* does **not** carry over to a travel
  document → darkon visa-free / ETA ⇒ **visa required**
- visa-on-arrival counters generally accept any valid travel document → **unchanged**
- eVisa portals generally require a passport → **visa required**

The rule is always applied. These countries are drawn with diagonal stripes over the
fill; the stripe key and the three tier counts live in the collapsed footer, not the
legend, since they qualify one layer's provenance rather than naming a map category.
Those counts are computed from the data at load, so they can't drift from a rebuild.
To see only what is sourced, comment out the `LP_RULE` fill-in loop in `build.py`
and rerun.

To add a country you have confirmed yourself, add it to the `confirmed` block in
`build.py` and rerun — it will leave the striped tier.

### Enforced invariant: the laissez-passer never beats the darkon

Both documents identify the holder as Israeli and the passport is the stronger one
everywhere, so any row claiming otherwise is a bad source — the aggregator lists
conflate "no visa needed in advance" with visa-free. `build.py` clamps those rows to
the darkon's status, prints every clamp, and rewrites the tooltip note to say what
happened. It currently fires on 8 countries, all from the weakest source:

```
Seychelles / Mozambique / St. Kitts and Nevis   visa_free -> eta
Nepal / Laos / Comoros / Cabo Verde             visa_free -> voa
Egypt                                           visa_free -> visa_required
```

Likewise, the spotlight skips each document's own country: a U.S. passport also gets
you into Israel, you simply have to present the Israeli document at the border — a
rule about which document to show, not about where you can go.

## Rebuilding

```sh
# 1. refresh the sources
cd data
for p in Visa_requirements_for_United_States_citizens \
         Visa_requirements_for_Russian_citizens \
         Visa_requirements_for_Israeli_citizens; do
  curl -sL "https://en.wikipedia.org/w/index.php?title=$p&action=raw" -o "$p.wiki"
done

# 2. check the section line-ranges in build.py still match
grep -n '^==' data/*.wiki

# 3. parse + join + emit
python3 build.py      # -> data/visa.json, prints match diagnostics
python3 assemble.py   # -> index.html + visa-map.html
```

`build.py` slices each article by **line range** (`SOVEREIGN` / `TERRITORY` at the
top), so step 2 matters — Wikipedia edits shift those numbers. The script prints
unmatched source rows and uncovered geometries on every run; both lists should stay
small. Country rows join to the atlas on the Natural Earth **name**, not the ISO
numeric id, because five geometries have no id and Australia shares `036` with
Ashmore and Cartier Islands.

## Mobile

Below 680px the controls stack one per line, the search box goes full width, and the
map gets `height: 52vh` instead of following its 2:1 aspect — at full phone width that
would leave it about 170px tall. The projection centres inside the taller box, so the
extra space reads as ocean.

The tooltip can't follow a cursor on touch, so it docks as a bottom sheet: tap a
country to pin it, dismiss with the × , by tapping the ocean, or with Escape. The ×
and the ocean-tap work on desktop too.

Under `@media (hover: none)` the map uses `touch-action: pan-y`, so a one-finger
vertical swipe scrolls the page rather than being swallowed by the map; pinch-zoom and
horizontal drag still pan the map. Trapping the page scroll inside a full-width map is
the more common failure, so this trades one-finger vertical panning away.

## Palette

Ordinal single-hue blue ramp, five steps, validated in both light and dark against
the chart surface (monotone lightness, adjacent ΔL ≥ 0.06, light end ≥ 2:1 contrast).
*Admission refused* uses the reserved critical-status red; *no data* is a neutral
hatch so it can never be mistaken for a ramp step. Because the lightest step sits
below 3:1 against the surface, the table view and the hover tooltip are the required
relief — don't remove them.

## Licence

Code is MIT. `data/visa.json` is a derivative of Wikipedia and is CC BY-SA 4.0 —
reuse must keep the attribution and the share-alike terms. Bundled d3, topojson-client
and world-atlas are ISC. See [LICENSE](LICENSE).

## Contributing a correction

The laissez-passer layer is the weak spot and first-hand reports are the best fix.
If you know a country's actual treatment of the *teudat ma'avar*, add it to the
`confirmed` block in `build.py` and open a PR — that lifts it out of the striped
general-rule tier. Taiwan is already in there as an example.
