import { defineConfig } from "vite";

// Read GOOGLE_TILES_API_KEY from the project-root .env
export default defineConfig({ envDir: "..", envPrefix: ["VITE_", "GOOGLE_TILES_"] });
