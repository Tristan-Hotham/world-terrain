"""Step 4. Statistics from the zoom 4 grid (land only, weighted by true cell area), the peaks and the cities.

Land: each cell counts by its true area times the share of it that is land in Natural Earth (lakes inside countries count
as land at their surface height; the Caspian Sea is water). A coastal cell's height mixes land and sea floor, so cells that
are not wholly land with wholly-land neighbours are floored at 0 m; only those interior cells can be below sea level.
Antarctica south of 85.05 S (outside Web Mercator) comes from ETOPO10. The Earth curve adds the sea floor (and the polar
caps from ETOPO10) for comparison.
Country and continent medians and shares come from 25 m histograms.
Outputs: WORK/stats.json, data/countries.csv, data/continents.csv, data/hypsometry.csv, data/below_sea_level.csv
Run: python3 code/04_stats.py
"""
import csv
import numpy as np
from scipy import ndimage
from common import *

elev = np.load(f"{WORK}/elev.npy")
lf = np.load(f"{WORK}/landfrac.npy")
ctry = np.load(f"{WORK}/ctry.npy")
fine = np.load(f"{WORK}/ctry_fine.npy")
sub = fine.reshape(N, 2, N, 2).transpose(0, 2, 1, 3).reshape(N, N, 4).copy()
del fine
row_area = np.load(f"{WORK}/row_area.npy")
cap = np.load(f"{WORK}/cap.npz")
C = jload(f"{WORK}/countries.json")
area = (row_area[:, None] * np.ones((1, N))).astype(np.float32)
lat_c = lat_of_row(np.arange(N) + .5)

interior = (lf == 1) & (ndimage.minimum_filter(lf, size=3, mode="wrap") == 1)
land_h = np.where(interior, elev, np.maximum(elev, 0))
W = area * lf
cap_e = cap["elev"].ravel().astype(np.float64); cap_a = cap["area"].ravel()
cap_e = np.maximum(cap_e, 0)

# ---- world land hypsometry, from weighted histograms in 5 m bins ----
HB0, HBW, HNB = -11000.0, 5.0, 4000
hidx = lambda v: np.clip(((np.asarray(v, np.float64) - HB0) / HBW).astype(np.int64), 0, HNB - 1)
lm = lf > 0
hv = land_h[lm]; iv = hidx(hv); wv = W[lm].astype(np.float64)
ant_i = [c["i"] for c in C[1:] if c["a3"] == "ATA"][0]
greenland_i = [c["i"] for c in C[1:] if c["a3"] == "GRL"][0]
ant_frac = ((sub == ant_i).sum(-1) / 4.0)[lm]
gr_frac = ((sub == greenland_i).sum(-1) / 4.0)[lm]
av = area[lm].astype(np.float64)
ci_ = hidx(cap_e)


def H(wts, cap_w):
    return np.bincount(iv, weights=wts, minlength=HNB) + np.bincount(ci_, weights=cap_w, minlength=HNB)


def M(wts, cap_w):
    return float((hv * wts).sum() + (cap_e * cap_w).sum())


lo_edge = HB0 + np.arange(HNB) * HBW


def wq(vals, wts, q):
    o = np.argsort(vals); cw = np.cumsum(wts[o]); return float(vals[o][np.searchsorted(cw, q * cw[-1])])


def hyps(hist, msum):
    tot = hist.sum(); cw = np.cumsum(hist) / tot
    return dict(area_km2=float(tot), mean=msum / tot, median=float(lo_edge[np.searchsorted(cw, .5)] + HBW / 2),
                above={str(t): float(hist[lo_edge >= t].sum() / tot) for t in THRESH}, below0=float(hist[lo_edge < 0].sum() / tot))


