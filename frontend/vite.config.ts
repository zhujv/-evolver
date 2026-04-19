import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/rpc": {
        target: "http://127.0.0.1:16888",
        changeOrigin: true,
      },
    },
  },
  // npm run preview 默认走 preview 配置；若无此项，/rpc 不会转发到后端，会得到 HTML 导致 JSON 解析失败
  preview: {
    port: 4173,
    proxy: {
      "/rpc": {
        target: "http://127.0.0.1:16888",
        changeOrigin: true,
      },
    },
  },
});
