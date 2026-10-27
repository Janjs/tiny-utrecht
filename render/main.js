// One orthographic camera for the whole canvas. A shot is a sub-rectangle of
// its frustum, so shots line up to the pixel without moving the camera.
import { TilesRenderer, WGS84_ELLIPSOID, CAMERA_FRAME } from "3d-tiles-renderer";
import { GoogleCloudAuthPlugin, GLTFExtensionsPlugin, TileCompressionPlugin } from "3d-tiles-renderer/plugins";
import { Matrix4, Scene, WebGLRenderer, OrthographicCamera, MathUtils } from "three";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import view from "./view.json";

const params = new URLSearchParams(location.search);
const col = parseInt(params.get("col") ?? "1");
const row = parseInt(params.get("row") ?? "1");
const shot = parseInt(params.get("shot") ?? view.shot_px);
const errorTarget = parseFloat(params.get("error") ?? "2");
const overview = params.has("overview");
// overview: the whole canvas in one small shot, for checking the framing
const [W, H] = overview ? [shot, shot] : view.canvas_px;
// top-left of the canvas relative to the camera's centre point, in pixels; widening the canvas
// to the right or bottom keeps every existing pixel where it was
const [ox, oy] = overview ? [-W / 2, -H / 2] : view.origin_px;
const s = overview ? (view.canvas_px[0] * view.meters_per_px) / shot : view.meters_per_px;

const renderer = new WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setClearColor(0x87ceeb);
renderer.setPixelRatio(1);
renderer.setSize(shot, shot);
document.body.appendChild(renderer.domElement);

const scene = new Scene();
const camera = new OrthographicCamera(-1, 1, 1, -1, 1, 20000);
WGS84_ELLIPSOID.getObjectFrame(
  view.lat * MathUtils.DEG2RAD, view.lon * MathUtils.DEG2RAD, view.target_height_m,
  view.azimuth_deg * MathUtils.DEG2RAD, view.elevation_deg * MathUtils.DEG2RAD, 0,
  camera.matrixWorld, CAMERA_FRAME,
);
camera.matrixWorld.multiply(new Matrix4().makeTranslation(0, 0, 5000));
camera.matrixWorld.decompose(camera.position, camera.quaternion, camera.scale);

const left = overview ? ox * s : (ox + col * shot) * s;
const top = overview ? -oy * s : (-oy - row * shot) * s;
Object.assign(camera, { left, right: left + shot * s, top, bottom: top - shot * s });
camera.updateProjectionMatrix();
camera.updateMatrixWorld(true);

const tiles = new TilesRenderer();
tiles.registerPlugin(new GoogleCloudAuthPlugin({ apiToken: import.meta.env.GOOGLE_TILES_API_KEY, autoRefreshToken: true }));
tiles.registerPlugin(new TileCompressionPlugin());
tiles.registerPlugin(new GLTFExtensionsPlugin({
  dracoLoader: new DRACOLoader().setDecoderPath("https://unpkg.com/three@0.153.0/examples/jsm/libs/draco/gltf/"),
}));
tiles.errorTarget = errorTarget;
tiles.lruCache.maxSize = 40000;
tiles.lruCache.minSize = 20000;
if ("maxBytesSize" in tiles.lruCache) tiles.lruCache.maxBytesSize = 4e9;
tiles.setCamera(camera);
tiles.setResolution(camera, shot, shot);
scene.add(tiles.group);

window.TILES_LOADED = false;
let stableSince = 0;
let frames = 0;
function animate() {
  requestAnimationFrame(animate);
  tiles.update();
  renderer.render(scene, camera);
  frames++;
  const busy = tiles.stats.downloading + tiles.stats.parsing + (tiles.stats.queued ?? 0);
  if (busy === 0 && frames > 60) {
    stableSince ||= performance.now();
    window.TILES_LOADED = performance.now() - stableSince > 2000;
  } else {
    stableSince = 0;
    window.TILES_LOADED = false;
  }
}
animate();
window.capture = () => renderer.domElement.toDataURL("image/png");
window.tiles = tiles; window.camera = camera;
