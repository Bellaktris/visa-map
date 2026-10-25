#!/usr/bin/env python3
"""Build a self-contained visa-requirements map for a USA + Russia + Israel document holder.

Sources (fetched into ./data as raw wikitext):
  * Visa requirements for United States citizens   -> US ordinary passport
  * Visa requirements for Russian citizens         -> RU ordinary passport
  * Visa requirements for Israeli citizens         -> IL darkon (full passport)
  * hand-built LP layer                            -> IL teudat ma'avar (laissez-passer)
"""
import json, re, pathlib, datetime

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"

# (file, first line of section, line after section) for the sovereign-state table
SOVEREIGN = {
    "US": ("Visa_requirements_for_United_States_citizens.wiki", 21, 1564),
    "RU": ("Visa_requirements_for_Russian_citizens.wiki", 178, 1515),
    "IL": ("Visa_requirements_for_Israeli_citizens.wiki", 50, 1369),
}
# ...and for the dependent / disputed / unrecognised territories tables. The Israeli
# article puts Taiwan, Kosovo, Palestine, N. Cyprus and Somaliland in a separate
# "Unrecognised or partially recognised countries" table at 1405, so start there.
TERRITORY = {
    "US": ("Visa_requirements_for_United_States_citizens.wiki", 1564, 2063),
    "RU": ("Visa_requirements_for_Russian_citizens.wiki", 1515, 1821),
    "IL": ("Visa_requirements_for_Israeli_citizens.wiki", 1405, 1797),
}

# best -> worst. "freedom of movement" folds into visa_free: it is visa-free plus
# residence rights, and a 6th ordinal step will not fit the light ramp's dL floor.
ORDER = ["visa_free", "eta", "voa", "evisa", "visa_required", "refused", "unknown"]
RANK = {c: i for i, c in enumerate(ORDER)}


def clean(s):
    s = re.sub(r"<ref[^>]*?/>", "", s)
    s = re.sub(r"<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\{\{(?:refn|efn|cn|citation needed|sfn|dead link|webarchive)[^{}]*\}\}", "", s, flags=re.I)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s.replace("&nbsp;", " ")).strip()


def categorise(label):
    t = label.lower()
    if any(k in t for k in ("admission refused", "admission restricted", "suspend",
                            "travel restricted", "entry not allowed", "no entry")):
        return "refused"
    if "undefined" in t:
        return "unknown"
    if "visa required" in t or "permit required" in t:
        return "visa_required"       # also covers "Visa required / eVisa (conditional)"
    if "on arrival" in t:
        return "voa"                 # "eVisa / Visa on arrival" -> VOA is the easier path
    if any(k in t for k in ("evisa", "e-visa", "online visa", "e-voa")):
        return "evisa"
    if any(k in t for k in ("electronic travel", "electronic border", "electronic authorization",
                            "electronic authorisation", "visa waiver")) or "eta" in t.split("/")[0].lower().split():
        return "eta"
    if "freedom of movement" in t or "visa not required" in t or "visa-free" in t:
        return "visa_free"
    return "visa_required"


def parse(path, start, end):
    """Pull (country -> status) out of one wikitable section."""
    lines = (DATA / path).read_text(encoding="utf-8").split("\n")[start - 1:end - 1]
    out, i = {}, 0
    while i < len(lines):
        # row label cell: "| {{flag|X}}", '! style="…"|{{flag|X}}', "| colspan=2 | {{flag|X}}",
        # "| {{nowrap|{{flag|X}}}}"
        m = re.match(r"^[|!]\s*(?:(?:[a-z-]+=(?:\"[^\"]*\"|[^|\s]+)\s*)+\|\s*)?"
                     r"(?:\{\{nowrap\|)?\{\{flag(?:country|icon)?\|([^|}]+)", lines[i])
        if not m:
            i += 1
            continue
        country = m.group(1).strip()
        cells, j = [], i + 1
        while j < len(lines) and not lines[j].startswith("|-") and not lines[j].startswith("|}"):
            if lines[j][:1] in "|!":
                cells.append(clean(lines[j]))
            elif cells:
                cells[-1] += " " + clean(lines[j])
            j += 1
        status = cells[0] if cells else ""
        lm = re.match(r"^[|!]\s*\{\{[a-zA-Z0-9 _/-]+\s*\|?(.*?)\}\}", status)
        label = (lm.group(1) if lm else status.lstrip("|! ")).strip()
        label = re.sub(r"^style=[^|]*\|", "", label).strip()
        stay = ""
        if len(cells) > 1:
            stay = re.sub(r'^[|!]\s*(data-sort-value="[^"]*"\s*\|)?\s*', "", cells[1]).strip()
        if label:
            out[country] = {"cat": categorise(label), "label": label, "stay": stay[:44]}
        i = j
    return out


