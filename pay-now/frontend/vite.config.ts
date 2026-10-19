import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En développement, les appels /auth et /me passent par la passerelle Caddy publiée en local.
const gateway = "http://127.0.0.1:8080";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/auth": gateway, "/me": gateway } },
});
