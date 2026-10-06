import type { NextConfig } from "next";

// El navegador habla solo con Next (mismo origen); /api/* se reenvía al backend. Así el móvil
// no necesita CORS ni apuntar a la IP del PC, y no hay contenido mixto bajo HTTPS.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Redes locales: permite abrir el servidor de desarrollo desde el móvil (http://192.168.x.x:3000).
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*"],
  // /api/solve con Opus y reintentos puede pasar del límite por defecto del proxy (30 s).
  experimental: { proxyTimeout: 300_000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  async headers() {
    return [
      {
        // El navegador debe pedir siempre la versión más reciente del service worker.
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Content-Security-Policy", value: "default-src 'self'; script-src 'self'" },
        ],
      },
    ];
  },
};

export default nextConfig;
