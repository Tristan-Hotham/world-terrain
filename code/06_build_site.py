"""Step 6. Build index.html from code/page_template.html, code/page_text.html and code/page_charts.js. Every number in
the text is a {{path|format}} token filled from data/results.json; facts stated in words are checked by the asserts below
(they cover the page, paper, blog and collage). The placeholders 10.5281/zenodo.23848930, https://doi.org/10.5281/zenodo.23848930 and https://blog.tristanhotham.com/2026/10/31/world-terrain/ are left for the
publisher to fill.
Run: python3 code/06_build_site.py
"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json"), encoding="utf-8"))
PLACEHOLDERS = {"DOI", "DOI_URL", "BLOG_URL"}
ORD = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(v):,}"
    if f == "abs": return f"{abs(round(v)):,}"
    if f == "pct": return f"{round(v * 100)}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    if f == "ord": return ORD(int(v))
    raise ValueError(f)


def sub(m):
    if m.group(1).strip() in PLACEHOLDERS:
        return m.group(0)
    return fmt(get(m.group(1).strip()), m.group(3))


# ---- facts stated in words (page, paper, blog, collage) ----
co = [c["name"] for c in R["continents"]]
assert co == ["Antarctica", "Asia", "North America", "Africa", "South America", "Europe", "Oceania"], co
hi = [c["a3"] for c in R["countries"]["high"]]; lo = [c["a3"] for c in R["countries"]["low"]]
assert hi[:5] == ["TJK", "BTN", "KGZ", "LSO", "NPL"], hi
assert R["countries"]["high"][3]["cont"] == "Africa" and all(c["cont"] == "Asia" for c in R["countries"]["high"][:3])
assert lo[0] == "NLD" and R["countries"]["low"][0]["name"] == "Netherlands" and R["countries"]["pick"]["BGD"]["mean"] > R["countries"]["low"][0]["mean"]
assert R["countries"]["pick"]["DNK"]["mean"] > R["countries"]["low"][0]["mean"]
assert R["countries"]["pick"]["LSO"]["min"] > 1000 and R["countries"]["pick"]["LSO"]["above1000"] == 1.0
ad = R["countries"]["pick"]["AND"]; assert ad["cells"] < 10 and ad["mean"] > R["countries"]["high"][5]["mean"]          # Andorra 'would rank among the highest'
assert R["earth"]["sea_depth"] > 4 * R["land"]["mean"]                                                               # 'more than four times deeper'
assert R["antarctica"]["mean"] > R["continents"][1]["mean"] * 2
pk = R["peaks"]
assert pk["cont_top"]["Oceania"]["name"] == "Mount Wilhelm" and pk["prominent"][8]["name"] == "Puncak Jaya" and pk["prominent"][8]["iso"] == ["IDN"]
assert [p["name"] for p in pk["prominent"][:5]] == ["Mount Everest", "Aconcagua", "Denali", "Mount Kilimanjaro", "Pico Cristóbal Colón"]
assert pk["prominent"][0]["prom"] == pk["prominent"][0]["elev"] and pk["prominent"][4]["range"] == "Sierra Nevada de Santa Marta"
assert [pk["cont_top"][k]["name"] for k in ("Asia", "South America", "North America", "Africa", "Europe", "Antarctica")] == ["Mount Everest", "Aconcagua", "Denali", "Mount Kilimanjaro", "Mount Elbrus", "Vinson Massif"]
assert pk["k2_prom_rank"] == 22 and pk["prominent"][10]["name"] == "Mont Blanc"
assert pk["hp_status"]["open data lacks the high point"] > 0
CK = json.load(open(os.path.join(os.environ.get("TERRAIN_WORK", "/dev/shm/world-terrain"), "peak_checks.json"), encoding="utf-8"))["hp_check"]
lack = {c["iso"]: c for c in CK if c.get("status") == "open data lacks the high point"}
assert lack["SAU"]["ref_name"] == "Jabal Ferwa" and lack["SOM"]["ref_name"] == "Shimbiris"
assert any(p["name"] == "South Summit" for p in pk["top"])                                                         # subsidiary tops listed as items
ct = R["cities"]
assert ct["top_million"][0]["name"] == "Quito" and [c["name"] for c in ct["biggest_above2000"][:3]] == ["Mexico City", "Bogotá", "Addis Ababa"]
assert ct["top_100k"][1]["name"] == "El Alto" and ct["top_100k"][2]["name"] == "Potosí" and ct["capitals"][0]["name"] == "La Paz"
assert ct["lowest"][0]["name"] == "Baku" and ct["lowest"][0]["elev"] < 0
assert R["land"]["above"]["2000"] > ct["share_above"]["2000"] * 5
b = R["below"]["g"]
assert b["caspian"]["area"] > b["qattara"]["area"] > b["eyre"]["area"] > b["nl"]["area"] > b["afar"]["area"]
assert b["deadsea"]["min"] == min(g["min"] for g in R["below"]["groups"] if g["name"] != "Elsewhere")             # 'the lowest land'
assert b["death"]["area"] < 1000
assert R["grid"]["spike_max"] == 11500
import csv as _csv
_cc = {r["name"]: r for r in _csv.DictReader(open(os.path.join(ROOT, "data", "cities.csv"), encoding="utf-8"))}
assert float(_cc["Lijiang"]["elevation_m"]) == 2400 and int(_cc["Lijiang"]["population"]) >= 1e6 and int(_cc["Zhaotong"]["population"]) >= 1e6
assert not {"Lijiang", "Zhaotong"} & {c["name"] for c in R["cities"]["top_million"]}                                  # left out of the ranking
A = {c["name"]: c for c in R["continents"]}
assert (A["Antarctica"]["area_m"] * A["Antarctica"]["above2000"] + A["Asia"]["area_m"] * A["Asia"]["above2000"]) / (R["land"]["area_m"] * R["land"]["above"]["2000"]) > .5   # 'most of it in Antarctica and Asia'

TOK = re.compile(r"\{\{([^}|]+)(\|(\w+))?\}\}")


def check_text(html):
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv", "Civil Serv"):
        assert bad not in vis, bad
    return vis


if __name__ == "__main__":
    tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
    txt = open(os.path.join(HERE, "page_text.html"), encoding="utf-8").read()
    parts = dict(re.findall(r"<!--@(\w+)-->(.*?)<!--@end-->", txt, flags=re.S))
    for k in ("INTRO", "BODY"):
        tpl = tpl.replace(f"/*{k}*/", parts[k].strip())
    tpl = tpl.replace("/*CHARTS*/", open(os.path.join(HERE, "page_charts.js"), encoding="utf-8").read())
    tpl = tpl.replace("/*FULLSCREEN*/", open(os.path.join(HERE, "fullscreen_snippet.html"), encoding="utf-8").read().strip())
    html = TOK.sub(sub, tpl)
    PD = dict(R=R, curve=R["curve"], countries=json.load(open(os.path.join(ROOT, "data", "page", "countries.json"), encoding="utf-8")),
              cityAbove=R["cities"]["above_curve"])
    html = html.replace("/*PD*/", json.dumps(PD, ensure_ascii=False, separators=(",", ":")))
    left = set(re.findall(r"\{\{(\w+)\}\}", html))
    assert left <= PLACEHOLDERS and "{{" not in re.sub(r"\{\{(DOI|DOI_URL|BLOG_URL)\}\}", "", html), left
    check_text(html)
    for scr in re.findall(r"<script>(.*?)</script>", html, flags=re.S):
        for bad in ("—", "–"):
            assert bad not in scr, bad
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()), "bytes")
