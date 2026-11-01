"""Step 5. data/results.json (every number quoted anywhere) and the page data in data/page/.
Page files: borders.json (Natural Earth 50m countries, simplified, for borders, the land mask and 'which country'),
peaks.json, cities.json, places.json (Natural Earth populated places for labels), countries.json (per-country figures).
Run: python3 code/05_results.py
"""
import csv
from shapely.geometry import shape, mapping
from common import *

S = jload(f"{WORK}/stats.json")
PC = jload(f"{WORK}/peak_checks.json")
CC = jload(f"{WORK}/city_checks.json")
GM = jload(f"{WORK}/grid_meta.json")
P = jload(f"{WORK}/peaks.json")
CI = jload(f"{WORK}/cities.json")
r1 = lambda x: round(float(x), 1)
r0 = lambda x: int(round(float(x)))
r4 = lambda x: round(float(x), 4)
nm = {d["a3"]: d for d in S["countries"]}
short = lambda d: {"United States of America": "United States", "Russian Federation": "Russia", "Republic of Korea": "South Korea",
                   "Dem. Rep. Korea": "North Korea", "Lao PDR": "Laos", "Kingdom of eSwatini": "Eswatini"}.get(d["name"], d["name"])


def crow(d):
    return dict(a3=d["a3"], iso=d["iso"], name=short(d), cont=d["cont"], mean=r0(d["mean"]), median=r0(d["median"]), max=r0(d["max_cell"]), min=r0(d["min_cell"]),
                area=r0(d["area"]), cells=r1(d["cells"]), above1000=r4(d["above1000"]), above2000=r4(d["above2000"]), above3000=r4(d["above3000"]))


w, na, ant, ni, e = S["world"], S["noant"], S["antarctica"], S["noice"], S["earth"]
above = lambda h: {k: r4(v) for k, v in h["above"].items()}
R = dict(
    meta=dict(slug=SLUG, page=PAGE_URL, repo=REPO, year=2026),
    grid=dict(zoom=Z, px=N, km_equator=r1(S["grid"]["km_equator"]), km_60=r1(S["grid"]["km_60"]), n_spikes=GM["n_spikes"], spike_max=r0(GM["spike_max"]), land_cells=S["grid"]["land_cells"],
              highest_cell=r0(e["highest_cell"]), deepest_cell=r0(e["deepest_cell"])),
    land=dict(area_m=r1(w["area_km2"] / 1e6), mean=r0(w["mean"]), median=r0(w["median"]), above=above(w), below0=r4(w["below0"])),
    noant=dict(area_m=r1(na["area_km2"] / 1e6), mean=r0(na["mean"]), median=r0(na["median"]), above=above(na)),
    antarctica=dict(area_m=r1(ant["area_km2"] / 1e6), mean=r0(ant["mean"]), median=r0(ant["median"]), above=above(ant)),
    noice=dict(mean=r0(ni["mean"]), median=r0(ni["median"]), above=above(ni)),
    earth=dict(above0=r4(e["above0"]), mean=r0(e["mean"]), sea_depth=r0(e["sea_mean_depth"]), area_m=r1(e["area_km2"] / 1e6)),
    continents=[dict(name=d["name"], mean=r0(d["mean"]), median=r0(d["median"]), area_m=r1(d["area"] / 1e6), above1000=r4(d["above1000"]),
                     above2000=r4(d["above2000"]), above3000=r4(d["above3000"])) for d in S["continents"]],
    countries=dict(n_ranked=S["n_ranked"], high=[crow(nm[a]) for a in S["rank_high"][:12]], low=[crow(nm[a]) for a in S["rank_low"][:12]],
                   n_all=len([d for d in S["countries"] if d.get("area")]),
                   pick={a: crow(nm[a]) for a in ("GBR", "CHE", "NPL", "BTN", "TJK", "CHN", "USA", "IND", "NLD", "AUS", "BRA", "RUS", "BOL", "ETH", "LSO", "AND", "GRL", "ATA", "DNK", "BGD", "AFG", "KGZ", "ARM", "RWA", "AUT", "ITA", "FRA", "NOR", "IRL")}),
    below=dict(total=r0(S["below"]["total"]), named=r0(S["below"]["named"]), n_patches=S["below"]["n_patches"],
               groups=[dict(name=d["name"], area=r0(d["area"]), min=r0(d["min"]), lon=d["lon"], lat=d["lat"]) for d in S["below"]["groups"]],
               nl_share=r4(S["below"]["nl_share"])),
)
G = {d["name"]: d for d in R["below"]["groups"]}
R["below"]["g"] = {k: G[v] for k, v in (("caspian", "Caspian Depression"), ("qattara", "Qattara Depression"), ("eyre", "Kati Thanda-Lake Eyre"),
                                         ("nl", "Netherlands polders"), ("afar", "Afar and Danakil"), ("deadsea", "Dead Sea and the Jordan valley"),
                                         ("turpan", "Turpan Depression"), ("death", "Death Valley"), ("salton", "Salton Trough"), ("else", "Elsewhere"))}
