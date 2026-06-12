import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/health": { target: "http://localhost:8000", changeOrigin: true },
      "/metrics": { target: "http://localhost:8000", changeOrigin: true },
      "/ingest": { target: "http://localhost:8000", changeOrigin: true },
      "/bootstrap-demo": { target: "http://localhost:8000", changeOrigin: true },
      "/audit": { target: "http://localhost:8000", changeOrigin: true },
      "/feedback": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
