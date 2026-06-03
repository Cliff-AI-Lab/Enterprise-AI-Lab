import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5183,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:18791",
        changeOrigin: true,
      },
    },
  },
});