z = np.zeros_like(cap_a)
w_ant = av * ant_frac; w_gr = av * gr_frac
hist_w = H(wv, cap_a); hist_noant = H(wv - w_ant, z); hist_ant = H(w_ant, cap_a); hist_noice = H(wv - w_ant - w_gr, z)
world = hyps(hist_w, M(wv, cap_a)); noant = hyps(hist_noant, M(wv - w_ant, z)); antarctica = hyps(hist_ant, M(w_ant, cap_a))
noice = hyps(hist_noice, M(wv - w_ant - w_gr, z))
print("world land: area", round(world["area_km2"] / 1e6, 2), "M km2, mean", round(world["mean"]), "median", round(world["median"]))
print("  above", {k: round(v * 100, 1) for k, v in world["above"].items()})
print("no Antarctica: mean", round(noant["mean"]), {k: round(v * 100, 1) for k, v in noant["above"].items()})
print("Antarctica mean", round(antarctica["mean"]), "no ice sheets mean", round(noice["mean"]))
del ant_frac, gr_frac, av

# curve, every 25 m (land) and the whole Earth (land and sea floor)
abv = lambda hist: 1 - np.concatenate([[0], np.cumsum(hist)])[:-1] / hist.sum()   # share at or above each bin's lower edge
A_w, A_n = abv(hist_w), abv(hist_noant)
curve = [dict(h=int(e), above=float(A_w[int((e - HB0) / HBW)]), above_noant=float(A_n[int((e - HB0) / HBW)])) for e in range(0, 7001, 25)]
# whole Earth surface: grid (sea floor + land heights) plus ETOPO10 above 85.05 N and below 85.05 S
e10 = np.fromfile(ETOPO10, "<i2").reshape(1081, 2161)[:, :2160].astype(np.float64)
lat10 = 90 - np.arange(1081) / 6.0
lo = np.clip(lat10 - 1 / 12, -90, 90); hi = np.clip(lat10 + 1 / 12, -90, 90)
a10 = R_EARTH ** 2 * np.radians(1 / 6) * (np.sin(np.radians(hi)) - np.sin(np.radians(lo)))
polar = np.abs(lat10) > MERC_LAT
hist_e = np.bincount(hidx(e10[polar].ravel()), weights=np.repeat(a10[polar], 2160), minlength=HNB)
esum = float((e10[polar] * a10[polar][:, None]).sum())
for r0 in range(0, N, 512):            # in strips, to keep memory low
    eh = np.where(lm[r0:r0 + 512], land_h[r0:r0 + 512], elev[r0:r0 + 512]).astype(np.float64)
    aw = np.repeat(row_area[r0:r0 + 512, None], N, 1)
    hist_e += np.bincount(hidx(eh).ravel(), weights=aw.ravel(), minlength=HNB); esum += float((eh * aw).sum())
ew = float(hist_e.sum())
A_e = abv(hist_e)
earth_curve = [dict(h=int(e), above=float(A_e[int((e - HB0) / HBW)])) for e in range(-11000, 9001, 100) if e < 9000]
sea = lo_edge < 0
earth = dict(area_km2=ew, above0=float(hist_e[~sea].sum() / hist_e.sum()), mean=esum / ew,
             sea_mean_depth=float(-((lo_edge + HBW / 2) * hist_e)[sea].sum() / hist_e[sea].sum()),
             deepest_cell=float(elev.min()), highest_cell=float(elev.max()))
del eh, aw
import gc; gc.collect()
r, c = np.unravel_index(np.argmax(elev), elev.shape)
earth["highest_cell_at"] = [round(c / N * 360 - 180 + 180 / N, 3), round(float(lat_c[r]), 3)]
r, c = np.unravel_index(np.argmin(elev), elev.shape)
earth["deepest_cell_at"] = [round(c / N * 360 - 180 + 180 / N, 3), round(float(lat_c[r]), 3)]

# ---- countries and continents ----
rows = []
cont = {}
# per country, from the four half-size sub-cells of every grid cell: weighted histograms of height in 25 m bins
NC = len(C); BW = 25.0; B0 = -1000.0; NB = int((9000 - B0) / BW)
hb = np.clip(((land_h - B0) / BW).astype(np.int32), 0, NB - 1).ravel()
qa = (area / 4).ravel().astype(np.float64)
del iv, wv, hv
hist = np.zeros(NC * NB); sw = np.zeros(NC); swh = np.zeros(NC); mx = np.full(NC, -1e9); mn = np.full(NC, 1e9)
lhr = land_h.ravel()
for k in range(4):
    sk = sub[..., k].ravel().astype(np.int32)
    hist += np.bincount(sk * NB + hb, weights=qa, minlength=NC * NB)
    sw += np.bincount(sk, weights=qa, minlength=NC); swh += np.bincount(sk, weights=qa * lhr, minlength=NC)
    np.maximum.at(mx, sk, lhr); np.minimum.at(mn, sk, lhr)
    del sk
