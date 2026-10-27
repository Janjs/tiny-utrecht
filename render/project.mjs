// Projects OSM water polygons into canvas pixels with the renderer's exact camera.
// in: ../data/osm_water.json (Overpass "out geom")  out: ../data/water_px.json
import { readFileSync, writeFileSync } from "node:fs";
import { WGS84_ELLIPSOID, CAMERA_FRAME } from "3d-tiles-renderer";
import { Matrix4, Vector3, MathUtils } from "three";

const view = JSON.parse(readFileSync(new URL("./view.json", import.meta.url)));
const WATER_HEIGHT_M = 44; // ellipsoid height of canal water: geoid ~43.5 m + NAP ~0.5 m
const [ox, oy] = view.origin_px; // canvas top-left relative to the camera centre
const s = view.meters_per_px;

const camWorld = new Matrix4();
WGS84_ELLIPSOID.getObjectFrame(
  view.lat * MathUtils.DEG2RAD, view.lon * MathUtils.DEG2RAD, view.target_height_m,
  view.azimuth_deg * MathUtils.DEG2RAD, view.elevation_deg * MathUtils.DEG2RAD, 0,
  camWorld, CAMERA_FRAME,
);
camWorld.multiply(new Matrix4().makeTranslation(0, 0, 5000));
const camInv = camWorld.clone().invert();

const v = new Vector3();
export function toPixel(lat, lon, h = WATER_HEIGHT_M) {
  WGS84_ELLIPSOID.getCartographicToPosition(lat * MathUtils.DEG2RAD, lon * MathUtils.DEG2RAD, h, v);
  v.applyMatrix4(camInv);
  return [v.x / s - ox, -v.y / s - oy];
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop())) main();

function main() {
const ring = (geom) => geom.map((p) => toPixel(p.lat, p.lon).map((n) => Math.round(n * 10) / 10));
const osm = JSON.parse(readFileSync(new URL("../data/osm_water.json", import.meta.url)));
const polys = [];
for (const el of osm.elements) {
  if (el.type === "way" && el.geometry) polys.push({ id: `w${el.id}`, outer: [ring(el.geometry)], inner: [] });
  if (el.type === "relation") {
    const members = el.members.filter((m) => m.geometry);
    polys.push({
      id: `r${el.id}`,
      outer: members.filter((m) => m.role !== "inner").map((m) => ring(m.geometry)),
      inner: members.filter((m) => m.role === "inner").map((m) => ring(m.geometry)),
    });
  }
}
writeFileSync(new URL("../data/water_px.json", import.meta.url), JSON.stringify(polys));
console.log(`${polys.length} polygons`, "Dom tower ->", toPixel(52.0907, 5.1214, 46));
}
