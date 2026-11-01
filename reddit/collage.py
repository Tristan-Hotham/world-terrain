"""r/dataisbeautiful collage for world-terrain: 3000 x 3750 px, light background. Numbers from data/results.json.
Labels sit on open sea with thin leader lines to their feature; the script checks that no two leader lines cross and
that no label box overlaps another.
Run: python3 reddit/collage.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
from figlib import *
from matplotlib.patches import Rectangle
import matplotlib.patheffects as pe

R = jload(f"{DATA}/results.json")
fmt = lambda v: f"{round(v):,}"
pc = lambda v, d=0: f"{v * 100:.{d}f}%"
CBG = "#F7F4EE"
RES = 0.075
h, land, lat, lon = lonlat_grid(RES)
img = relief_rgb(h, land, lat, RES, exag=24, light_sea=True)
out, ext, P = equal_earth(img, lat, lon, 3400, -62, 84, bg=tuple(np.array([247, 244, 238]) / 255))

fig = plt.figure(figsize=(12, 15), dpi=250, facecolor=CBG)
fig.text(.04, .972, "How high is the world?", fontproperties=DISP, fontsize=58, color=FG, va="top")
fig.text(.04, .915, f"Height above sea level of every place on Earth, in colour, with shaded relief. The average land stands {fmt(R['land']['mean'])} m high,\n"
         f"but only {pc(R['land']['above']['2000'])} of the land is above 2,000 m, and only {pc(R['cities']['share_above']['2000'], 1)} of the people in the world's listed cities live that high.",
         family=SER, fontsize=15, color=FG, va="top", linespacing=1.45)

ax = fig.add_axes([.005, .478, .99, .38]); ax.imshow(out, extent=ext, interpolation="lanczos"); ax.axis("off")
ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
pk = R["peaks"]; cp = R["countries"]["pick"]
LAB = [  # text, feature lon/lat, preferred side (dx, dy in degrees, a hint for the search)
    (f"Himalaya\nEverest {fmt(pk['prominent'][0]['elev'])} m", (86.93, 27.99), (0, -30)),
    (f"Andes\nAconcagua {fmt(pk['prominent'][1]['elev'])} m", (-70.01, -32.65), (-30, 0)),
    ("Altiplano", (-67.5, -18), (-30, 0)),
    ("Rocky Mountains", (-108, 41), (-40, 0)),
    ("Mexican Plateau", (-102, 23), (-30, -5)),
    (f"Denali\n{fmt(pk['cont_top']['North America']['elev'])} m", (-151.0, 63.07), (-10, -15)),
    (f"Greenland\nice sheet\nmean {fmt(cp['GRL']['mean'])} m", (-41, 72), (12, -20)),
    (f"Alps\nMont Blanc {fmt(pk['prominent'][10]['elev'])} m", (6.87, 45.83), (-35, 0)),
    ("Ethiopian\nHighlands", (39, 9.5), (20, 0)),
    (f"Kilimanjaro\n{fmt(pk['cont_top']['Africa']['elev'])} m", (37.36, -3.07), (25, -10)),
    (f"New Guinea Highlands\nPuncak Jaya {fmt(pk['prominent'][8]['elev'])} m", (137.18, -4.08), (15, 12)),
    ("Great Dividing Range", (148.5, -31), (-10, -15)),
]
# land polygons (Natural Earth 1:50m) in the map's projection: no label box may touch them
import shapely
from shapely.geometry import shape, box as sbox, LineString
from shapely.ops import unary_union
from pyproj import Transformer
_fw = Transformer.from_crs(4326, 8857, always_xy=True)
LANDP = unary_union([shapely.transform(shape(f["geometry"]).buffer(0), lambda xy: np.column_stack(_fw.transform(xy[:, 0], xy[:, 1])))
                     for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]])
shapely.prepare(LANDP)
halo = [pe.withStroke(linewidth=3.2, foreground="white")]
fig.canvas.draw(); rend = fig.canvas.get_renderer()
inv = ax.transData.inverted()
PADM = 35000                                          # keep boxes 60 km clear of any coast
XL, YL = ax.get_xlim(), ax.get_ylim()
placed = []                                           # (box polygon, leader LineString)
for t, (fx, fy), (hx, hy) in LAB:
    tx = ax.text(0, 0, t, ha="center", va="center", fontsize=8.6, color=FG, family=MONO, zorder=7, path_effects=halo, linespacing=1.15,
                 bbox=dict(boxstyle="round,pad=.2", fc=(1, 1, 1, .92), ec="none"))
    fig.canvas.draw()
    bb = tx.get_bbox_patch().get_window_extent(rend)
    (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    w, h = x1 - x0, y1 - y0
    FX, FY = P(fx, fy); HX, HY = P(fx + hx, fy + hy)
    best = None
    for gx in np.linspace(XL[0] + w / 2, XL[1] - w / 2, 160):
        for gy in np.linspace(YL[0] + h / 2, YL[1] - h / 2, 70):
            d = np.hypot(gx - HX, gy - HY)
            if best is not None and d >= best[0]: continue
            bx = sbox(gx - w / 2, gy - h / 2, gx + w / 2, gy + h / 2)
            if bx.buffer(PADM).intersects(LANDP): continue
            if any(bx.buffer(PADM).intersects(o[0]) for o in placed): continue
            # leader from the feature to the nearest point of the box edge
            ex = min(max(FX, gx - w / 2), gx + w / 2); ey = min(max(FY, gy - h / 2), gy + h / 2)
            ln = LineString([(FX, FY), (ex, ey)])
            if any(ln.intersects(o[0]) or ln.crosses(o[1]) for o in placed): continue
            if any(o[1].intersects(bx) for o in placed): continue
            best = (d, gx, gy, bx, ln)
    assert best, ("no clear place for", t)
    print(t.split(chr(10))[0], "box km", round(w / 1e3), round(h / 1e3), "at", [round(v / 1e3) for v in best[1:3]])
    _, gx, gy, bx, ln = best
    tx.set_position((gx, gy))
    ax.plot(*ln.xy, color="#2B2420", lw=.7, zorder=5, solid_capstyle="round")
    ax.plot([FX], [FY], "o", ms=3.2, color="#2B2420", mec="white", mew=.7, zorder=6)
    placed.append((bx, ln))
# final geometric check: no box touches land, another box, or another label's leader; no two leaders cross
for i, (bx, ln) in enumerate(placed):
    assert not bx.intersects(LANDP), LAB[i][0]
    for j, (bx2, ln2) in enumerate(placed):
        if i == j: continue
        assert not bx.intersects(bx2) and not ln2.intersects(bx) and not ln.crosses(ln2), (LAB[i][0], LAB[j][0])
print("labels placed clear of land:", len(placed))

# legend under the map
lg = fig.add_axes([.2, .437, .6, .028]); lg.axis("off")
T = [0, 250, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000]; n = len(T) - 1
for i in range(n):
    for k in range(10):
        v = T[i] + (T[i + 1] - T[i]) * k / 10
        lg.add_patch(Rectangle((i + k / 10, .45), .1001, .55, fc=land_rgb(v), ec="none"))
lg.add_patch(Rectangle((0, .45), n, .55, fc="none", ec=MUT, lw=.6))
for i, t in enumerate(T[:-1]): lg.text(i, .3, f"{t:,}" if t < 1000 else f"{t // 1000}k" if t % 1000 == 0 else f"{t / 1000:.1f}k", ha="center", va="top", fontsize=10)
lg.text(n, .3, "m", ha="center", va="top", fontsize=10, color=MUT)
lg.add_patch(Rectangle((-1.75, .45), .55, .55, fc=np.array(LOWLAND) / 255, ec=MUT, lw=.6)); lg.text(-1.47, .3, "land below\nsea level", ha="center", va="top", fontsize=9)
lg.add_patch(Rectangle((n + 1.2, .45), .55, .55, fc=sea_rgb(-3000) * .55 + np.array([.93, .95, .96]) * .45, ec=MUT, lw=.6)); lg.text(n + 1.47, .3, "sea\nfloor", ha="center", va="top", fontsize=9)
lg.set_xlim(-1.9, n + 1.9); lg.set_ylim(-.6, 1.4)
fig.text(.5, .465, "Height above sea level, metres (1k = 1,000 m; steps not to scale) · Equal Earth projection, 60° S to 84° N", ha="center", fontsize=10.5, color=MUT)

# big numbers
nums = [(f"{fmt(R['land']['mean'])} m", UMBER, f"average height of the land\n({fmt(R['noant']['mean'])} m without Antarctica)"),
        (pc(R["land"]["above"]["2000"]), RUST, "of the land is more than\n2,000 m above sea level"),
        (pc(R["cities"]["share_above"]["2000"], 1), MOSS, "of people in listed cities\nlive above 2,000 m"),
        (pc(R["earth"]["above0"], 1), ICE, "of the Earth's surface is\nabove sea level at all")]
for i, (big, col, small) in enumerate(nums):
    x = .04 + i * .24
    fig.text(x, .415, big, fontproperties=DISP, fontsize=40, color=col, va="top")
    fig.text(x, .37, small, fontsize=11, color=FG, va="top", linespacing=1.4)

# panels
a1 = fig.add_axes([.07, .145, .26, .145]); a1.set_facecolor(CBG)
cv = np.array(R["curve"])
for k in range(len(cv) - 1):
    a1.add_patch(Rectangle((0, cv[k, 0]), cv[k, 1] * 100, cv[k + 1, 0] - cv[k, 0], fc=land_rgb(cv[k, 0]), ec="none"))
a1.plot(cv[:, 1] * 100, cv[:, 0], color=FG, lw=1.6)
for m in ("1000", "2000", "3000", "5000"):
    v = R["land"]["above"][m] * 100; a1.plot(v, int(m), "o", color=FG, ms=4)
    a1.annotate(f"{v:.{1 if v < 1 else 0}f}% > {int(m):,} m", (v, int(m)), xytext=(7, 3), textcoords="offset points", fontsize=9.5)
a1.set_xlim(0, 100); a1.set_ylim(0, 7000); style(a1, axis="y")
a1.set_xlabel("% of the world's land higher than this", fontsize=9.5); a1.set_ylabel("metres", fontsize=9.5)
a1.set_title("How much land is above each height", loc="left", fontsize=12, pad=10)

a2 = fig.add_axes([.47, .145, .18, .145]); a2.set_facecolor(CBG)
hi = R["countries"]["high"][:8][::-1]
a2.barh(range(len(hi)), [c["mean"] for c in hi], color=[land_rgb(c["mean"]) for c in hi], edgecolor="#00000040")
a2.set_yticks(range(len(hi)), [c["name"] for c in hi], fontsize=10)
for i, c in enumerate(hi): a2.text(c["mean"] + 50, i, fmt(c["mean"]), va="center", fontsize=9.5)
a2.set_xlim(0, 3700); style(a2); a2.tick_params(axis="x", labelsize=8.5)
a2.set_title("Highest countries\naverage height, m", loc="left", fontsize=12, pad=10)

a3 = fig.add_axes([.8, .145, .15, .145]); a3.set_facecolor(CBG)
ct = R["cities"]["top_million"][:8][::-1]
a3.barh(range(len(ct)), [c["elev"] for c in ct], color=[land_rgb(c["elev"]) for c in ct], edgecolor="#00000040")
a3.set_yticks(range(len(ct)), [c["name"] for c in ct], fontsize=10)
for i, c in enumerate(ct): a3.text(c["elev"] + 50, i, fmt(c["elev"]), va="center", fontsize=9.5)
a3.set_xlim(0, 3800); style(a3); a3.tick_params(axis="x", labelsize=8.5)
a3.set_title("Highest cities of\n1 million+, m", loc="left", fontsize=12, pad=10)

fig.text(.04, .012, "Sources: AWS Terrain Tiles (Mapzen Terrarium: SRTM, GMTED2010, ETOPO1 and others; see github.com/tilezen/joerd attribution);\n"
         "zoom 4 grid of about 10 km, statistics weighted by true area, lakes excluded; ETOPO10 south of 85° S. Peaks and cities: Wikidata (CC0),\n"
         "Natural Earth, Wikipedia. Countries ranked if they cover 100+ grid cells. Chinese prefecture-level 'cities'\nranked only if Natural Earth gives their urban area 1 million+.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib  ·  maps.tristanhotham.com/world-terrain",
         fontsize=9, color=MUT, linespacing=1.55, va="bottom")
outp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "how_high_is_the_world.png")
fig.savefig(outp, facecolor=CBG, dpi=250)
print("ok", outp)
