"""Step 7. Figures for the blog and the paper (release/blog/b_*.png, used by both), and header.png (1200 x 630).
Every number drawn comes from data/results.json.
Run: python3 code/07_figures.py
"""
import shutil
from figlib import *
from matplotlib.patches import Rectangle

R = jload(f"{DATA}/results.json")
BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
os.makedirs(BL, exist_ok=True); os.makedirs(PA, exist_ok=True)
fmt = lambda v: f"{round(v):,}"
pc = lambda v, d=0: f"{v * 100:.{d}f}%"


def save(fig, name):
    fig.savefig(f"{BL}/b_{name}.png", dpi=200, facecolor=fig.get_facecolor())     # the paper uses the same files
    plt.close(fig)


RES = 0.075
h, land, lat, lon = lonlat_grid(RES)
img = relief_rgb(h, land, lat, RES, exag=22, light_sea=True)


def legend_bar(ax, x0, y0, w, hh, fs=9):
    T = [0, 250, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000]
    n = len(T) - 1
    for i in range(n):
        for k in range(8):
            v = T[i] + (T[i + 1] - T[i]) * k / 8
            ax.add_patch(Rectangle((x0 + w * (i + k / 8) / n, y0), w / n / 8 + 1e-4, hh, transform=ax.transAxes, fc=land_rgb(v), ec="none", clip_on=False))
    for i, t in enumerate(T[:-1]):
        ax.text(x0 + w * i / n, y0 - hh * .5, f"{t:,}", transform=ax.transAxes, ha="center", va="top", fontsize=fs, color=FG)
    ax.text(x0 + w, y0 - hh * .5, "m", transform=ax.transAxes, ha="center", va="top", fontsize=fs, color=MUT)


# ---- 1. world relief ----
out, ext, P = equal_earth(img, lat, lon, 3000, -62, 84, bg=tuple(np.array([246, 243, 236]) / 255))
fig = plt.figure(figsize=(12, 6.3), facecolor=BG)
ax = fig.add_axes([0, .1, 1, .9]); ax.imshow(out, extent=ext, interpolation="lanczos"); ax.axis("off")
lg = fig.add_axes([0, 0, 1, .1]); lg.axis("off")
legend_bar(lg, .25, .55, .5, .25)
lg.text(.5, .97, "Height above sea level, metres (tints) with shaded relief", ha="center", va="top", fontsize=10, color=FG, transform=lg.transAxes)
save(fig, "world_relief")

# ---- 2. hypsometric curve ----
cv = np.array(R["curve"])
fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=BG); ax.set_facecolor(BG)
for k in range(len(cv) - 1):
    ax.add_patch(Rectangle((0, cv[k, 0]), cv[k, 1] * 100, cv[k + 1, 0] - cv[k, 0], fc=land_rgb(cv[k, 0]), ec="none"))
ax.plot(cv[:, 1] * 100, cv[:, 0], color=FG, lw=2, label="All land")
ax.plot(cv[:, 2] * 100, cv[:, 0], color=ICE, lw=1.6, ls="--", label="Without Antarctica")
for m in ("1000", "2000", "3000", "5000"):
    v = R["land"]["above"][m] * 100; ax.plot(v, int(m), "o", color=FG, ms=5)
    ax.annotate(f"{v:.{1 if v < 1 else 0}f}% above {int(m):,} m", (v, int(m)), xytext=(10, 6), textcoords="offset points", fontsize=10.5)
ax.set_xlim(0, 100); ax.set_ylim(0, 7000); style(ax, axis="y")
ax.set_xlabel("share of the world's land higher than this (%)"); ax.set_ylabel("height above sea level (m)")
ax.legend(frameon=False, loc="upper right"); fig.tight_layout(); save(fig, "hypsometry")

