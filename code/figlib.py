"""Shared drawing helpers for the figures, the header and the collage: fonts, the page's hypsometric palette, and a
shaded-relief world image built from the zoom 4 grid (resampled from Web Mercator to longitude and latitude, Antarctica
south of 85.05 S from ETOPO10) and reprojected to Equal Earth."""
import os, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import ListedColormap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(os.path.join(FONTS, f))
DISP = fm.FontProperties(fname=os.path.join(FONTS, "FrauncesVar.ttf"), weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
plt.rcParams.update({"font.family": MONO, "font.size": 11})
BG, FG, MUT, RULE, PAPER = "#F6F3EC", "#1F1B17", "#665E55", "#DDD5C6", "#FCFAF5"
UMBER, MOSS, ICE, RUST = "#8A4F2E", "#4E7446", "#33688C", "#B4532A"
LAND = [(0, (168, 198, 150)), (100, (186, 208, 158)), (250, (208, 220, 168)), (500, (234, 227, 178)), (1000, (232, 207, 152)), (1500, (216, 180, 128)),
        (2000, (198, 154, 112)), (3000, (174, 130, 104)), (4000, (156, 126, 122)), (5000, (190, 180, 186)), (6000, (228, 226, 232)), (7000, (250, 250, 252))]
SEA = [(-11000, (104, 142, 186)), (-6000, (134, 172, 208)), (-3000, (160, 195, 223)), (-1000, (182, 211, 231)), (-200, (201, 224, 237)), (0, (216, 233, 241))]
LOWLAND = (112, 158, 138)


def ramp(stops, x):
    x = np.asarray(x, float); xs = [s[0] for s in stops]; cs = np.array([s[1] for s in stops]) / 255
    return np.stack([np.interp(x, xs, cs[:, k]) for k in range(3)], axis=-1).astype(np.float32)


land_rgb = lambda h: ramp(LAND, h)
sea_rgb = lambda h: ramp(SEA, h)
hexc = lambda h: matplotlib.colors.to_hex(land_rgb(h))
LAND_CMAP = ListedColormap(land_rgb(np.linspace(0, 7000, 256)))


def style(ax, grid=True, axis="x"):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(MUT)
    ax.tick_params(colors=FG, labelsize=10)
    if grid: ax.grid(axis=axis, color=RULE, lw=.8); ax.set_axisbelow(True)


def lonlat_grid(res=0.075):
    """Heights and a land mask on a regular longitude/latitude grid (cached)."""
    fn = f"{WORK}/lonlat_{res}.npz"
    if os.path.exists(fn):
        z = np.load(fn); return z["h"], z["land"], z["lat"], z["lon"]
    E = np.load(f"{WORK}/elev.npy").astype(np.float32)
    nx, ny = int(round(360 / res)), int(round(180 / res))
    lon = -180 + (np.arange(nx) + .5) * res; lat = 90 - (np.arange(ny) + .5) * res
    r, _ = rc_of(0, np.clip(lat, -MERC_LAT + 1e-6, MERC_LAT - 1e-6)); r = r - .5
    c = (lon + 180) / 360 * N - .5
    r0 = np.clip(np.floor(r).astype(int), 0, N - 2); ty = np.clip(r - r0, 0, 1)[:, None]
    c0 = np.floor(c).astype(int) % N; c1 = (c0 + 1) % N; tx = (c - np.floor(c))[None, :].astype(np.float32)
    h = np.empty((ny, nx), np.float32)
    for a in range(0, ny, 400):
        b = slice(a, a + 400); R0, T = r0[b], ty[b]
        h[b] = (E[R0][:, c0] * (1 - tx) + E[R0][:, c1] * tx) * (1 - T) + (E[R0 + 1][:, c0] * (1 - tx) + E[R0 + 1][:, c1] * tx) * T
    # polar caps from ETOPO10
    e10 = np.fromfile(ETOPO10, "<i2").reshape(1081, 2161)[:, :2160].astype(np.float32)
    pol = np.abs(lat) > MERC_LAT - .05
    ri = np.clip(np.round((90 - lat[pol]) * 6).astype(int), 0, 1080); ci = np.clip(np.floor((lon + 180) * 6).astype(int), 0, 2159)
    h[pol] = e10[ri][:, ci]
    # land: Natural Earth countries less lakes
    import rasterio.features, rasterio.transform
    from shapely.geometry import shape
    T = rasterio.transform.from_origin(-180, 90, res, res)
    shp = [(shape(f["geometry"]), 1) for f in jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]]
    land = rasterio.features.rasterize(shp, out_shape=(ny, nx), transform=T, fill=0, dtype="uint8")
    lk = [(shape(f["geometry"]), 1) for f in jload(f"{PEAKS_X}/ne_10m_lakes.geojson")["features"] if f["properties"]["featurecla"] in ("Lake", "Reservoir")]
    lakes = rasterio.features.rasterize(lk, out_shape=(ny, nx), transform=T, fill=0, dtype="uint8")
    land = (land > 0) & (lakes == 0)
    np.savez(fn, h=h, land=land, lat=lat, lon=lon)
    return h, land, lat, lon