hist = hist.reshape(NC, NB)
cells = np.zeros(NC)
for k in range(4):
    cells += np.bincount(sub[..., k].ravel(), minlength=NC) / 4.0
mids = B0 + (np.arange(NB) + .5) * BW
for ci in range(1, NC):
    c = C[ci]
    hh = hist[ci].copy(); a_ = sw[ci]; s_ = swh[ci]; mxc, mnc = mx[ci], mn[ci]
    if c["a3"] == "ATA":
        hh += np.bincount(np.clip(((cap_e - B0) / BW).astype(int), 0, NB - 1), weights=cap_a, minlength=NB)
        a_ += cap_a.sum(); s_ += (cap_e * cap_a).sum(); mxc = max(mxc, cap_e.max())
    if a_ == 0:
        rows.append(dict(iso=c["iso"], a3=c["a3"], name=c["name"], short=c["short"], qid=c["qid"], cont=c["cont"], area=0, cells=0, type=c["type"])); continue
    cw = np.cumsum(hh) / a_
    above = lambda t: float(hh[mids > t].sum() / a_)
    rec = dict(iso=c["iso"], a3=c["a3"], name=c["name"], short=c["short"], qid=c["qid"], cont=c["cont"], area=float(a_), cells=float(cells[ci]),
               mean=float(s_ / a_), median=float(mids[np.searchsorted(cw, .5)]), max_cell=float(mxc), min_cell=float(mnc),
               above1000=above(1000), above2000=above(2000), above3000=above(3000), below0=float(hh[mids < 0].sum() / a_),
               sov=c["sov"], type=c["type"], lon=c["lon"], lat=c["lat"], pop=c["pop"])
    rows.append(rec)
    k = c["cont"] if c["cont"] != "Seven seas (open ocean)" else None
    if k:
        cc = cont.setdefault(k, np.zeros(NB + 2)); cc[:NB] += hh; cc[NB] += a_; cc[NB + 1] += s_
conts = []
for k, cc in cont.items():
    hh = cc[:NB]; a_ = cc[NB]; cw = np.cumsum(hh) / a_
    conts.append(dict(name=k, area=float(a_), mean=float(cc[NB + 1] / a_), median=float(mids[np.searchsorted(cw, .5)]),
                      above1000=float(hh[mids > 1000].sum() / a_), above2000=float(hh[mids > 2000].sum() / a_), above3000=float(hh[mids > 3000].sum() / a_)))
conts.sort(key=lambda d: -d["mean"])
for d in conts:
    print(f"  {d['name']:15s} mean {d['mean']:6.0f}  median {d['median']:6.0f}  >2000 {d['above2000'] * 100:4.1f}%")
# a country is 'well resolved' if it covers at least 100 cells of the zoom 4 grid
for r_ in rows:
    r_["resolved"] = r_.get("cells", 0) >= 100
rank = sorted([r_ for r_ in rows if r_["resolved"] and r_["type"] in ("Sovereign country", "Country") and r_["a3"] != "ATA"], key=lambda d: -d["mean"])
print("highest:", [(d["short"], round(d["mean"])) for d in rank[:10]])
print("lowest:", [(d["short"], round(d["mean"])) for d in rank[-10:]])

