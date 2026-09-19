import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API key never reaches the browser: the frontend only talks to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } } },
});