# ── Wikipedia name -> world-atlas (Natural Earth) name ───────────────────────
ALIAS = {
    # sovereign states
    "The Bahamas": "Bahamas", "Cape Verde": "Cabo Verde", "Republic of the Congo": "Congo",
    "Democratic Republic of the Congo": "Dem. Rep. Congo", "Ivory Coast": "Côte d'Ivoire",
    "Czech Republic": "Czechia", "East Timor": "Timor-Leste", "Eswatini": "eSwatini",
    "Federated States of Micronesia": "Micronesia", "Bosnia and Herzegovina": "Bosnia and Herz.",
    "Central African Republic": "Central African Rep.", "Dominican Republic": "Dominican Rep.",
    "Equatorial Guinea": "Eq. Guinea", "Solomon Islands": "Solomon Is.", "South Sudan": "S. Sudan",
    "Sao Tome and Principe": "São Tomé and Principe", "São Tomé and Príncipe": "São Tomé and Principe",
    "United States": "United States of America", "Vatican City": "Vatican",
    "People's Republic of China": "China", "Republic of China": "Taiwan",
    "North Macedonia": "Macedonia", "Western Sahara": "W. Sahara", "Marshall Islands": "Marshall Is.",
    "Antigua and Barbuda": "Antigua and Barb.", "Saint Kitts and Nevis": "St. Kitts and Nevis",
    "Saint Vincent and the Grenadines": "St. Vin. and Gren.", "State of Palestine": "Palestine",
    # dependent / disputed territories
    "British Indian Ocean Territory": "Br. Indian Ocean Ter.", "British Virgin Islands": "British Virgin Is.",
    "Cayman Islands": "Cayman Is.", "Cook Islands": "Cook Is.", "Falkland Islands": "Falkland Is.",
    "Faroe Islands": "Faeroe Is.", "French Polynesia": "Fr. Polynesia", "Macau": "Macao",
    "Northern Cyprus": "N. Cyprus", "Northern Mariana Islands": "N. Mariana Is.",
    "Pitcairn Islands": "Pitcairn Is.", "Turks and Caicos Islands": "Turks and Caicos Is.",
    "U.S. Virgin Islands": "U.S. Virgin Is.", "Åland Islands": "Åland",
    "Sahrawi Arab Democratic Republic": "W. Sahara",
    "Saint Pierre and Miquelon": "St. Pierre and Miquelon", "Wallis and Futuna": "Wallis and Futuna Is.",
    "Saint Barthélemy": "St-Barthélemy", "Saint Martin": "St-Martin",
    "Falkland Islands (Malvinas)": "Falkland Is.",
    "South Georgia and the South Sandwich Islands": "S. Geo. and the Is.",
    "French Southern and Antarctic Lands": "Fr. S. Antarctic Lands",
}

# ── IL laissez-passer (teudat ma'avar) ───────────────────────────────────────
# No Wikipedia table exists for this document, so this layer is assembled by hand
# at three confidence levels, which the map renders and labels differently:
#
#   "official"  official or encyclopedic sources:
#               [A] en.wikipedia.org/wiki/Israeli_travel_document_in_lieu_of_national_passport
#                   (rev. Aug 2026), itself citing the European Commission's register of
#                   recognised third-country travel documents
#               [B] Henley & Partners Global Mobility Report, Jan 2026 (IATA-derived)
#   "reported"  consumer/immigration-practice compilations of embassy replies:
#               [C] pravoisrael.us  ·  [D] welcome-israel.com (Oct 2025, "61 countries")
#               These two disagree with each other in places; conflicts are flagged.
#   "inferred"  no source at all — derived from the darkon row by LP_RULE below.
LP = {}