def hillshade(h, lat, res, exag=14.0, az=315, alt=42):
    dy = res * 111320.0; dx = dy * np.cos(np.radians(lat))[:, None]
    gy, gx = np.gradient(h.astype(np.float32))
    sx = gx / dx * exag; sy = -gy / dy * exag          # rows run north to south
    slope = np.arctan(np.hypot(sx, sy)); aspect = np.arctan2(sy, -sx)
    azm = np.radians(360 - az + 90); zen = np.radians(90 - alt)
    hs = np.cos(zen) * np.cos(slope) + np.sin(zen) * np.sin(slope) * np.cos(azm - aspect)
    return np.clip(hs, 0, 1).astype(np.float32)


def relief_rgb(h, land, lat, res, exag=14.0, sea_k=.35, sea_on=True, light_sea=False):
    """RGB relief image (0..1): hypsometric tints times shading on land, a lighter shaded sea."""
    hs = hillshade(np.where(land | (h > 0), h, h * sea_k), lat, res, exag)
    img = np.empty(h.shape + (3,), np.float32)
    lnd = land | (h > 0)
    img[lnd] = land_rgb(np.maximum(h[lnd], 0))
    low = land & (h < 0)
    img[low] = np.array(LOWLAND) / 255
    if sea_on:
        s = sea_rgb(h[~lnd])
        if light_sea: s = s * .55 + np.array([.93, .95, .96]) * .45
        img[~lnd] = s
    else:
        img[~lnd] = np.array([.93, .95, .96])
    f = np.where(lnd, .5 + .62 * hs, .86 + .16 * hs)[..., None]
    return np.clip(img * f, 0, 1)


def equal_earth(img, lat, lon, width, lat_min=-90, lat_max=90, bg=(1, 1, 1)):
    """Reproject a lon/lat image to Equal Earth (EPSG 8857). Returns RGBA, extent (x0, x1, y0, y1) and a lon/lat -> x/y function."""
    from pyproj import Transformer
    fwd = Transformer.from_crs(4326, 8857, always_xy=True); inv = Transformer.from_crs(8857, 4326, always_xy=True)
    X0, _ = fwd.transform(-180, 0); X1, _ = fwd.transform(180, 0)
    _, Y0 = fwd.transform(0, lat_min); _, Y1 = fwd.transform(0, lat_max)
    height = int(round(width * (Y1 - Y0) / (X1 - X0)))
    xs = np.linspace(X0, X1, width); ys = np.linspace(Y1, Y0, height)
    out = np.zeros((height, width, 4), np.float32)
    res = lat[0] - lat[1]
    for a in range(0, height, 300):
        XX, YY = np.meshgrid(xs, ys[a:a + 300])
        lo, la = inv.transform(XX, YY)
        ok = np.isfinite(lo) & np.isfinite(la) & (np.abs(lo) <= 180)
        xb, _ = fwd.transform(np.where(ok, lo, 0), np.where(ok, la, 0))
        ok &= np.abs(xb - XX) < 1000
        ri = np.clip(((lat[0] + res / 2 - la) / res).astype(int), 0, len(lat) - 1)
        ci = np.clip(((lo + 180) / res).astype(int), 0, len(lon) - 1)
        blk = img[ri, ci]; blk[~ok] = bg
        out[a:a + 300, :, :3] = blk; out[a:a + 300, :, 3] = ok
    return out, (X0, X1, Y0, Y1), lambda lo, la: fwd.transform(lo, la)
