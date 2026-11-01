"""Step 9. Blog post (release/blog/post.html from code/blog_template.html) and release/blog/meta.json, the Zenodo folder
(paper PDF, key CSVs, results.json, a code-and-data zip and metadata.json), README.md and LICENSE.
Image placeholders {{IMG|file|alt|caption}} and the links 10.5281/zenodo.23848930, https://doi.org/10.5281/zenodo.23848930 and https://blog.tristanhotham.com/2026/10/31/world-terrain/ are left for the publisher.
Run: python3 code/09_release.py
"""
import importlib.util, json, os, re, shutil, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("b", os.path.join(HERE, "06_build_site.py")); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
R = b.R
NAME = "Hotham_How_High_Is_the_World"
DASH = ("—", "–", "--")
TOK = re.compile(r"\{\{(?!IMG\|)([^{}|]+)(\|(\w+))?\}\}")
# numbers written into the blog's alt text
assert [c["mean"] for c in R["continents"]] == [2208, 1059, 740, 629, 587, 370, 301]
hi, lo = R["countries"]["high"], R["countries"]["low"]
assert hi[0]["mean"] == 2961 and hi[9]["name"] == "Rwanda" and lo[5]["name"] == "Denmark" and lo[5]["mean"] == 30 and lo[0]["mean"] == 10
assert [round(R["land"]["above"][k] * 100, 1) for k in ("1000", "2000", "3000", "5000")] == [26.2, 11.0, 5.1, 0.5]
pr = R["peaks"]["prominent"]
assert [p["prom"] for p in pr[:6]] == [8849, 6961, 6155, 5885, 5529, 5250] and pr[14]["name"] == "Mauna Kea" and pr[14]["prom"] == 4205
assert [c["name"] for c in R["cities"]["top_million"][:12]] == ["Quito", "Bogotá", "Addis Ababa", "Arequipa", "Xining", "Sanaa", "Mexico City", "Kunming", "San Luis Potosí", "León de Los Aldama", "Kabul", "Johannesburg"]
lb = R["land"]["bands"][0]; cb = [x for x in R["cities"]["bands"] if x["lo"] == 0][0]; tp = sum(x["pop_m"] for x in R["cities"]["bands"])
assert round(lb["share"] * 100) == 32 and round(cb["pop_m"] / tp * 100) == 70
assert R["countries"]["pick"]["AND"]["cells"] < 100 and R["countries"]["pick"]["GBR"]["cells"] > 100

# blog
t = open(os.path.join(HERE, "blog_template.html"), encoding="utf-8").read()
t = TOK.sub(b.sub, t)
left = set(re.findall(r"\{\{(\w+)\}\}", t)); assert left <= b.PLACEHOLDERS, left
vis = re.sub(r"<!--.*?-->", "", t, flags=re.S)
for bad in DASH + ("DSIT", "DCMS", "civil serv"): assert bad not in vis, bad
for ln in t.splitlines():
    if "{{IMG|" in ln: assert ln.startswith("{{IMG|") and ln.endswith("}}"), ln
BL = os.path.join(ROOT, "release", "blog"); os.makedirs(BL, exist_ok=True)
open(os.path.join(BL, "post.html"), "w", encoding="utf-8").write(t)
imgs = re.findall(r"\{\{IMG\|([^|]+)\|", t)
for m in imgs: assert os.path.exists(os.path.join(BL, m)), m
assert 5 <= len(imgs) <= 8, len(imgs)
for fn in os.listdir(BL):
    if fn.startswith("b_") and fn not in imgs: os.remove(os.path.join(BL, fn))
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
pc = lambda v, d=0: f"{v * 100:.{d}f}%"
meta = dict(
    title="How high is the world? Mountains, plateaus and height above sea level on one map",
    slug="world-terrain",
    excerpt=(f"A map of the height of the whole planet, sharp from continents to valleys. The world's land averages {R['land']['mean']:,} m, only "
             f"{pc(R['land']['above']['2000'])} of it is above 2,000 m, and only {pc(R['cities']['share_above']['2000'], 1)} of the people in its cities live that high."),
    seo_description="An interactive world map of height above sea level, with shaded relief, peaks and cities, and how much of the land is high.",
    tags=["terrain", "elevation", "mountains", "height above sea level", "hypsometry", "maps", "data visualisation", "Wikidata"],
    header_alt=(f"Title card reading 'How high is the world?' in black on cream, with the line: only {pc(R['land']['above']['2000'])} of the land is above 2,000 m, "
                f"{pc(R['cities']['share_above']['2000'], 1)} of city people live that high. Beside it a world relief map in the Equal Earth projection, green lowlands "
                "rising through tan and brown to the pale mauve of the Tibetan Plateau and the Andes, with Greenland's ice dome in brown."))
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
for v in meta.values():
    for bad in DASH: assert bad not in str(v)