def lp(cat, countries, label, conf, src, stay=""):
    for c in countries:
        LP[c] = {"cat": cat, "label": label, "stay": stay, "conf": conf, "src": src}


# -- official ---------------------------------------------------------------
EU_EFTA_SCHENGEN = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", "Estonia",
    "Finland", "France", "Germany", "Greece", "Hungary", "Iceland", "Ireland", "Italy", "Latvia",
    "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Norway", "Poland",
    "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
]
lp("visa_free", EU_EFTA_SCHENGEN, "Visa not required", "official",
   "Recognised for visa-free entry by every EU/EFTA/Schengen state [A]", "90 days / 180")
LP["Malta"]["src"] = "Recognised only since August 2026 [A]"
LP["Ireland"]["src"] = "Visa-free; outside Schengen but recognised [A][B]"
lp("visa_free", ["Russia", "Ukraine", "Japan", "Bosnia and Herzegovina", "Montenegro",
                 "Serbia", "Mexico", "Hong Kong"], "Visa not required", "official",
   "Named as visa-free for this document [A][B]")
lp("visa_free", ["Andorra", "San Marino", "Vatican City"], "Visa not required", "official",
   "No separate border control; entry is via Schengen [A]")
lp("visa_required", ["Canada", "United Kingdom", "United States", "New Zealand", "Australia"],
   "Visa required", "official",
   "Visa-free for the darkon only — the eTA/ETA/ESTA/NZeTA systems reject this document [A][B]")

# -- reported ---------------------------------------------------------------
lp("visa_free", ["Georgia"], "Visa not required", "reported", "Reported visa-free [C][D]", "1 year")
lp("visa_free", ["Singapore"], "Visa not required", "reported",
   "Reported visa-free; SG Arrival Card required 3+ days ahead [C][D]", "30 days")
lp("visa_free", ["Ecuador"], "Visa not required", "reported", "Reported visa-free [C]", "90 days / 180")
lp("visa_free", ["Brazil"], "Visa not required", "reported",
   "Reported visa-free, but acceptance of temporary documents is inconsistent [C]")
lp("visa_free", ["Moldova", "Monaco", "Seychelles", "Fiji", "Turkey", "Egypt", "Mongolia", "Nepal",
                 "Laos", "Lesotho", "eSwatini", "Mauritius", "Mozambique", "Comoros", "Cabo Verde",
                 "Honduras", "Nicaragua", "El Salvador", "Peru", "Bahamas", "Grenada",
                 "St. Kitts and Nevis", "Saint Lucia", "Aruba", "Bermuda", "Isle of Man",
                 "New Caledonia", "Falkland Is."],
   "Visa not required", "reported", "Reported visa-free [D]")
lp("visa_required", ["Argentina", "South Africa"], "Visa required", "reported",
   "Visa-free for the darkon, visa required for this document [C]")
lp("visa_required", ["Paraguay"], "Reported as not accepted for entry", "reported",
   "Reported as not accepted — verify with the embassy [C]")
lp("refused", ["United Arab Emirates"], "Admission refused", "reported",
   "Reported that no visas are issued on this document [C]")
# the two reported sources contradict each other on these four
lp("visa_required", ["Albania", "Belarus", "Costa Rica", "Uruguay"], "Visa required (disputed)",
   "reported", "Sources conflict — [D] lists visa-free, [C] lists visa required. Assume a visa.")

# -- confirmed first-hand by the traveller ----------------------------------
lp("visa_required", ["Taiwan"], "Visa required", "confirmed",
   "Document is accepted and a visa is required — confirmed by the traveller. "
   "Taiwan's visa exemption covers ordinary Israeli passports only.")

