import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1420, strictPort: true },
  // Signing/build secrets prefixed with TAURI_ must never become frontend data.
  envPrefix: ["VITE_"],
});
