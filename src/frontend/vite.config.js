import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs on uvicorn (port 8000). Proxying /api keeps the browser
// on one origin, so no CORS setup is needed while developing.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_TARGET || "http://127.0.0.1:8000",
    },
  },
});
