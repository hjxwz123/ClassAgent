import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue({ template: { compilerOptions: { isCustomElement: (tag) => tag === "math-field" } } })],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ["vue"],
          charts: ["echarts"],
          icons: ["@phosphor-icons/vue"],
          mathlive: ["mathlive"]
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      },
      "/static": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  }
});