# ---- land below sea level: interior land cells under 0 m, grouped into connected patches ----
# Antarctica and Greenland are left out: under their ice shelves and fjords the tiles give sea or bedrock depths
icey = np.isin(ctry, [ant_i, greenland_i])
blw = interior & (elev < 0) & ~icey
lab, nlab = ndimage.label(blw, structure=np.ones((3, 3)))
NAMED = [("Caspian Depression", 44, 58, 36, 49), ("Dead Sea and the Jordan valley", 34.8, 36, 29.5, 33.3), ("Qattara Depression", 24, 30.5, 28, 31),
         ("Turpan Depression", 88, 91, 42, 44), ("Afar and Danakil", 39, 44, 10, 15.5), ("Netherlands polders", 3, 7.5, 51, 54),
         ("Death Valley", -118, -116, 35.5, 37.2), ("Salton Trough", -117, -114.5, 32, 34), ("Kati Thanda-Lake Eyre", 136, 139, -30, -27),
         ("Chott Melrhir", 5, 8, 33, 35), ("Sabkhat Ghuzayyil", 18, 22, 29, 31), ("Akdzhakaya Depression", 57, 60, 39.5, 41.5), ("Laguna del Carbón", -70, -67, -50, -48),
         ("Karagiye Depression", 50.5, 52, 43, 44), ("Bajo del Gualicho", -66, -64.5, -41, -39.8), ("Fayum and Wadi El Rayan", 29.8, 31, 29, 29.8)]
dep = {}
del sub, hist, W
for k, sl in enumerate(ndimage.find_objects(lab), start=1):
    rr, cc = np.where(lab[sl] == k); rr = rr + sl[0].start; cc = cc + sl[1].start
    lon = cc.mean() / N * 360 - 180; lat = float(lat_c[int(rr.mean())])
    nm = next((n for n, x0, x1, y0, y1 in NAMED if x0 <= lon <= x1 and y0 <= lat <= y1), "Elsewhere")
    d = dep.setdefault(nm, dict(name=nm, area=0.0, cells=0, min=0.0, lon=lon, lat=lat))
    a = area[rr, cc].sum(); d["area"] += float(a); d["cells"] += len(rr); d["min"] = min(d["min"], float(elev[rr, cc].min()))
    if a > d.get("_a", 0):
        i = np.argmin(elev[rr, cc]); d["lon"] = round(float(cc[i] / N * 360 - 180 + 180 / N), 3); d["lat"] = round(float(lat_c[rr[i]]), 3); d["_a"] = a
deps = sorted(dep.values(), key=lambda d: -d["area"])
for d in deps: d.pop("_a", None)
below_total = float(sum(d["area"] for d in deps))
print("below sea level:", round(below_total), "km2", [(d["name"], round(d["area"]), d["min"]) for d in deps])
nl = next((r_ for r_ in rows if r_["a3"] == "NLD"), None)
grid_info = dict(cells=N * N, km_equator=40075.017 / N, km_60=40075.017 / N * .5, land_cells=int((lf > 0).sum()), interior_cells=int(interior.sum()))
del lab, blw, icey, interior, land_h, lf, area, lm, hb, qa, lhr
import gc; gc.collect()

# ---- peaks ----
P = jload(f"{WORK}/peaks.json")
PC = jload(f"{WORK}/peak_checks.json")
iso_name = {c["iso"]: c["short"] for c in C[1:]}
iso_cont = {c["iso"]: c["cont"] for c in C[1:]}
# rankings: one entry per summit (items within 3 km of a higher or better-known item, such as Kibo and Kilimanjaro, are folded in)
def dedupe(lst, key, n=3000):
    kept = []
    for o in sorted(lst, key=lambda o: (-key(o), -(o["wp_rank"] is not None), -o["sl"]))[:n]:
        if not o["name"]: continue
        if any(abs(k["lat"] - o["lat"]) < .05 and hav(o["lon"], o["lat"], k["lon"], k["lat"]) < 3 and abs(k["elev"] - o["elev"]) < 60 for k in kept): continue
        kept.append(o)
    return kept


top = dedupe(P[:], lambda o: o["elev"])
top10 = top[:15]
prom = dedupe([o for o in P if o["prom"] and o["prom_src"] == "wikipedia"], lambda o: o["prom"])[:20]     # the curated Wikipedia ranking
hp = {}
for o in P:
    for iso in o["countries"]:
        if iso not in hp or o["elev"] > hp[iso]["elev"]: hp[iso] = o