# Default rule for every destination with no country-specific source. This is not a
# gap: the Wikipedia table these layers come from states outright that it covers
# "holders of ordinary passports" and that requirements for the Teudat Maavar "may
# vary". Visa exemptions are almost always written for passport holders, so a darkon
# waiver is NOT assumed to carry over; a visa-on-arrival counter generally does accept
# any valid travel document, while eVisa portals generally do not.
LP_RULE = {
    "visa_free": "visa_required", "eta": "visa_required", "evisa": "visa_required",
    "voa": "voa", "visa_required": "visa_required", "refused": "refused", "unknown": "unknown",
}
LP_RULE_NOTE = {
    "visa_free": "No source. The darkon is visa-free here, but waivers are written for passport "
                 "holders — assume a visa is required and confirm with the embassy.",
    "eta": "No source. Electronic authorisation systems generally reject this document.",
    "evisa": "No source. eVisa portals generally require a passport.",
    "voa": "No source. Visa-on-arrival counters generally accept any valid travel document.",
    "visa_required": "No source, but the darkon needs a visa here too.",
    "refused": "No source, but Israeli travel documents are refused here.",
    "unknown": "No source.",
}

# ── assemble ─────────────────────────────────────────────────────────────────
# Join on the Natural Earth name, not the ISO id: five geometries carry no id at all
# (Kosovo, N. Cyprus, Somaliland, …) and Australia shares id 036 with Ashmore and
# Cartier Is., so an id-keyed dict silently loses one of them. Names are unique.
topo = json.loads((ROOT / "vendor" / "countries-50m.json").read_text())
geo_names = [g["properties"]["name"] for g in topo["objects"]["countries"]["geometries"]]
assert len(geo_names) == len(set(geo_names)), "atlas names are not unique"
known = set(geo_names)

sovereign = {k: parse(*v) for k, v in SOVEREIGN.items()}
territory = {k: parse(*v) for k, v in TERRITORY.items()}

layers = {"US": {}, "RU": {}, "IL": {}, "LP": {}}
unmatched = set()


def place(layer, wiki_name, rec):
    key = ALIAS.get(wiki_name, wiki_name)
    if key not in known:
        unmatched.add(wiki_name)
        return
    layers[layer][key] = rec


for doc in ("US", "RU", "IL"):
    for name, rec in sovereign[doc].items():
        place(doc, name, rec)
    for name, rec in territory[doc].items():
        # Skip only rows this same article already covered as a sovereign state — those
        # are the "parent country" group headers. Checking against the union of all three
        # articles would drop e.g. Taiwan from the Russian layer, where it only appears
        # in the territories table.
        if name in sovereign[doc]:
            continue
        place(doc, name, rec)

for name, rec in LP.items():
    place("LP", name, dict(rec))

# home countries
for doc, home in (("US", "United States of America"), ("RU", "Russia"), ("IL", "Israel"), ("LP", "Israel")):
    layers[doc][home] = {"cat": "visa_free", "label": "Home country", "stay": "", "home": True,
                         "conf": "official", "src": ""}

CAT_LABEL = {"visa_free": "Visa not required", "eta": "Travel authorisation",
             "voa": "Visa on arrival", "evisa": "eVisa", "visa_required": "Visa required",
             "refused": "Admission refused", "unknown": "No information"}

# fill the rest of the laissez-passer layer from the darkon row (see LP_RULE)
for name, darkon in layers["IL"].items():
    if name in layers["LP"]:
        continue
    cat = LP_RULE[darkon["cat"]]
    layers["LP"][name] = {
        "cat": cat,
        "label": {"visa_required": "Visa required", "voa": "Visa on arrival",
                  "refused": "Admission refused", "unknown": "No information"}[cat],
        "stay": darkon["stay"] if cat == darkon["cat"] else "",
        "conf": "inferred",
        "src": LP_RULE_NOTE[darkon["cat"]],
    }

