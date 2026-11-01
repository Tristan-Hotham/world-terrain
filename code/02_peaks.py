"""Step 2. Clean the peaks.

Sources, merged by Wikidata item:
  1. Wikidata mountains, hills, summits and volcanoes of every kind (peaks.tsv, paged so nothing is truncated: elevation P2044
     as stated and as normalised to metres, prominence P2660, P625, P17, sitelinks).
  2. Natural Earth 10m elevation points (public domain), fetched from
     https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_geography_regions_elevation_points.geojson
     Used only for summits Wikidata lacks or cannot place, and for a name where Wikidata has no English label.
  3. The 125 most prominent summits from English Wikipedia's 'List of mountain peaks by prominence' (CC BY-SA 4.0),
     as tabulated with Wikidata ids at https://raw.githubusercontent.com/ianto-cannon/ianto-cannon.github.io/master/peaks.js
     Used for the prominence ranking (a curated list) and the same gaps.
Cleaning: collapse duplicate rows (one per country or statement); take the metre value that Wikidata normalised from the
preferred statement, then check every height against the terrain grid around the point, converting values that only make
sense in feet or kilometres (wrong units in Wikidata) and dropping the rest; drop prominences larger than the elevation.
Country: Natural Earth countries within 1 km of the point, plus the Wikidata country (P17) when that country lies
within 25 km, plus the country named in the Wikipedia list.
An independent list of country high points (peakbagger, via
https://raw.githubusercontent.com/jan-mate/peak_capital_distance/master/country_highpoints.csv) is used only to check.
Outputs: data/peaks.csv, WORK/peaks.json, WORK/peak_checks.json
Run: python3 code/02_peaks.py
"""
import csv, re
from collections import defaultdict, Counter
import numpy as np
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from common import *

elev = np.load(f"{WORK}/elev.npy")
C = jload(f"{WORK}/countries.json")
by_qid = {c["qid"]: c for c in C[1:] if c["qid"]}
by_name = {}
for c in C[1:]:
    for k in (c["name"], c["short"]):
        by_name[k.lower()] = c
by_name.update({"usa": by_name["united states"], "china/nepal": None, "south georgia": by_name.get("south georgia and the islands"),
                "timor-leste": by_name.get("timor-leste") or by_name.get("east timor"), "drc": by_name.get("democratic republic of the congo")})
TYPE = {"Q8502": "mountain", "Q54050": "hill", "Q207326": "summit", "Q8072": "volcano"}
FT = 0.3048

# ---- 1. Wikidata ----
rows = tsv(PEAKS)
P = {}
n_rows = len(rows); dropped = Counter()
ranges = {r["m"] for r in rows if r.get("type") == "Q46831"}
for r in rows:
    q = r["m"]
    if q in ranges:
        continue
    p = P.setdefault(q, dict(qid=q, name=r["mL"] or "", elevs=Counter(), raw=None, proms=Counter(), pts=[], p17=set(), types=set(), sl=0, src=set()))
    e = num(r["elev"]); em = num(r.get("elevm")); pr = num(r["prom"]); pt = point(r["coord"])
    if em is not None: p["elevs"][em] += 1
    if e is not None: p["raw"] = e
    if pr is not None: p["proms"][pr] += 1
    if pt and pt not in p["pts"]: p["pts"].append(pt)
    if r["country"]: p["p17"].add(r["country"])
    if r.get("type") in TYPE: p["types"].add(TYPE[r["type"]])
    p["sl"] = max(p["sl"], int(num(r["sl"]) or 0)); p["src"].add("wikidata")
# order each item's metre values: first the one normalised from the preferred (truthy) statement, then the others
for p in P.values():
    e = p["raw"]; vals = [v for v, _ in p["elevs"].most_common()]
    first = None; p["unit"] = "m"
    if e is not None:
        best = None
        for v in vals:
            for k, u in ((1, "m"), (FT, "ft"), (1000, "km")):
                d = abs(v - e * k)
                if d <= max(.6, abs(e * k) * 1e-4) and (best is None or d < best[0]):
                    best = (d, v, u)
        if best: first, p["unit"] = best[1], best[2]
        if first is None and not vals: vals = [e]
    p["order"] = ([first] if first is not None else []) + [v for v in vals if v != first]
dropped["mountain range items"] = len(ranges)
n_wd = len(P)

