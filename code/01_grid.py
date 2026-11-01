"""Step 1. The zoom 4 terrain grid, the land and country masks, and the Antarctic cap.

- Mosaics the 256 Terrarium tiles at zoom 4 into one 4096 x 4096 Web Mercator grid of heights (metres).
- Rasterises Natural Earth 10m countries (less its lakes and reservoirs, also from Natural Earth) at twice that resolution (8192 x 8192) so each zoom 4 cell gets the share of
  its area that is land and the country covering most of it.
- Web Mercator stops at 85.05 degrees, so the part of Antarctica south of that line is taken from ETOPO10 (ice surface).
Outputs (WORK): elev.npy, landfrac.npy, ctry.npy (index into countries.json), cap.npz, countries.json
Run: python3 code/01_grid.py
"""
import numpy as np, shapely
from PIL import Image
import rasterio.features, rasterio.transform
from shapely.geometry import shape, box, mapping
from pyproj import Transformer
from common import *

# ---- heights ----
elev = np.zeros((N, N), np.float32)
for x in range(16):
    for y in range(16):
        a = np.asarray(Image.open(f"{TILES}/4/{x}/{y}.png").convert("RGB"), np.float64)
        elev[y * 256:(y + 1) * 256, x * 256:(x + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
# despike: a handful of corrupt cells (for example 11,500 m on Baffin Island) differ from their neighbours by kilometres
from scipy.ndimage import median_filter
med = median_filter(elev, size=3, mode="nearest")
d = elev - med
# high spikes on land or shelf, or deep holes in shallow ground; atolls (a few metres high amid deep ocean) are real and kept
spike = ((d > 2500) & (med > -500)) | ((d < -2500) & (med > -1000))
print("spikes replaced by the median of their neighbours:", int(spike.sum()), [(int(r), int(c), float(elev[r, c]), float(med[r, c])) for r, c in zip(*np.where(spike))][:10])
spike_max = float(elev[spike].max()) if spike.any() else None
elev[spike] = med[spike]
np.save(f"{WORK}/elev.npy", elev)
jsave({"n_spikes": int(spike.sum()), "spike_max": spike_max}, f"{WORK}/grid_meta.json")
print("heights", elev.min(), elev.max())

# ---- countries at 2x ----
F = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
tr = Transformer.from_crs(4326, 3857, always_xy=True)
HALF = 20037508.342789244
clipbox = box(-180, -MERC_LAT, 180, MERC_LAT)
C = [None]
shapes = []
for f in F:
    p = f["properties"]
    g = shape(f["geometry"]).buffer(0)
    C.append(dict(i=len(C), a3=p["ADM0_A3"], iso=p["ISO_A3"] if p["ISO_A3"] != "-99" else p["ADM0_A3"], name=p["NAME_LONG"] or p["NAME"],
                  short=p["NAME"], qid=p.get("WIKIDATAID"), cont=p["CONTINENT"], sub=p.get("SUBREGION"), sov=p["SOV_A3"], type=p["TYPE"],
                  pop=p.get("POP_EST"), lon=p.get("LABEL_X"), lat=p.get("LABEL_Y"), area_ne=g.area))
    gc = g.intersection(clipbox)
    if gc.is_empty:
        continue
    shapes.append((shapely.transform(gc, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1]))), len(C) - 1))
M = 2 * N
T = rasterio.transform.from_origin(-HALF, HALF, 2 * HALF / M, 2 * HALF / M)
fine = rasterio.features.rasterize(shapes, out_shape=(M, M), transform=T, fill=0, dtype="int16")
# lakes and reservoirs are water, not land (salt pans such as Kati Thanda-Lake Eyre, often dry, stay land)
lakes = []
for f in jload(f"{PEAKS_X}/ne_10m_lakes.geojson")["features"]:
    if f["properties"]["featurecla"] in ("Lake", "Reservoir"):
        g = shape(f["geometry"]).buffer(0).intersection(clipbox)
        if not g.is_empty:
            lakes.append((shapely.transform(g, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1]))), 1))
lake = rasterio.features.rasterize(lakes, out_shape=(M, M), transform=T, fill=0, dtype="uint8")
print("lake sub-cells removed from land:", int(((lake > 0) & (fine > 0)).sum()))
fine[lake > 0] = 0
lake_frac = lake.reshape(N, 2, N, 2).mean(axis=(1, 3)).astype(np.float32)
np.save(f"{WORK}/lakefrac.npy", lake_frac)
del lake
sub = fine.reshape(N, 2, N, 2).transpose(0, 2, 1, 3).reshape(N, N, 4)
landfrac = (sub > 0).sum(-1) / 4.0
# majority country of each cell (ties: first sub-cell)
ctry = np.zeros((N, N), np.int16)
for k in range(4):
    v = sub[..., k]
    cnt = (sub == v[..., None]).sum(-1)
    take = (v > 0) & (cnt > ((sub == ctry[..., None]).sum(-1) * (ctry > 0)))
    ctry[take] = v[take]
np.save(f"{WORK}/landfrac.npy", landfrac.astype(np.float32))
np.save(f"{WORK}/ctry.npy", ctry)
np.save(f"{WORK}/ctry_fine.npy", fine)

# ---- cell areas (km2): exact for a Mercator row between its two latitudes ----
lat_e = lat_of_row(np.arange(N + 1))
row_area = R_EARTH ** 2 * np.radians(360 / N) * (np.sin(np.radians(lat_e[:-1])) - np.sin(np.radians(lat_e[1:])))
np.save(f"{WORK}/row_area.npy", row_area)

# ---- Antarctic cap from ETOPO10 (ice surface), rows south of the Mercator limit ----
e10 = np.fromfile(ETOPO10, "<i2").reshape(1081, 2161)   # rows run from 90 N (first) to 90 S (last), checked at Everest
lat10 = 90 - np.arange(1081) / 6.0                            # cell centres, 90N .. 90S
cap_rows = np.where(lat10 < -MERC_LAT)[0]
cap = e10[cap_rows][:, :2160].astype(np.float64)
cl = lat10[cap_rows]
lo = np.clip(cl - 1 / 12, -90, None); hi = np.minimum(cl + 1 / 12, -MERC_LAT)
cap_area = (R_EARTH ** 2 * np.radians(1 / 6) * (np.sin(np.radians(hi)) - np.sin(np.radians(lo))))[:, None] * np.ones((1, 2160))
np.savez(f"{WORK}/cap.npz", elev=cap, area=cap_area)
print("cap", cap.shape, round(cap_area.sum()), "km2, mean", round((cap * cap_area).sum() / cap_area.sum()))

# checks
A = row_area[:, None] * landfrac
print("land area in grid", round(A.sum() / 1e6, 2), "M km2; plus cap", round(cap_area.sum() / 1e6, 2))
for nm, lon, lat in [("Everest", 86.925, 27.988), ("Caspian", 50.5, 42.0), ("Dead Sea", 35.5, 31.5), ("Lake Victoria", 33.0, -1.0), ("Lake Superior", -87.5, 47.7)]:
    r, c = rc_of(lon, lat); r, c = int(r), int(c)
    print(nm, elev[r, c], "landfrac", landfrac[r, c], "ctry", C[ctry[r, c]]["name"] if ctry[r, c] else None)
for c in C[1:]:
    c.pop("area_ne")
jsave(C, f"{WORK}/countries.json")