json.dump(meta, open(os.path.join(BL, "meta.json"), "w"), indent=2, ensure_ascii=False)

# README
L, NA, CT, PK, BE = R["land"], R["noant"], R["cities"], R["peaks"], R["below"]
readme = f"""# How high is the world?

A detailed world map of height above sea level, drawn live in the browser from the open AWS Terrain Tiles at every zoom (height tints, shaded relief, height steps, a readout of any point), with the world's peaks and cities by height, and a study of how high the land is and how high people live.

**Interactive version:** https://maps.tristanhotham.com/world-terrain/

**Paper and archived release:** {{https://doi.org/10.5281/zenodo.23848930}}

**Blog post:** {{https://blog.tristanhotham.com/2026/10/31/world-terrain/}}

A data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- The world's land averages {L['mean']:,} m above sea level (median {L['median']:,} m), or {NA['mean']:,} m without Antarctica's ice. {pc(L['above']['500'])} of it lies above 500 m, {pc(L['above']['1000'])} above 1,000 m, {pc(L['above']['2000'])} above 2,000 m, {pc(L['above']['3000'])} above 3,000 m, {pc(L['above']['4000'], 1)} above 4,000 m and {pc(L['above']['5000'], 1)} above 5,000 m.
- Continents: Antarctica {R['continents'][0]['mean']:,} m, Asia {R['continents'][1]['mean']:,} m, North America {R['continents'][2]['mean']:,} m, Africa {R['continents'][3]['mean']:,} m, South America {R['continents'][4]['mean']:,} m, Europe {R['continents'][5]['mean']:,} m, Oceania {R['continents'][6]['mean']:,} m. {pc(R['earth']['above0'], 1)} of the Earth's whole surface is above sea level.
- Countries (of {R['countries']['n_ranked']} covering at least 100 grid cells): highest {hi[0]['name']} ({hi[0]['mean']:,} m), {hi[1]['name']} ({hi[1]['mean']:,} m), {hi[2]['name']} ({hi[2]['mean']:,} m), {hi[3]['name']} ({hi[3]['mean']:,} m); lowest the {lo[0]['name']} ({lo[0]['mean']} m). United Kingdom {R['countries']['pick']['GBR']['mean']} m.
- People live low: of {CT['pop_bn']:.1f} billion people in {CT['n']:,} Wikidata cities of 50,000 or more, half live below {CT['median_person']} m, {pc(CT['share_above']['1000'], 1)} above 1,000 m and {pc(CT['share_above']['2000'], 1)} above 2,000 m. Highest city of a million or more: {CT['top_million'][0]['name']} ({CT['top_million'][0]['elev']:,} m); highest capital La Paz ({CT['capitals'][0]['elev']:,} m).
- Below sea level: {BE['named']:,} km² in named depressions on the 10 km grid, {pc(BE['caspian_share_named'])} of it around the Caspian; then Qattara, Kati Thanda-Lake Eyre, the Netherlands and Afar.
- Peaks: {PK['n']:,} summits after cleaning; the highest point of {PK['hp_verified']} countries confirmed against an independent list.

Every number is in `data/results.json`, which the page, paper, blog and collage are built from.

## Method in brief

- **Terrain.** AWS Terrain Tiles (Terrarium encoding: height = R × 256 + G + B / 256 − 32,768 m). The page decodes them live at zoom 0 to 14. The statistics use zoom 4, a 4,096 × 4,096 Web Mercator grid ({R['grid']['km_equator']} km at the equator, {R['grid']['km_60']} km at 60°), each cell weighted by its exact area on a sphere; {R['grid']['n_spikes']} corrupt cells replaced by their neighbours' median. Antarctica south of 85.05° S from ETOPO10.
- **Land.** Natural Earth 1:10m countries less lakes and reservoirs, rasterised at twice the grid's resolution. Coastal cells are floored at 0 m; only wholly-land interior cells can be below sea level. Ice counts at its surface.
- **Peaks.** Every Wikidata mountain, hill, summit and volcano with a height ({PK['n_wd']:,} items, heights normalised to metres from their stated units), plus {PK['n_ne']} summits from Natural Earth elevation points and {PK['n_wp']} from Wikipedia's 125 most prominent summits (which also give the prominence ranking); every height checked against the 10 km cells around it, feet and kilometres converted, implausible values dropped, and country high points checked against a peakbagger.com list (not republished).
- **Cities.** Wikidata cities of 50,000 or more with height and population; duplicates merged, metropolitan areas and provinces dropped, heights checked against the terrain.

## Files

| Path | What it is |
|---|---|
| `index.html` | The interactive page (results embedded; peaks, cities, places and borders load from `data/page/`; terrain tiles load live from Amazon). |
| `header.png` | Social card (1200 by 630). |
| `data/countries.csv` | Every country: land area, grid cells, mean and median height, highest and lowest cell, shares above 1,000, 2,000 and 3,000 m and below 0 m, highest peak in the open data and whether it is confirmed. |
| `data/continents.csv` | The same by continent. |
| `data/hypsometry.csv`, `data/earth_hypsometry.csv` | Share of land (with and without Antarctica), and of the whole Earth's surface, above each height. |
| `data/below_sea_level.csv` | Land below sea level by depression. |
| `data/peaks.csv` | {PK['n']:,} cleaned summits: height and prominence with their sources, point, countries, kind, sitelinks, the check applied and the grid heights around them. |
| `data/cities.csv` | {CT['n']:,} cleaned cities: height, population, point, country, grid height and check. |
| `data/results.json` | Every number used anywhere. |
| `data/page/` | Page files: borders, peaks (the 15,000 best known first, the rest loaded when zoomed in), cities, place names, country figures. |
| `code/` | Numbered scripts (below), page, paper and blog templates. |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |
| `release/` | Paper PDF and LaTeX (its figures are the blog figures), blog post and figures, Zenodo metadata (with the list of files to upload) and the code-and-data zip. |
| `qa/` | Screenshots from the last check of the page. |

## Known limits

- The statistics are smoothed to about 10 km: the highest cell is {R['grid']['highest_cell']:,} m, {R['derived']['everest_vs_cell']:,} m below Everest's summit. Small countries (under 100 cells) are only roughly resolved and are not ranked.
- Coastal cells are floored at sea level, hiding small coastal depressions; another {BE['g']['else']['area']:,} km² of patches below 0 m on deltas and coasts is not counted.
- Wikidata heights come from many surveys of different ages, subsidiary tops are listed as items of their own, and some wrong heights will remain despite the checks. Wikidata populations differ in date and definition; Chinese prefecture-level cities include rural areas, so they enter the million-plus ranking only if Natural Earth gives their urban area a million or more.

## How to rerun

Needs Python 3 with numpy, scipy, shapely, rasterio, pyproj, matplotlib, Pillow and fontTools; xelatex and pdftotext; Playwright for the QA step. Raw inputs are read in place from the paths in `code/common.py` (set `TERRAIN_RAW`, `TERRAIN_GEO`, `TERRAIN_WORK` to change). The supplementary files (Natural Earth elevation points and lakes, the Wikipedia prominence table and the check list) were fetched from the GitHub URLs given in `code/02_peaks.py` and `code/common.py`.

```
python3 code/01_grid.py        # terrain grid, land and country masks, Antarctic cap
python3 code/02_peaks.py       # peaks: merge, check, countries
python3 code/03_cities.py      # cities
python3 code/04_stats.py       # statistics and CSVs
python3 code/05_results.py     # results.json and page data
python3 code/06_build_site.py  # index.html
python3 code/07_figures.py     # figures and header
python3 code/08_paper.py       # paper PDF
python3 code/09_release.py     # blog, Zenodo files, README, LICENSE
python3 reddit/collage.py      # collage
python3 code/12_qa.py          # screenshots and console check
```

## Sources and licences

- AWS Terrain Tiles, Mapzen and the Registry of Open Data on AWS: https://registry.opendata.aws/terrain-tiles/. Sources and terms: https://github.com/tilezen/joerd/blob/master/docs/attribution.md (SRTM, GMTED2010, ETOPO1, NED and 3DEP, Canadian DEM, EU-DEM produced using Copernicus data, Geoscience Australia CC BY 4.0, LINZ CC BY 4.0, INEGI, OS Terrain 50 under the Open Government Licence, ArcticDEM and others). The tiles are not redistributed here.
- ETOPO10, derived from NOAA's ETOPO1 (Amante and Eakins 2009). Public domain.
- Wikidata (CC0). Natural Earth (public domain). English Wikipedia, 'List of mountain peaks by prominence' (CC BY-SA 4.0), as tabulated at ianto-cannon.github.io.
- Base map and satellite tiles on the page © Esri.

## Citation

Hotham, T. (2026) How high is the world? Height above sea level, mountains and where people live, from open terrain data. Zenodo. {{https://doi.org/10.5281/zenodo.23848930}}

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
"""
for bad in DASH: assert bad not in readme.replace("|---|---|", ""), bad
assert "DSIT" not in readme and "DCMS" not in readme
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)
open(os.path.join(ROOT, "LICENSE"), "w", encoding="utf-8").write("""MIT License

Copyright (c) 2026 Tristan Hotham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


This licence covers the code in code/, reddit/collage.py and the page scripts.
The text of the page, the figures and the derived data in data/ are released
under CC BY 4.0, except that the prominence values taken from English
Wikipedia's 'List of mountain peaks by prominence' (in data/peaks.csv, where
prominence_source is 'wikipedia') are shared under CC BY-SA 4.0. Wikidata is
CC0 and Natural Earth is public domain. The terrain statistics are derived from
the AWS Terrain Tiles; see https://github.com/tilezen/joerd/blob/master/docs/attribution.md
for the terms of each source (some, such as Geoscience Australia and LINZ, ask
for attribution under CC BY 4.0, and OS Terrain 50 is under the Open Government
Licence, Crown copyright and database right). The tiles are not redistributed.
""")

