# Tiny Utrecht

An isometric pixel-art map of central Utrecht, after [tiny.london](https://tiny.london/how/):
3.0 × 1.8 km at 0.293 m per pixel (10,240 × 6,144 px), from Lombok to Wilhelminapark.

## How it is made

1. **Render** (`render/`): one orthographic camera (45° tilt, 15° turn) renders Google's
   Photorealistic 3D Tiles in 2048 px shots that line up to the pixel. `node render/capture.mjs`
2. **Water** (`render/project.mjs`, `scripts/water.py`): OpenStreetMap water polygons projected
   with the same camera, used to tell the model where water is and to check its drawings.
3. **Drawing** (`scripts/teacher.py --grid`): Gemini 3 Pro Image redraws 84 overlapping 1024 px
   tiles as pixel art. Each drawing is checked against the render and OSM (photo copy, invented
   water, water colour, colour cast, blank areas) and redrawn up to 3 times.
4. **Map** (`scripts/assemble.py`): tiles cross-fade over their overlaps; the Dom tower, under
   scaffolding in Google's mesh, is patched from a hand-checked drawing.
5. **Site** (`scripts/make_dzi.py`, `site/`): a Deep Zoom pyramid shown with OpenSeadragon, with
   live Utrecht weather from Open-Meteo.

Keys go in `.env`: `GOOGLE_TILES_API_KEY`, `GEMINI_API_KEY`.

## Run the site

```bash
docker build -t tiny-utrecht . && docker run -p 8080:80 tiny-utrecht
```

nginx serves `site/` and proxies `/api/weather` to Open-Meteo, cached for an hour for all visitors.

## Credits

Map imagery derived from Google Photorealistic 3D Tiles (Map data ©2026 Google). Water © OpenStreetMap
contributors, ODbL. Weather by Open-Meteo. Pipeline after Andy Coenen's
[isometric-nyc](https://github.com/cannoneyed/isometric-nyc) and Boris Starkov's tiny.london.
