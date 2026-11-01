## Title

[OC] How high is the world? Only 11% of Earth's land is above 2,000 m, and only 1.9% of people in its cities live that high

## Body

I mapped height above sea level for the whole planet from the open AWS Terrain Tiles (SRTM, GMTED2010, ETOPO1 and national surveys), with every 10 km cell weighted by its true area. The world's land averages 807 m (678 m without Antarctica's ice); half of it is below 432 m, 26% is above 1,000 m and 0.5% above 5,000 m. Highest countries on average: Tajikistan (2,961 m), Bhutan, Kyrgyzstan; lowest: the Netherlands (10 m). Of 2.6 billion people in 4,325 Wikidata cities, half live below 92 m. Caveat: a 10 km grid smooths peaks (the highest cell is 6,727 m) and city populations come from Wikidata, where Chinese 'cities' include their surrounding prefectures. Interactive map, where you can click anywhere for its height: https://maps.tristanhotham.com/world-terrain/

## Source comment

Source: AWS Terrain Tiles, Terrarium format (Mapzen; SRTM, GMTED2010, ETOPO1, NED/3DEP, EU-DEM, OS Terrain 50 and others; attribution at github.com/tilezen/joerd), zoom 4 grid; ETOPO10 for Antarctica south of 85° S; peaks and cities from Wikidata (CC0), with Natural Earth elevation points and Wikipedia's list of peaks by prominence (CC BY-SA 4.0); Natural Earth countries and lakes (public domain).

Tools: Python (numpy, rasterio, pyproj, matplotlib); Leaflet for the interactive map, which decodes the terrain tiles live in the browser.

Interactive version: https://maps.tristanhotham.com/world-terrain/
Paper: https://doi.org/10.5281/zenodo.23848930
Blog post: https://blog.tristanhotham.com/2026/10/31/world-terrain/