# ---- 3. continents and countries ----
fig, axs = plt.subplots(1, 2, figsize=(12, 5.4), facecolor=BG, gridspec_kw=dict(width_ratios=[1, 1.15]))
co = R["continents"][::-1]
axs[0].barh([c["name"] for c in co], [c["mean"] for c in co], color=[land_rgb(c["mean"]) for c in co], edgecolor="#00000040")
for i, c in enumerate(co): axs[0].text(c["mean"] + 40, i, f"{fmt(c['mean'])} m", va="center", fontsize=10)
axs[0].set_title("Average height of the land, by continent", loc="left", fontsize=12); axs[0].set_xlim(0, 2700)
hi = R["countries"]["high"][:10][::-1]; lo = R["countries"]["low"][:6]
seq = lo + [None] + hi                                  # bottom to top: lowest countries, a gap, highest countries
vals = [c["mean"] if c else 0 for c in seq]; labs = [c["name"] if c else "" for c in seq]
y = np.arange(len(vals))
axs[1].barh(y, vals, color=[land_rgb(v) for v in vals], edgecolor="#00000040"); axs[1].set_yticks(y, labs)
for i, v in enumerate(vals):
    if labs[i]: axs[1].text(v + 40, i, f"{fmt(v)} m", va="center", fontsize=10)
axs[1].text(1500, 6, "above: the 10 highest\nbelow: the 6 lowest", fontsize=10, color=MUT, va="center")
axs[1].set_title("Highest and lowest countries (mean height)", loc="left", fontsize=12); axs[1].set_xlim(0, 3500)
for a in axs: style(a); a.set_facecolor(BG)
fig.tight_layout(); save(fig, "countries")

# ---- 4. prominence ----
pr = R["peaks"]["prominent"][::-1]
fig, ax = plt.subplots(figsize=(10, 6.4), facecolor=BG); ax.set_facecolor(BG)
y = np.arange(len(pr))
ax.barh(y, [p["elev"] for p in pr], color=[land_rgb(p["elev"]) for p in pr], edgecolor="#00000030", label="height")
ax.barh(y, [p["prom"] for p in pr], height=.38, color=UMBER, label="prominence")
ax.set_yticks(y, [f"{p['name']} ({', '.join(p['countries'])})" for p in pr], fontsize=9.5)
for i, p in enumerate(pr): ax.text(max(p["elev"], p["prom"]) + 80, i, f"{fmt(p['prom'])} m", va="center", fontsize=9.5)
ax.set_xlim(0, 10000); ax.set_xlabel("metres"); style(ax); ax.legend(frameon=False, loc="lower right")
ax.set_title("The most prominent peaks: height (pale) and prominence (dark)", loc="left", fontsize=12)
fig.tight_layout(); save(fig, "prominence")

# ---- 5. land and people by height ----
lb = R["land"]["bands"]; cb = [b for b in R["cities"]["bands"] if b["lo"] >= 0]; tp = sum(b["pop_m"] for b in R["cities"]["bands"])
rows = []
for b in lb:
    c = sum(x["pop_m"] for x in cb if x["lo"] >= b["lo"] and x["hi"] <= b["hi"]) / tp
    rows.append((b["lo"], b["hi"], b["share"], c))
fig, ax = plt.subplots(figsize=(10, 5.8), facecolor=BG); ax.set_facecolor(BG)
y = np.arange(len(rows))
ax.barh(y + .2, [r[2] * 100 for r in rows], height=.4, color=[land_rgb((r[0] + min(r[1], 6000)) / 2) for r in rows], edgecolor="#00000040", label="share of the world's land")
ax.barh(y - .2, [r[3] * 100 for r in rows], height=.4, color=FG, label="share of people in listed cities")
ax.set_yticks(y, [f"above {r[0]:,} m" if r[1] >= 7000 else f"{r[0]:,} to {r[1]:,} m" for r in rows])
for i, r in enumerate(rows):
    ax.text(r[2] * 100 + .8, i + .2, f"{r[2] * 100:.{1 if r[2] < .1 else 0}f}%", va="center", fontsize=9)
    ax.text(r[3] * 100 + .8, i - .2, f"{r[3] * 100:.{1 if r[3] < .1 else 0}f}%", va="center", fontsize=9)