# ---- 2. Natural Earth elevation points ----
NE = jload(f"{PEAKS_X}/ne_10m_geography_regions_elevation_points.geojson")["features"]
ne_dep = []
n_ne_new = 0
for f in NE:
    pr_ = f["properties"]
    if pr_["featurecla"] == "depression" or (pr_["elevation"] is not None and pr_["elevation"] < 0):
        ne_dep.append(dict(name=pr_["name"], elev=pr_["elevation"], lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1], qid=pr_.get("wikidataid")))
        continue
    if pr_["featurecla"] != "mountain" or not pr_.get("wikidataid") or pr_["elevation"] is None:
        continue
    q = pr_["wikidataid"]
    if q in ranges:
        continue
    if q not in P:
        n_ne_new += 1
        P[q] = dict(qid=q, name=pr_.get("name_en") or pr_["name"], elevs=Counter(), proms=Counter(), pts=[], p17=set(), types={"mountain"}, sl=0, src=set())
    p = P[q]
    p["ne_elev"] = float(pr_["elevation"]); p["ne_pt"] = tuple(f["geometry"]["coordinates"])
    p["ne_name"] = pr_.get("name_en") or pr_["name"]
    p["src"].add("naturalearth")

# ---- 3. Wikipedia: list of peaks by prominence ----
js = open(f"{PEAKS_X}/peaks.js", encoding="utf-8").read()
lines = re.findall(r'^"(.*)",?$', js, re.M)
WP = list(csv.DictReader(lines))
n_wp_new = 0
for i, w in enumerate(WP):
    q = w["wiki"]
    if q not in P:
        n_wp_new += 1
        P[q] = dict(qid=q, name=w["name"], elevs=Counter(), proms=Counter(), pts=[], p17=set(), types={"mountain"}, sl=0, src=set())
    p = P[q]
    p["wp_elev"] = float(w["height"]); p["wp_prom"] = float(w["prominence"]); p["wp_pt"] = (float(w["lon"]), float(w["lat"]))
    p["wp_rank"] = i + 1; p["wp_name"] = w["name"]; p["wp_country"] = w["country"]; p["wp_range"] = w["range"]
    p["src"].add("wikipedia")


# ---- terrain check ----
ctry = np.load(f"{WORK}/ctry.npy")
# highest summit of each continent in Natural Earth's elevation points: no summit may exceed it by more than 50 m
REG = {"Asia": "Asia", "Africa": "Africa", "Europe": "Europe", "North America": "North America", "South America": "South America",
       "Oceania": "Oceania", "Antarctica": "Antarctica"}
CAP = {"world": 0}
for f in NE:
    pr_ = f["properties"]
    if pr_["featurecla"] == "mountain" and pr_["elevation"] and pr_.get("region") in REG:
        CAP[pr_["region"]] = max(CAP.get(pr_["region"], 0), pr_["elevation"] + 50)
        CAP["world"] = max(CAP["world"], pr_["elevation"] + 50)
print("continental caps", CAP)


def window(lon, lat, k=2, raw=False):
    r, c = rc_of(lon, lat); r, c = int(r), int(c) % N
    r0, r1 = max(0, r - k), min(N, r + k + 1)
    cols = [(c + d) % N for d in range(-k, k + 1)]
    w = elev[r0:r1][:, cols]
    if raw:
        return float(w.min())
    return float(elev[r, c]), float(w.max()), max(0.0, float(w.min()))


def excess(e, zc, zmax, zmin):
    """How far a summit height rises above the highest 10 km cell nearby, in units of the local relief (plus 300 m).
    Across 15,000 European summits in Wikidata it is below 0.8 for 99.9% of them. For Natural Earth's 630 named mountains
    (known to be in metres) it is below 1.22 for 95%; the highest values, up to about 4, are small islands."""
    return (e - max(zmax, 0)) / (zmax - zmin + 300)


def low_ok(e, zc, zmax, zmin):
    return e >= min(zc, zmin) - 400 - 0.3 * (zmax - zmin)


def fits(e, zc, zmax, zmin, tight=False):
    return low_ok(e, zc, zmax, zmin) and excess(e, zc, zmax, zmin) <= (1.0 if tight else 3.5)