R["below"]["caspian_share"] = r4(G["Caspian Depression"]["area"] / S["below"]["total"])
R["below"]["caspian_share_named"] = r4(G["Caspian Depression"]["area"] / S["below"]["named"])

# peaks
pk = S["peaks"]
cn = {d["iso"]: short(d) for d in S["countries"]}
pr = lambda o: dict(name=o["name"], qid=o["qid"], elev=r0(o["elev"]), prom=r0(o["prom"]) if o["prom"] else None, lon=o["lon"], lat=o["lat"],
                    countries=[cn.get(i, i) for i in o["countries"]], iso=o["countries"], range=o.get("wp_range"))
hp = pk["hp"]
hpv = [h for h in hp if h["verified"]]
fl = PC["flags"]
R["peaks"] = dict(n=pk["n"], n_rows=PC["n_rows"], n_wd=PC["n_wd_items"], n_ne=PC["n_ne_new"], n_wp=PC["n_wp_new"],
                  feet=fl.get("converted from feet", 0), km=fl.get("converted from kilometres", 0),
                  dropped=sum(v for k, v in fl.items() if "does not fit" in k or "dropped" in k and "prominence" not in k or "no positive" in k or "no coordinates" in k or "outside" in k),
                  mismatch=fl.get("elevation does not fit the terrain", 0), replaced=fl.get("Wikidata value replaced by published list", 0),
                  ranges=PC["dropped"].get("mountain range items", 0), n_named=len([o for o in P if o["name"]]),
                  top=[pr(o) for o in pk["top"][:12]], prominent=[pr(o) for o in pk["prominent"][:15]],
                  cont_top={k: pr(v) for k, v in pk["cont_top"].items() if k != "Seven seas (open ocean)"},
                  hp_n=len(hp), hp_verified=len(hpv), hp_checked=PC["hp_status"].get("agrees", 0) + PC["hp_status"].get("open data lacks the high point", 0) + PC["hp_status"].get("open data higher", 0) + PC["hp_status"].get("no peak in the open data", 0),
                  hp_status=PC["hp_status"],
                  hp=[dict(country=h["country"], iso=h["iso"], peak=h["name"] if "name" in h else h["peak"], elev=r0(h["elev"]), qid=h["qid"], lon=h["lon"], lat=h["lat"], shared=h["shared"])
                      for h in hpv],
                  n_8000=len([o for o in pk["top"] if o["elev"] >= 8000]))
R["peaks"]["ft_stated"] = fl.get("stated in feet in Wikidata (normalised to metres)", 0)
R["peaks"]["no_coord"] = fl.get("no coordinates", 0)
R["peaks"]["n_top_8000"] = len([o for o in pk["top"] if o["elev"] >= 8000])
R["peaks"]["k2_prom_rank"] = next(o["wp_rank"] for o in P if o["qid"] == "Q43512")
R["peaks"]["hp_countries_over_5000"] = len([h for h in hpv if h["elev"] >= 5000])
R["peaks"]["hp_countries_under_100"] = len([h for h in hpv if h["elev"] < 100])
R["peaks"]["hp_lowest"] = sorted(R["peaks"]["hp"], key=lambda h: h["elev"])[:5]

# cities
c = S["cities"]
cr = lambda o: dict(name=o["name"], country=o["country"], iso=o["iso"], elev=r0(o["elev"]), pop=r0(o["pop"]), lon=o["lon"], lat=o["lat"], qid=o["qid"])
R["cities"] = dict(n=c["n"], pop_bn=round(c["pop"] / 1e9, 2), share_above={k: r4(v) for k, v in c["share_above"].items()}, n_above=c["n_above"],
                   pop_above_m={k: r1(v / 1e6) for k, v in c["pop_above"].items()}, median_person=r0(c["median_person"]), mean_person=r0(c["mean_person"]),
                   n_million=c["n_million"], n_prefecture_excluded=c["n_prefecture_excluded"], top_million=[cr(o) for o in c["top_million"][:12]], top_100k=[cr(o) for o in c["top_100k"][:15]],
                   lowest=[cr(o) for o in c["lowest_100k"][:6]], capitals=[dict(name=d["name"], country=d["country"], elev=r0(d["elev"]), pop=r0(d["pop"])) for d in c["capitals_top"][:10]],
                   n_capitals=c["n_capitals"], n_items=CC["n_items"], dropped=sum(v for k, v in CC["flags"].items() if "dropped" in k), feet=CC["flags"].get("converted from feet", 0))
# population by elevation band
bands = [-100, 0, 250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000]
bp = []
for a, b in zip(bands[:-1], bands[1:]):
    s = [o for o in CI if a <= o["elev"] < b]
    bp.append(dict(lo=a, hi=b, n=len(s), pop_m=r1(sum(o["pop"] for o in s) / 1e6)))
