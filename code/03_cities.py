"""Step 3. Clean the cities: Wikidata cities of 50,000 or more with an elevation (P2044) and a population (P1082).

- Collapse duplicate rows (one per population figure, point or country): keep the largest population and the point
  whose 10 km grid height is closest to the stated elevation.
- Drop aggregates that would count people twice (metropolitan areas and municipalities, provinces, districts, counties,
  'Greater' areas) and a second item of the same name within 10 km of a larger one.
- Check each elevation against the terrain grid around the point: a city lies between the lowest and highest 10 km cells
  near it, allowing for relief. Values that only fit in feet are converted for US and British items; others are dropped.
Outputs: data/cities.csv, WORK/cities.json
Run: python3 code/03_cities.py
"""
import csv, re
from collections import defaultdict, Counter
import numpy as np
from common import *

elev = np.load(f"{WORK}/elev.npy")
C = jload(f"{WORK}/countries.json")
by_qid = {c["qid"]: c for c in C[1:] if c["qid"]}
ctry = np.load(f"{WORK}/ctry.npy")
FT = 0.3048
AGG = re.compile(r"metropolitan|municipality|province|district|county|greater |\bmetro\b|region|urban area|agglomeration|prefecture|oblast", re.I)

rows = tsv(CITIES)
G = defaultdict(list)
for r in rows:
    G[r["c"]].append(r)


def window(lon, lat, k=1):
    r, c = rc_of(lon, lat); r, c = int(r), int(c) % N
    w = elev[max(0, r - k):r + k + 1][:, [(c + d) % N for d in range(-k, k + 1)]]
    return float(elev[r, c]), float(w.max()), float(w.min()), int(ctry[r, c])


def fits(e, zc, zmax, zmin):
    rel = zmax - max(zmin, 0)
    return max(zmin, 0) - 250 - 0.5 * rel <= e <= zmax + 250 + 0.5 * rel


flags = Counter(); out = []; ex = defaultdict(list)
for q, rs in G.items():
    name = rs[0]["cL"] or q
    if AGG.search(name):
        flags["aggregate area (dropped)"] += 1; continue
    pops = [num(r["pop"]) for r in rs if num(r["pop"])]
    els = sorted({num(r["elev"]) for r in rs if num(r["elev"]) is not None})
    pts = list(dict.fromkeys(point(r["coord"]) for r in rs if point(r["coord"])))
    if not pops or not els or not pts:
        flags["missing value"] += 1; continue
    pop = max(pops)
    best = None
    for pt in pts:
        if abs(pt[1]) >= MERC_LAT: continue
        zc, zmax, zmin, ci = window(*pt)
        for e in els:
            if fits(e, zc, zmax, zmin):
                d = abs(e - zc)
                if best is None or d < best[0]: best = (d, e, pt, zc, ci, "ok")
    feet_ok = any(r["country"] in ("Q30", "Q145") for r in rs)      # feet are only plausible for US and British items
    if best is None and feet_ok:
        for pt in pts:
            zc, zmax, zmin, ci = window(*pt)
            for e in els:
                if fits(e * FT, zc, zmax, zmin) and e * FT > 30:
                    best = (abs(e * FT - zc), round(e * FT), pt, zc, ci, "converted from feet"); break
            if best: break
    if best is None:
        flags["elevation does not fit the terrain (dropped)"] += 1
        ex["mismatch"].append((name, q, els, round(window(*pts[0])[0]), pop)); continue
    if best[5] != "ok":
        flags[best[5]] += 1; ex["feet"].append((name, q, els, best[1], round(best[3])))
    if len(els) > 1: flags["several elevations (the one nearest the grid kept)"] += 1
    if len(pts) > 1: flags["several points (the one nearest the grid kept)"] += 1
    _, e, pt, zc, ci, fl = best
    cq = sorted({r["country"] for r in rs if r["country"]})
    cc = by_qid.get(cq[0]) if cq else None
    iso = C[ci]["iso"] if ci else (cc["iso"] if cc else None)
    out.append(dict(qid=q, name=dash(name), elev=e, pop=pop, lon=round(pt[0], 4), lat=round(pt[1], 4), iso=iso, z4=round(zc), flag=fl))

# same name within 10 km of a larger item: keep the larger
out.sort(key=lambda o: -o["pop"])
keep = []
for o in out:
    dup = any(k["name"] == o["name"] and hav(o["lon"], o["lat"], k["lon"], k["lat"]) < 10 for k in keep[:2000] if abs(k["lat"] - o["lat"]) < .2)
    if dup:
        flags["same name within 10 km of a larger item (dropped)"] += 1; continue
    keep.append(o)
out = keep
cname = {c["iso"]: c["short"] for c in C[1:]}
for o in out:
    o["country"] = cname.get(o["iso"], "")
jsave(out, f"{WORK}/cities.json")
jsave(dict(n_items=len(G), n_rows=len(rows), n_kept=len(out), flags=dict(flags), examples={k: v[:40] for k, v in ex.items()}), f"{WORK}/city_checks.json")
with open(f"{DATA}/cities.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["wikidata", "name", "country", "iso3", "elevation_m", "population", "lon", "lat", "grid_cell_m", "check"])
    for o in out:
        w.writerow([o["qid"], o["name"], o["country"], o["iso"], o["elev"], int(o["pop"]), o["lon"], o["lat"], o["z4"], o["flag"]])
print("items", len(G), "kept", len(out), dict(flags))
for k, v in ex.items():
    print(k, v[:15])