out = []
flags = Counter()
examples = defaultdict(list)
for q, p in P.items():
    pt = p["pts"][0] if p["pts"] else p.get("wp_pt") or p.get("ne_pt")      # Wikidata, else the Wikipedia list (0.01 degree), else Natural Earth (approximate)
    if not pt:
        flags["no coordinates"] += 1; continue
    lon, lat = pt
    if abs(lat) >= MERC_LAT:
        flags["outside the grid (south of 85 S)"] += 1; continue
    zc, zmax, zmin = window(lon, lat)
    rawmin = window(lon, lat, raw=True)
    ref = p.get("wp_elev") or p.get("ne_elev")             # published lists in metres: a fallback when no Wikidata value fits
    wd = [e for e in p.get("order", []) if e > 0]
    us = "Q30" in p["p17"]
    island = zmax < 600 and rawmin < -50                   # islands: steep peaks over low, partly sea 10 km cells
    # Wikidata's units are known, so a value is read as feet only if it is far beyond anything Natural Earth's named
    # mountains reach (2.7 away from the sea) or above its continent's highest summit: a unit entered wrongly
    k = 3.0
    if island:
        k = 3.5
    r_, c_ = rc_of(lon, lat); cont = C[ctry[int(r_), int(c_) % N]]["cont"] if ctry[int(r_), int(c_) % N] else None
    cap = CAP.get(cont, CAP["world"])
    chosen = None; flag = "ok"
    for e in wd:
        if ref is not None and abs(e - ref) <= 100:
            chosen = (e, "wikidata"); break
        if (excess(e, zc, zmax, zmin) > k or e > cap) and fits(e * FT, zc, zmax, zmin, True) and e * FT >= zc - 200:
            chosen = (round(e * FT, 1), "wikidata"); flag = "converted from feet"; break
        if e > cap:
            continue
        if e < 10 and not low_ok(e, zc, zmax, zmin) and fits(e * 1000, zc, zmax, zmin, True):
            chosen = (e * 1000, "wikidata"); flag = "converted from kilometres"; break
        if fits(e, zc, zmax, zmin):
            chosen = (e, "wikidata"); break
    if chosen is None and ref is not None:
        if fits(ref, zc, zmax, zmin) and ref <= cap:
            chosen = (ref, "wikipedia" if p.get("wp_elev") else "naturalearth")
            if wd: flag = "Wikidata value replaced by published list"
    if chosen is None:
        if not wd and ref is None:
            flags["no positive elevation"] += 1; continue
        flags["elevation does not fit the terrain"] += 1
        examples["mismatch"].append((p["name"], q, (wd or [ref])[0], round(zc), round(zmax)))
        continue
    if flag != "ok":
        flags[flag] += 1; examples[flag].append((p["name"], q, (wd or [ref])[0], chosen[0], round(zc), round(zmax), round(excess((wd or [ref])[0], zc, zmax, zmin), 2), sorted(p["p17"]), sorted(p["types"])))
    if len(p["elevs"]) > 1:
        flags["several Wikidata elevations (preferred one kept if plausible)"] += 1
    if p.get("unit") in ("ft", "km"):
        flags[f"stated in {'feet' if p['unit'] == 'ft' else 'kilometres'} in Wikidata (normalised to metres)"] += 1
    e, esrc = chosen
    prom = None; psrc = None
    for pr_, _ in p["proms"].most_common():
        f_ = FT if p.get("unit") == "ft" else 1000 if p.get("unit") == "km" else 1     # prominence is given in the elevation's unit
        v = pr_ * f_ * (FT if flag == "converted from feet" else 1000 if flag == "converted from kilometres" else 1)
        if 0 < v <= e + 1:
            prom, psrc = round(v, 1), "wikidata"; break
        flags["prominence larger than elevation (dropped)"] += 1
    if "wp_prom" in p:
        prom, psrc = p["wp_prom"], "wikipedia"
    name = p["name"] or p.get("wp_name") or p.get("ne_name") or ""
    out.append(dict(qid=q, name=name, elev=round(e, 1), elev_src=esrc, prom=prom, prom_src=psrc, lon=round(lon, 5), lat=round(lat, 5),
                    types=sorted(p["types"]), sl=p["sl"], src=sorted(p["src"]), flag=flag, z4=round(zc), z4max=round(zmax),
                    island=island, p17=sorted(p["p17"]), wp_country=p.get("wp_country"), wp_rank=p.get("wp_rank"), wp_range=p.get("wp_range")))

# ---- countries ----
geoms = [shape(f["geometry"]).buffer(0) for f in jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]]
tree = STRtree(geoms)
KM = 1 / 111.0
for o in out:
    pt = Point(o["lon"], o["lat"])
    near = set()
    for i in tree.query(pt.buffer(1 * KM / max(.2, np.cos(np.radians(o["lat"]))))):
        if geoms[i].distance(pt) <= 1 * KM / max(.2, np.cos(np.radians(o["lat"]))):
            near.add(C[i + 1]["iso"])
    for q in o["p17"]:
        c = by_qid.get(q)
        if c and geoms[c["i"] - 1].distance(pt) <= 25 * KM / max(.2, np.cos(np.radians(o["lat"]))):
            near.add(c["iso"])
    if o["wp_country"]:
        for nm in o["wp_country"].split("/"):
            c = by_name.get(nm.strip().lower())
            if c: near.add(c["iso"])
    o["countries"] = sorted(near)
    if not near:
        flags["in no country (sea or ice shelf)"] += 1

