"""Step 8. Paper PDF: fill code/paper_template.tex from data/results.json, write release/paper/Hotham_How_High_Is_the_World.tex
and compile it with xelatex (figures from step 7). Set TERRAIN_DOI (for example 10.5281/zenodo.1234567) to print the DOI;
without it the paper shows the placeholder 10.5281/zenodo.23848930.
Run: python3 code/08_paper.py
"""
import csv, importlib.util, os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("b", os.path.join(HERE, "06_build_site.py")); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
R = b.R
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_How_High_Is_the_World"
DOI = os.environ.get("TERRAIN_DOI", "10.5281/zenodo.23848930")
tex = lambda s: str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")

# facts stated only in the paper
rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "countries.csv"), encoding="utf-8")))
ranked = [r for r in rows if r["well_resolved"] == "1" and r["iso3"] != "ATA"]
assert [r["iso3"] for r in ranked if float(r["lowest_cell_m"]) > 1000] == ["LSO", "RWA"], [r["name"] for r in ranked if float(r["lowest_cell_m"]) > 1000]
assert R["countries"]["pick"]["NPL"]["mean"] < 2500


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct": return f"{v * 100:.0f}\\%"
    if f == "pct1": return f"{v * 100:.1f}\\%"
    if f == "f1": return f"{v:.1f}"
    if f == "ord": return b.ORD(int(v))
    return tex(str(v))


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(b.get(path.strip()), f.strip() or "raw")


p, c = R["peaks"], R["cities"]
TS = ("\\begin{table}[tbp]\\centering\\small\\caption{Sources, what was used and licences.}\\label{tab:sources}"
      "\\begin{tabular}{>{\\raggedright\\arraybackslash}p{3.6cm}>{\\raggedright\\arraybackslash}p{7.4cm}>{\\raggedright\\arraybackslash}p{3.4cm}}\\toprule Source & Used & Licence\\\\\\midrule\n"
      "AWS Terrain Tiles (Terrarium) & Zoom 4 grid for statistics; all zooms on the map & Per source; mostly public domain, some CC BY or OGL\\\\\n"
      "ETOPO10 (from ETOPO1) & Antarctica south of 85.05 S; polar caps for the Earth curve & Public domain\\\\\n"
      f"Wikidata & {p['n_wd']:,} peak items, {c['n_items']:,} city items & CC0\\\\\n"
      f"Natural Earth & Countries, lakes, places; {p['n_ne']} added summits & Public domain\\\\\n"
      f"English Wikipedia & 125 most prominent summits ({p['n_wp']} added) & CC BY-SA 4.0\\\\\n"
      "peakbagger.com list & National high points, check only & Not redistributed\\\\\n"
      "\\bottomrule\\end{tabular}\\end{table}")
pick = lambda L: "".join(f"{tex(x['name'])} & {x['mean']:,} & {x['median']:,} & {x['max']:,} & {x['above2000'] * 100:.0f}\\\\\n" for x in L)
TC = ("\\begin{table}[tbp]\\centering\\small\\caption{The ten highest and ten lowest countries by mean height of land (countries covering at least 100 cells of the zoom 4 grid). "
      "Median from 25 m bins; highest 10 km cell; share of land above 2,000 m (\\%).}\\label{tab:countries}"
      "\\begin{tabular}{lrrrr}\\toprule Country & Mean m & Median m & Highest cell m & Above 2,000 m\\\\\\midrule\n" + pick(R["countries"]["high"][:10]) +
      "\\midrule\n" + pick(R["countries"]["low"][:10]) + "\\bottomrule\\end{tabular}\\end{table}")
t = open(os.path.join(HERE, "paper_template.tex"), encoding="utf-8").read()
link = f"\\url{{https://doi.org/{DOI}}}" if DOI else "\\{\\{DOI\\}\\}"
t = t.replace("{{DOILINK}}", link).replace("{{TABLE_SOURCES}}", TS).replace("{{TABLE_COUNTRIES}}", TC)
for k in ("page", "repo"):
    t = t.replace("\\url{{{meta.%s}}}" % k, "\\url{%s}" % R["meta"][k])
t = re.sub(r"\{\{(?!TABLE_)([^{}]+?)\}\}", sub, t)
assert "{{" not in t.replace("\\{\\{DOI\\}\\}", "") and "--" not in t and "\u2014" not in t and "\u2013" not in t
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l][:10])
for ext in (".aux", ".log", ".out"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
print("paper", r.returncode, len(txt.split()), "words;", [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("\u2014") + txt.count("\u2013"))