ok = {c["iso"] for c in PC["hp_check"] if c.get("status") == "agrees"}
hp_rows = []
for iso, o in hp.items():
    hp_rows.append(dict(iso=iso, country=iso_name.get(iso, iso), cont=iso_cont.get(iso), peak=o["name"], qid=o["qid"], elev=o["elev"], lon=o["lon"], lat=o["lat"],
                        verified=iso in ok, shared=len(o["countries"]) > 1))
hp_rows.sort(key=lambda d: -d["elev"])
cont_top = {}
for k in sorted({v for v in iso_cont.values() if v}):
    cands = [o for o in P if any(iso_cont.get(i) == k for i in o["countries"])]
    d = dedupe(cands, lambda o: o["elev"], n=40)
    if d: cont_top[k] = d[0]
print("continent tops:", {k: (v["name"], v["elev"]) for k, v in cont_top.items()})
print("prominent:", [(o["name"], o["prom"]) for o in prom[:8]])

# ---- cities ----
CI = jload(f"{WORK}/cities.json")
pop = np.array([c["pop"] for c in CI]); ce = np.array([c["elev"] for c in CI])
city = dict(n=len(CI), pop=float(pop.sum()),
            share_above={str(t): float(pop[ce > t].sum() / pop.sum()) for t in (500, 1000, 1500, 2000, 2500, 3000)},
            n_above={str(t): int((ce > t).sum()) for t in (1000, 2000, 3000, 4000)},
            pop_above={str(t): float(pop[ce > t].sum()) for t in (1000, 2000, 3000)},
            median_person=wq(ce.astype(float), pop, .5), mean_person=float((ce * pop).sum() / pop.sum()),
            below0=[c for c in CI if c["elev"] < 0])
# Chinese prefecture-level 'cities' carry the population of a whole prefecture in Wikidata, so for the million-plus ranking a
# Chinese city counts only if Natural Earth's urban population (pop_max) of the same place, within 30 km, is a million or more
import unicodedata
nrm = lambda x: "".join(ch for ch in unicodedata.normalize("NFKD", x.lower()) if not unicodedata.combining(ch)).replace(" city", "").replace("'", "").strip()
NEP = [(f["properties"]["name"], f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1], f["properties"]["pop_max"] or 0)
       for f in jload(f"{GEO}/ne_10m_populated_places_simple.geojson")["features"] if f["properties"]["adm0_a3"] in ("CHN", "TWN", "HKG", "MAC")]
def urban(c):
    if c["iso"] != "CHN": return c["pop"]
    m = [p for p in NEP if abs(p[2] - c["lat"]) < .4 and hav(p[1], p[2], c["lon"], c["lat"]) < 30 and nrm(p[0]) == nrm(c["name"])]
    return max([p[3] for p in m], default=0)
for c in CI:
    if c["pop"] >= 1e6: c["urban"] = urban(c)
excl = [c for c in CI if c["pop"] >= 1e6 and c["urban"] < 1e6]
big = sorted([dict(c, pop=c["urban"], pop_src="Natural Earth urban area" if c["iso"] == "CHN" else "Wikidata") for c in CI if c["pop"] >= 1e6 and c["urban"] >= 1e6], key=lambda c: -c["elev"])
city["n_prefecture_excluded"] = len(excl)
print("million-plus Chinese 'cities' left out of the ranking:", len(excl), sorted([(c["name"], c["elev"]) for c in excl], key=lambda x: -x[1])[:8])
mid = sorted([c for c in CI if c["pop"] >= 1e5], key=lambda c: -c["elev"])
city["n_million"] = len(big)
city["top_million"] = big[:15]; city["top_100k"] = mid[:20]
city["lowest_100k"] = sorted([c for c in CI if c["pop"] >= 1e5], key=lambda c: c["elev"])[:10]
print("city share above 1000/2000:", round(city["share_above"]["1000"] * 100, 1), round(city["share_above"]["2000"] * 100, 1), "median person", city["median_person"])
# capitals: Natural Earth admin-0 capitals matched to a Wikidata city of the same name within 25 km
PP = jload(f"{GEO}/ne_10m_populated_places_simple.geojson")["features"]
caps = []
for f in PP:
    p = f["properties"]
    if p["adm0cap"] != 1: continue
    lon, lat = f["geometry"]["coordinates"][:2]
    cand = [c for c in CI if abs(c["lat"] - lat) < .3 and hav(lon, lat, c["lon"], c["lat"]) < 25]
    if not cand: continue
    cand.sort(key=lambda c: (c["name"] != p["name"], -c["pop"]))
    c = cand[0]
    caps.append(dict(name=p["name"], country=p["adm0name"], elev=c["elev"], pop=c["pop"], qid=c["qid"], lon=lon, lat=lat))