ax.set_xlim(0, 80); style(ax); ax.legend(frameon=False, loc="lower right"); ax.set_xlabel("%")
ax.set_title(f"Land and city people by height: {pc(R['land']['above']['2000'])} of land, {pc(R['cities']['share_above']['2000'], 1)} of people above 2,000 m", loc="left", fontsize=11.5)
fig.tight_layout(); save(fig, "people_land")

# ---- 6. highest cities ----
ct = R["cities"]["top_million"][:12][::-1]
fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=BG); ax.set_facecolor(BG)
y = np.arange(len(ct))
ax.barh(y, [c["elev"] for c in ct], color=[land_rgb(c["elev"]) for c in ct], edgecolor="#00000040")
ax.set_yticks(y, [f"{c['name']}, {c['country']}" for c in ct])
for i, c in enumerate(ct): ax.text(c["elev"] + 30, i, f"{fmt(c['elev'])} m · {c['pop'] / 1e6:.1f} million", va="center", fontsize=9.5)
ax.set_xlim(0, 3900); style(ax); ax.set_xlabel("height above sea level (m, Wikidata)")
ax.set_title("The highest cities of a million or more", loc="left", fontsize=12)
fig.tight_layout(); save(fig, "cities")

# ---- 7. below sea level: four close-ups ----
G = R["below"]["g"]
boxes = [("Caspian Depression", (44, 57, 36.5, 49)), ("Qattara Depression", (24.5, 30.5, 27.5, 31.5)),
         ("Dead Sea and the Jordan valley", (33.6, 37.4, 30.3, 33.4)), ("Netherlands polders", (3.3, 7.3, 51.2, 53.6))]
key = {"Caspian Depression": "caspian", "Qattara Depression": "qattara", "Dead Sea and the Jordan valley": "deadsea", "Netherlands polders": "nl"}
fig, axs = plt.subplots(1, 4, figsize=(13, 4.2), facecolor=BG)
for ax, (nm, (x0, x1, y0, y1)) in zip(axs, boxes):
    ri = (lat <= y1) & (lat >= y0); ci = (lon >= x0) & (lon <= x1)
    sub = img[ri][:, ci].copy(); hh = h[ri][:, ci]; ll = land[ri][:, ci]
    m = ll & (hh < 0); sub[m] = sub[m] * .35 + np.array([.1, .55, .5]) * .65
    ax.imshow(sub, extent=(x0, x1, y0, y1), aspect=1 / np.cos(np.radians((y0 + y1) / 2)), interpolation="nearest")
    g = G[key[nm]]
    ax.set_title(f"{nm.replace(' and the Jordan valley', ', Jordan valley')}\n{fmt(g['area'])} km² below 0 m\nlowest cell {fmt(g['min'])} m", fontsize=9.5, loc="left")
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("Land below sea level (teal) on the 10 km grid", x=.01, ha="left", fontsize=12)
fig.tight_layout(); save(fig, "below_sea")

# ---- header 1200 x 630 ----
outh, exth, _ = equal_earth(img, lat, lon, 1500, -58, 84, bg=tuple(np.array([246, 243, 236]) / 255))
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([.33, .06, .67, .88]); ax.imshow(outh, extent=exth, interpolation="lanczos"); ax.axis("off")
fig.text(.035, .86, "How high\nis the world?", fontproperties=DISP, fontsize=46, color=FG, va="top", linespacing=.95)
fig.text(.035, .50, f"Only {pc(R['land']['above']['2000'])} of the land\nis above 2,000 m.\n{pc(R['cities']['share_above']['2000'], 1)} of city people\nlive that high.", fontsize=15, family=SER, color=FG, va="top", linespacing=1.35)
fig.text(.035, .07, "maps.tristanhotham.com/world-terrain", fontsize=10.5, color=MUT)
fig.patches.append(Rectangle((0, 0), .012, 1, transform=fig.transFigure, fc=UMBER))
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG); plt.close(fig)
print("figures done")
