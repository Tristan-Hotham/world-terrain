# How high is the world?

A detailed world map of height above sea level, drawn live in the browser from the open AWS Terrain Tiles at every zoom (height tints, shaded relief, height steps, a readout of any point), with the world's peaks and cities by height, and a study of how high the land is and how high people live.

**Interactive version:** https://maps.tristanhotham.com/world-terrain/

**Paper and archived release:** {https://doi.org/10.5281/zenodo.23848930}

**Blog post:** {https://blog.tristanhotham.com/2026/10/31/world-terrain/}

A data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- The world's land averages 807 m above sea level (median 432 m), or 678 m without Antarctica's ice. 45% of it lies above 500 m, 26% above 1,000 m, 11% above 2,000 m, 5% above 3,000 m, 1.8% above 4,000 m and 0.5% above 5,000 m.
- Continents: Antarctica 2,208 m, Asia 1,059 m, North America 740 m, Africa 629 m, South America 587 m, Europe 370 m, Oceania 301 m. 29.6% of the Earth's whole surface is above sea level.
- Countries (of 161 covering at least 100 grid cells): highest Tajikistan (2,961 m), Bhutan (2,763 m), Kyrgyzstan (2,683 m), Lesotho (2,218 m); lowest the Netherlands (10 m). United Kingdom 158 m.
- People live low: of 2.6 billion people in 4,325 Wikidata cities of 50,000 or more, half live below 92 m, 10.3% above 1,000 m and 1.9% above 2,000 m. Highest city of a million or more: Quito (2,850 m); highest capital La Paz (3,640 m).
- Below sea level: 355,893 km² in named depressions on the 10 km grid, 76% of it around the Caspian; then Qattara, Kati Thanda-Lake Eyre, the Netherlands and Afar.
- Peaks: 134,657 summits after cleaning; the highest point of 189 countries confirmed against an independent list.

Every number is in `data/results.json`, which the page, paper, blog and collage are built from.

## Method in brief

- **Terrain.** AWS Terrain Tiles (Terrarium encoding: height = R × 256 + G + B / 256 − 32,768 m). The page decodes them live at zoom 0 to 14. The statistics use zoom 4, a 4,096 × 4,096 Web Mercator grid (9.8 km at the equator, 4.9 km at 60°), each cell weighted by its exact area on a sphere; 13 corrupt cells replaced by their neighbours' median. Antarctica south of 85.05° S from ETOPO10.
- **Land.** Natural Earth 1:10m countries less lakes and reservoirs, rasterised at twice the grid's resolution. Coastal cells are floored at 0 m; only wholly-land interior cells can be below sea level. Ice counts at its surface.
- **Peaks.** Every Wikidata mountain, hill, summit and volcano with a height (136,410 items, heights normalised to metres from their stated units), plus 89 summits from Natural Earth elevation points and 3 from Wikipedia's 125 most prominent summits (which also give the prominence ranking); every height checked against the 10 km cells around it, feet and kilometres converted, implausible values dropped, and country high points checked against a peakbagger.com list (not republished).
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
| `data/peaks.csv` | 134,657 cleaned summits: height and prominence with their sources, point, countries, kind, sitelinks, the check applied and the grid heights around them. |
| `data/cities.csv` | 4,325 cleaned cities: height, population, point, country, grid height and check. |
| `data/results.json` | Every number used anywhere. |
| `data/page/` | Page files: borders, peaks (the 15,000 best known first, the rest loaded when zoomed in), cities, place names, country figures. |
| `code/` | Numbered scripts (below), page, paper and blog templates. |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |
| `release/` | Paper PDF and LaTeX (its figures are the blog figures), blog post and figures, Zenodo metadata (with the list of files to upload) and the code-and-data zip. |
| `qa/` | Screenshots from the last check of the page. |

## Known limits

- The statistics are smoothed to about 10 km: the highest cell is 6,727 m, 2,122 m below Everest's summit. Small countries (under 100 cells) are only roughly resolved and are not ranked.
- Coastal cells are floored at sea level, hiding small coastal depressions; another 89,568 km² of patches below 0 m on deltas and coasts is not counted.
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

Hotham, T. (2026) How high is the world? Height above sea level, mountains and where people live, from open terrain data. Zenodo. {https://doi.org/10.5281/zenodo.23848930}

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