caps.sort(key=lambda d: -d["elev"])
city["capitals_top"] = caps[:12]; city["n_capitals"] = len(caps)
print("highest capitals:", [(d["name"], d["elev"]) for d in caps[:8]])

S = dict(world=world, noant=noant, noice=noice, antarctica=antarctica, earth=earth, curve=curve, earth_curve=earth_curve, continents=conts,
         countries=rows, rank_high=[d["a3"] for d in rank[:15]], rank_low=[d["a3"] for d in rank[-15:][::-1]], n_ranked=len(rank),
         below=dict(total=below_total, named=float(sum(d["area"] for d in deps if d["name"] != "Elsewhere")), n_patches=int(nlab), groups=deps, nl_share=nl["below0"] if nl else None, nl_cells=nl["cells"] if nl else None),
         peaks=dict(n=len(P), top=top10, prominent=prom, hp=hp_rows, cont_top=cont_top), cities=city,
         grid=grid_info)
jsave(S, f"{WORK}/stats.json")

with open(f"{DATA}/countries.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f)
    wr.writerow(["iso3", "name", "wikidata", "continent", "land_area_km2", "grid_cells", "well_resolved", "mean_elevation_m", "median_elevation_m",
                 "highest_cell_m", "lowest_cell_m", "share_above_1000m", "share_above_2000m", "share_above_3000m", "share_below_0m",
                 "highest_peak", "highest_peak_wikidata", "highest_peak_m", "high_point_confirmed"])
    hpd = {d["iso"]: d for d in hp_rows}
    for d in sorted(rows, key=lambda d: d["name"]):
        if not d.get("area"): continue
        p = hpd.get(d["iso"], {})
        wr.writerow([d["iso"], dash(d["name"]), d["qid"], d["cont"], round(d["area"]), round(d["cells"], 1), int(d["resolved"]), round(d["mean"]), round(d["median"]),
                     round(d["max_cell"]), round(d["min_cell"]), round(d["above1000"], 4), round(d["above2000"], 4), round(d["above3000"], 4), round(d["below0"], 4),
                     dash(p.get("peak", "")), p.get("qid", ""), p.get("elev", ""), int(bool(p.get("verified")))])
with open(f"{DATA}/continents.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f); wr.writerow(["continent", "land_area_km2", "mean_elevation_m", "median_elevation_m", "share_above_1000m", "share_above_2000m", "share_above_3000m"])
    for d in conts:
        wr.writerow([d["name"], round(d["area"]), round(d["mean"]), round(d["median"]), round(d["above1000"], 4), round(d["above2000"], 4), round(d["above3000"], 4)])
with open(f"{DATA}/hypsometry.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f); wr.writerow(["height_m", "share_of_land_above", "share_of_land_above_excluding_antarctica"])
    for d in curve:
        wr.writerow([d["h"], round(d["above"], 5), round(d["above_noant"], 5)])
with open(f"{DATA}/earth_hypsometry.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f); wr.writerow(["height_m", "share_of_earth_surface_above"])
    for d in earth_curve:
        wr.writerow([d["h"], round(d["above"], 5)])
with open(f"{DATA}/below_sea_level.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f); wr.writerow(["area", "land_below_sea_level_km2", "grid_cells", "lowest_cell_m", "lon", "lat"])
    for d in deps:
        wr.writerow([d["name"], round(d["area"]), d["cells"], round(d["min"]), d["lon"], d["lat"]])
print("earth: above sea level", round(earth["above0"] * 100, 1), "%, mean", round(earth["mean"]), "mean depth", round(earth["sea_mean_depth"]))
