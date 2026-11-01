"""Shared paths and helpers for the world-terrain study.

Raw inputs (read in place, never copied into the repo):
  TILES   AWS Terrain Tiles, Terrarium encoding, zoom 4 (16 x 16 tiles of 256 px, Web Mercator):
          TILES/4/{x}/{y}.png, height_m = R*256 + G + B/256 - 32768.
          Live copies: https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png
  ETOPO10 10 arc minute ice-surface grid derived from ETOPO1 (fills Antarctica south of the Mercator limit, 85.05 S)
  PEAKS   Wikidata mountains, hills, summits and volcanoes (P2044 elevation, P2660 prominence, P625, P17, sitelinks)
  PEAKS_X supplements fetched from GitHub (see 02_peaks.py): Natural Earth elevation points, the Wikipedia list of
          peaks by prominence (as tabulated by ianto-cannon.github.io), and a peakbagger list of country high points
          used only as an independent check, never redistributed.
  CITIES  Wikidata cities of 50,000 or more with elevation and population
  GEO     Natural Earth countries (10m, with WIKIDATAID) and populated places; Natural Earth 10m lakes in PEAKS_X
          (https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_lakes.geojson)
Intermediates are written to WORK (outside the repo by default)."""
import json, os, re, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW3 = os.environ.get("TERRAIN_RAW", "/home/claude/newdata/raw3")
TILES = os.path.join(RAW3, "terrarium_z4")
ETOPO10 = os.path.join(RAW3, "dem", "etopo10", "etopo10_ice_g_i2.bin")
PEAKS = os.path.join(RAW3, "peaks.tsv")
PEAKS_X = os.path.join(RAW3, "peaks_extra")
CITIES = os.path.join(RAW3, "city_elevations.tsv")
GEO = os.environ.get("TERRAIN_GEO", "/home/claude/newdata/raw/geo")
FONTS = os.environ.get("FONT_DIR", "/home/claude/ref/fonts")
DATA = os.path.join(ROOT, "data")
PAGE = os.path.join(DATA, "page")
WORK = os.environ.get("TERRAIN_WORK", "/dev/shm/world-terrain")
for d in (DATA, PAGE, WORK):
    os.makedirs(d, exist_ok=True)

SLUG = "world-terrain"
PAGE_URL = "https://maps.tristanhotham.com/world-terrain/"
REPO = "https://github.com/Tristan-Hotham/world-terrain"
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")

Z = 4
N = 256 * 2 ** Z           # 4096 pixels around the world
R_EARTH = 6371.0088        # mean radius, km (for areas)
MERC_LAT = math.degrees(math.atan(math.sinh(math.pi)))   # 85.0511
THRESH = [0, 200, 500, 1000, 1500, 2000, 3000, 4000, 5000]


def dash(v):
    """House style: no em or en dashes, no double hyphens, in anything written to data/."""
    if isinstance(v, str):
        v = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", v)
        v = v.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-")
        while "--" in v:
            v = v.replace("--", "-")
        return v
    if isinstance(v, list):
        return [dash(x) for x in v]
    if isinstance(v, dict):
        return {k: dash(x) for k, x in v.items()}
    return v


def _np(o):
    import numpy as np
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, np.floating): return float(o)
    if isinstance(o, np.bool_): return bool(o)
    if isinstance(o, np.ndarray): return o.tolist()
    raise TypeError(type(o))


def jsave(obj, path, indent=None):
    if os.path.abspath(path).startswith(DATA):
        obj = dash(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"), default=_np)


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tsv(path):
    """Parse a QLever TSV export into a list of dicts with plain values (entity ids as Q-numbers, literals unquoted)."""
    lines = open(path, encoding="utf-8").read().rstrip("\n").split("\n")
    head = [h.lstrip("?") for h in lines[0].split("\t")]
    out = []
    for ln in lines[1:]:
        f = ln.split("\t")
        row = {}
        for h, v in zip(head, f + [""] * (len(head) - len(f))):
            v = v.strip()
            if v.startswith("<http://www.wikidata.org/entity/"):
                v = v[len("<http://www.wikidata.org/entity/"):-1]
            elif v.startswith("<") and v.endswith(">"):
                v = v[1:-1]
            else:
                m = re.match(r'^"(.*)"(@[\w-]+|\^\^<[^>]+>)?$', v, re.S)
                if m:
                    v = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
            row[h] = v
        out.append(row)
    return out


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def point(wkt):
    m = re.match(r"POINT\(([-\d.eE]+) ([-\d.eE]+)\)", wkt or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


# Web Mercator pixel helpers for the zoom 4 grid
def lat_of_row(j):
    """Latitude of the top edge of row j (0..N) on the zoom 4 grid."""
    import numpy as np
    return np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * np.asarray(j, float) / N))))


def rc_of(lon, lat):
    """Row and column (floats) of a lon/lat point on the zoom 4 grid."""
    import numpy as np
    lat = np.clip(np.asarray(lat, float), -MERC_LAT + 1e-9, MERC_LAT - 1e-9)
    x = (np.asarray(lon, float) + 180) / 360 * N
    y = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * N
    return y, x


def hav(lon1, lat1, lon2, lat2):
    import numpy as np
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(a))