# ── ETIAS, modelled as already in force ──────────────────────────────────────
# Not live yet at time of writing; included at the traveller's request so the map
# reflects the world they will actually be planning trips in. ETIAS applies to
# visa-exempt third-country nationals entering the 30 participating states — it does
# NOT cover Ireland (outside Schengen) and it does not replace a visa, so the Russian
# passport is untouched: Russians still need a Schengen visa, not an authorisation.
ETIAS_STATES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia",
    "Finland", "France", "Germany", "Greece", "Hungary", "Iceland", "Italy", "Latvia",
    "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Norway", "Poland",
    "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
]
# For the laissez-passer this is a judgement call. The general rule in LP_RULE says
# electronic authorisation systems reject the document (true of ESTA, eTA, NZeTA, UK
# ETA). But the EU is the one place with specific evidence pointing the other way: the
# European Commission's own register recognises the teudat ma'avar for visa-free entry
# in every member state, and ETIAS keys off visa-exempt *nationality*, not document
# type. Specific evidence beats the general rule, so it gets ETIAS rather than a visa.
etias_applied = []
for name in ETIAS_STATES:
    for doc in ("US", "RU", "IL", "LP"):
        rec = layers[doc].get(name)
        if not rec or rec["cat"] != "visa_free":
            continue  # a visa requirement is not replaced by ETIAS
        rec["cat"] = "eta"
        rec["label"] = "ETIAS"
        rec["stay"] = "90 days / 180"
        note = "ETIAS is modelled here as already in force; it is not yet."
        if doc == "LP":
            note += (" Assumes ETIAS follows the EU register that recognises this document, rather than "
                     "rejecting it the way ESTA, eTA and the UK ETA do — the one place that evidence "
                     "points the other way. If ETIAS turns out to be passport-only, this becomes a visa.")
        rec["src"] = note
        etias_applied.append(f"{doc}/{name}")

# Invariant: the laissez-passer can never beat the darkon. Both identify the holder
# as Israeli and the passport is the stronger document everywhere, so any row claiming
# otherwise is a bad source — the aggregator lists conflate "no visa needed in advance"
# with visa-free. Clamp to the darkon and say so rather than silently trusting it.
clamped = []
for name, lprec in layers["LP"].items():
    darkon = layers["IL"].get(name)
    if not darkon or lprec.get("home") or RANK[lprec["cat"]] >= RANK[darkon["cat"]]:
        continue
    clamped.append(f"{name}: {lprec['cat']} -> {darkon['cat']}")
    lprec["src"] = (f"A source listed this as “{lprec['label'].lower()}”, but the darkon itself only "
                    f"gets {CAT_LABEL[darkon['cat']].lower()} here — a travel document cannot do better "
                    f"than the passport, so it is shown as the darkon's status.")
    lprec["cat"] = darkon["cat"]
    lprec["label"] = CAT_LABEL[darkon["cat"]]
    lprec["stay"] = darkon["stay"]

UNINHABITED = {"Antarctica", "Fr. S. Antarctic Lands", "Heard I. and McDonald Is.",
               "Siachen Glacier", "Ashmore and Cartier Is.", "Indian Ocean Ter."}
countries = {}
for name in geo_names:
    if name in UNINHABITED:
        continue
    docs = {d: layers[d].get(name) for d in ("US", "RU", "IL", "LP")}
    if not any(docs.values()):
        continue
    countries[name] = {"name": name, "docs": {d: v for d, v in docs.items() if v}}

out = {
    "generated": datetime.date.today().isoformat(),
    "order": ORDER,
    "countries": countries,
}
(DATA / "visa.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))

print(f"countries with at least one layer: {len(countries)}")
from collections import Counter
for d in ("US", "RU", "IL", "LP"):
    c = Counter(v["docs"][d]["cat"] for v in countries.values() if d in v["docs"])
    print(f"  {d}: {sum(c.values()):3d} rows  " + "  ".join(f"{k}={c[k]}" for k in ORDER if c[k]))
conf = Counter(v["docs"]["LP"].get("conf") for v in countries.values() if "LP" in v["docs"])
print("  LP confidence:", dict(conf))
print(f"  LP clamped to the darkon in {len(clamped)}: " + "; ".join(clamped))
print(f"  ETIAS applied to {len(etias_applied)} rows across "
      f"{len({e.split('/')[0] for e in etias_applied})} documents")
print("unmatched wiki names:", sorted(unmatched))
no_layer = sorted(n for n in geo_names if n not in countries and n not in UNINHABITED)
print("geometries with no data:", no_layer)