R["cities"]["bands"] = bp
R["cities"]["biggest_above2000"] = [cr(o) for o in sorted([o for o in CI if o["elev"] >= 2000], key=lambda o: -o["pop"])[:5]]
ce_ = [(o["elev"], o["pop"]) for o in CI]; tp = sum(p for _, p in ce_)
R["cities"]["above_curve"] = [[h, r4(sum(p for e_, p in ce_ if e_ >= h) / tp)] for h in range(0, 5001, 100)]
# land area by band, for the same bands (land above sea level)
cv = {d["h"]: d["above"] for d in S["curve"]}
R["land"]["bands"] = [dict(lo=a, hi=b, share=r4(cv.get(max(a, 0), 1) - cv.get(b, 0))) for a, b in zip([0, 250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000], [250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7000])]
# curves, thinned for the page
R["curve"] = [[d["h"], r4(d["above"]), r4(d["above_noant"])] for d in S["curve"] if d["h"] % 50 == 0]
R["earth_curve"] = [[d["h"], r4(d["above"])] for d in S["earth_curve"] if d["h"] % 200 == 0]
# derived ratios quoted in the text
R["derived"] = dict(land_above2000_vs_cities=round(R["land"]["above"]["2000"] / R["cities"]["share_above"]["2000"], 1),
                    land_above1000_vs_cities=round(R["land"]["above"]["1000"] / R["cities"]["share_above"]["1000"], 1),
                    noant_above2000_vs_cities=round(R["noant"]["above"]["2000"] / R["cities"]["share_above"]["2000"], 1),
                    everest_vs_cell=r0(8849 - R["grid"]["highest_cell"]),
                    asia_vs_europe=round(R["continents"][1]["mean"] / [d for d in R["continents"] if d["name"] == "Europe"][0]["mean"], 1))
jsave(R, f"{DATA}/results.json", indent=1)

# ---- page data ----
B = jload(f"{GEO}/ne_50m_admin_0_countries.geojson")["features"]
feats = []
for f in B:
    g = shape(f["geometry"]).simplify(.03, preserve_topology=True)
    gj = mapping(g)

    def rnd(x):
        return [rnd(y) for y in x] if isinstance(x[0], (list, tuple)) else [round(x[0], 3), round(x[1], 3)]
    gj = {"type": gj["type"], "coordinates": rnd(gj["coordinates"])}
    p = f["properties"]
    feats.append({"type": "Feature", "properties": {"a3": p["ADM0_A3"], "n": p["NAME"]}, "geometry": gj})
jsave({"type": "FeatureCollection", "features": feats}, f"{PAGE}/borders.json")
cdat = []
hpd = {h["iso"]: h for h in hp}
for d in S["countries"]:
    if not d.get("area"): continue
    h = hpd.get(d["iso"])
    cdat.append([short(d), d["a3"], r0(d["mean"]), r0(d["median"]), r0(d["max_cell"]), r0(d["area"]), r4(d["above1000"]), r4(d["above2000"]), int(d["resolved"]),
                 d["lat"], d["lon"], h["peak"] if h else "", r0(h["elev"]) if h else None, int(bool(h and h["verified"])), d["cont"], round(d["cells"], 1)])
jsave(cdat, f"{PAGE}/countries.json")
# peaks: [name, lat, lon, elev, prom, iso list, qid, kind, sitelinks, flag, rank] sorted by a display score
kind = lambda t: "v" if "volcano" in t else "h" if t == ["hill"] else "m"
score = lambda o: o["elev"] + 3 * (o["prom"] or 0) + 400 * o["sl"] ** .5 + (20000 if o.get("wp_rank") else 0)
pp = sorted(P, key=lambda o: -score(o))
rowsP = [[o["name"], round(o["lat"], 4), round(o["lon"], 4), r0(o["elev"]), r0(o["prom"]) if o["prom"] else 0, " ".join(o["countries"]), o["qid"], kind(o["types"]),
          o["sl"], {"ok": 0, "converted from feet": 1, "converted from kilometres": 2}.get(o["flag"], 3)] for o in pp]
jsave(rowsP[:15000], f"{PAGE}/peaks.json")          # the 15,000 best known, loaded with the page
jsave(rowsP[15000:], f"{PAGE}/peaks_more.json")     # the rest, loaded when zoomed in or searching
jsave([[o["name"], o["lat"], o["lon"], r0(o["elev"]), r0(o["pop"]), o["country"], o["qid"]] for o in sorted(CI, key=lambda o: -o["pop"])], f"{PAGE}/cities.json")
PPL = jload(f"{GEO}/ne_10m_populated_places_simple.geojson")["features"]
pl = sorted([[f["properties"]["name"], round(f["geometry"]["coordinates"][1], 3), round(f["geometry"]["coordinates"][0], 3), int(f["properties"]["pop_max"] or 0),
              f["properties"]["adm0name"], int(f["properties"]["adm0cap"] or 0)] for f in PPL], key=lambda r: -r[3])
jsave(pl, f"{PAGE}/places.json")
for fn in sorted(os.listdir(PAGE)):
    print(fn, os.path.getsize(f"{PAGE}/{fn}") // 1024, "KB")
print("results keys", list(R))