# ---- independent check of country high points (not redistributed) ----
hp = list(csv.DictReader(open(f"{PEAKS_X}/country_highpoints.csv", encoding="utf-8")))
ALIAS = {"United States": "United States", "Russia": "Russian Federation", "DR Congo": "Democratic Republic of the Congo", "Congo": "Republic of the Congo",
         "Ivory Coast": "Côte d'Ivoire", "Czechia": "Czech Republic", "Eswatini": "Kingdom of eSwatini", "North Macedonia": "North Macedonia",
         "South Korea": "Republic of Korea", "North Korea": "Dem. Rep. Korea", "Laos": "Lao PDR", "Myanmar": "Myanmar", "Vietnam": "Vietnam",
         "Gambia": "The Gambia", "Bahamas": "The Bahamas", "Timor-Leste": "Timor-Leste", "Cape Verde": "Republic of Cabo Verde",
         "São Tomé and Príncipe": "São Tomé and Principe", "Micronesia": "Federated States of Micronesia", "Brunei": "Brunei Darussalam"}
iso_of = {}
for c in C[1:]:
    iso_of.setdefault(c["name"].lower(), c["iso"]); iso_of.setdefault(c["short"].lower(), c["iso"])
REF = {}
for h in hp:
    iso = iso_of.get(ALIAS.get(h["country"], h["country"]).lower())
    if iso and h["elev_m"]:
        REF[iso] = max(REF.get(iso, 0), float(h["elev_m"]))
# a summit away from the coast that is higher than the high point of every country it lies in is an error (mostly feet)
keep = []
for o in out:
    refs = [REF.get(i) for i in o["countries"]]
    if o["countries"] and all(r is not None for r in refs) and not o["island"] and o["elev"] > max(refs) + 30 and "wikipedia" not in o["src"]:
        flags["higher than the country's high point (dropped)"] += 1
        examples["higher than the country's high point"].append((o["name"], o["qid"], o["elev"], o["countries"], max(refs)))
        continue
    keep.append(o)
out = keep
best = {}
for o in out:
    for iso in o["countries"]:
        if iso not in best or o["elev"] > best[iso]["elev"]:
            best[iso] = o
chk = []
for h in hp:
    nm = ALIAS.get(h["country"], h["country"]).lower()
    iso = iso_of.get(nm)
    if not iso:
        chk.append(dict(country=h["country"], status="country not matched")); continue
    ref = float(h["elev_m"]) if h["elev_m"] else None
    b = best.get(iso)
    if not b:
        st = "no peak in the open data"
    elif ref is not None and abs(b["elev"] - ref) <= 30:
        st = "agrees"
    elif ref is not None and b["elev"] < ref - 30:
        st = "open data lacks the high point"
    else:
        st = "open data higher"
    chk.append(dict(country=h["country"], iso=iso, ref_name=h["peak"], ref_elev=ref, ours=b["name"] if b else None, ours_elev=b["elev"] if b else None, status=st))
seen = set(); chk2 = []
for c in chk:
    k = c.get("iso") or c["country"]
    if k in seen: continue
    seen.add(k); chk2.append(c)
st = Counter(c["status"] for c in chk2)
print("high point check:", dict(st))
for c in chk2:
    if c["status"] == "open data higher":
        print("  higher:", c)
for o in out:
    o["verified_hp"] = False
for c in chk2:
    if c["status"] == "agrees":
        best[c["iso"]]["verified_hp"] = True

jsave(out, f"{WORK}/peaks.json")
jsave(dict(n_rows=n_rows, n_wd_items=n_wd, n_ne_new=n_ne_new, n_wp_new=n_wp_new, n_kept=len(out), flags=dict(flags), dropped=dict(dropped),
           examples=dict(examples), hp_check=chk2, hp_status=dict(st), depressions=ne_dep), f"{WORK}/peak_checks.json")
with open(f"{DATA}/peaks.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["wikidata", "name", "elevation_m", "elevation_source", "prominence_m", "prominence_source", "lon", "lat", "countries", "kind", "sitelinks",
                "sources", "check", "grid_cell_m", "grid_max_5x5_m"])
    for o in sorted(out, key=lambda o: -o["elev"]):
        w.writerow([o["qid"], dash(o["name"]), o["elev"], o["elev_src"], o["prom"] if o["prom"] is not None else "", o["prom_src"] or "", o["lon"], o["lat"],
                    " ".join(o["countries"]), "/".join(o["types"]), o["sl"], "+".join(o["src"]), o["flag"], o["z4"], o["z4max"]])
print("rows", n_rows, "wikidata items", n_wd, "+NE", n_ne_new, "+WP", n_wp_new, "kept", len(out))
print(dict(flags))
for k, v in examples.items():
    print(k, v[:12])