# Zenodo
Z = os.path.join(ROOT, "release", "zenodo"); os.makedirs(Z, exist_ok=True)
pt = open(os.path.join(ROOT, "release", "paper", NAME + ".tex"), encoding="utf-8").read()
ab = pt.split("\\begin{center}\\textbf{Abstract}\\end{center}")[1].split("\\textbf{Keywords:}")[0].strip()
ab = ab.replace("\\%", "%").replace("\\&", "&").replace("~", " ")
assert "\\" not in ab and "$" not in ab, ab
zmeta = dict(
    title="How High Is the World? Height Above Sea Level, Mountains and Where People Live, from Open Terrain Data",
    upload_type="publication", publication_type="workingpaper",
    description=(f"<p>{ab}</p><p>Interactive version: <a href=\"https://maps.tristanhotham.com/world-terrain/\">https://maps.tristanhotham.com/world-terrain/</a>. "
                 "Data and code: <a href=\"https://github.com/Tristan-Hotham/world-terrain\">https://github.com/Tristan-Hotham/world-terrain</a>. Blog post: https://blog.tristanhotham.com/2026/10/31/world-terrain/.</p>"
                 "<p>Text, figures and derived data: CC BY 4.0 (prominence values from English Wikipedia: CC BY-SA 4.0); code: MIT. Terrain: AWS Terrain Tiles "
                 "(Mapzen; SRTM, GMTED2010, ETOPO1 and other sources listed at github.com/tilezen/joerd), not redistributed. Peaks and cities: Wikidata (CC0). "
                 "Boundaries, lakes and places: Natural Earth (public domain).</p>"),
    creators=[{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
    keywords=["elevation", "height above sea level", "hypsometry", "topography", "mountains", "prominence", "cities", "terrain tiles", "SRTM", "Wikidata", "data visualisation"],
    license="cc-by-4.0", language="eng",
    related_identifiers=[
        dict(identifier="https://github.com/Tristan-Hotham/world-terrain", relation="isSupplementedBy", resource_type="software"),
        dict(identifier="https://maps.tristanhotham.com/world-terrain/", relation="isSupplementedBy", resource_type="other"),
        dict(identifier="https://registry.opendata.aws/terrain-tiles/", relation="isDerivedFrom", resource_type="dataset"),
        dict(identifier="10.7289/V5C8276M", relation="isDerivedFrom", scheme="doi", resource_type="dataset"),
        dict(identifier="https://www.wikidata.org/", relation="isDerivedFrom", resource_type="dataset"),
        dict(identifier="https://www.naturalearthdata.com/", relation="isDerivedFrom", resource_type="dataset")])
s = json.dumps(zmeta, ensure_ascii=False)
for bad in DASH: assert bad not in s, bad
zmeta["upload_files"] = [f"release/paper/{NAME}.pdf", "release/zenodo/world-terrain_code_and_data.zip"] + [f"data/{f}" for f in
                         ["results.json", "countries.csv", "continents.csv", "hypsometry.csv", "earth_hypsometry.csv", "below_sea_level.csv", "peaks.csv", "cities.csv"]]
json.dump(zmeta, open(os.path.join(Z, "metadata.json"), "w"), indent=2, ensure_ascii=False)
# to keep the repo free of duplicates, the Zenodo folder holds only the metadata and the code-and-data zip; the other files
# to upload are listed in metadata.json under "upload_files" (paths relative to the repo root)
for fn in os.listdir(Z):
    if fn not in ("metadata.json", "world-terrain_code_and_data.zip"): os.remove(os.path.join(Z, fn))
zp = os.path.join(Z, "world-terrain_code_and_data.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
    for base in ("code", "data", "reddit"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                if f.endswith(".png") or f.endswith(".pdf"): continue
                zf.write(os.path.join(dp, f), os.path.join("world-terrain", os.path.relpath(os.path.join(dp, f), ROOT)))
    for f in ("README.md", "LICENSE", "index.html", "header.png"): zf.write(os.path.join(ROOT, f), os.path.join("world-terrain", f))
print("release written; blog words", words, "images", len(imgs))
for f in sorted(os.listdir(Z)): print(" ", f, os.path.getsize(os.path.join(Z, f)) // 1024, "KB")
