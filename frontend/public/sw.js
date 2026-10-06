/* Service worker a mano. Reglas de privacidad (no relajar):
 *  - NUNCA se intercepta ni se guarda nada de /api/* (ejercicios, soluciones, PDF).
 *  - NUNCA se guardan imágenes del usuario: solo GET del mismo origen, sin blob:/data:.
 *  - Solo se guardan respuestas 200 "basic" (mismo origen), sin redirecciones ni no-store.
 * Qué hace: instala el shell offline, deja las navegaciones "red primero, caché si no hay red" y
 * los ficheros /_next/static/* "caché primero" (llevan hash en el nombre y no cambian).
 */
const VERSION = "v3";
const SHELL_CACHE = `shell-${VERSION}`;
const STATIC_CACHE = `static-${VERSION}`;
// Páginas estáticas (HTML igual para todos, sin datos de usuario): así abrir /historial/detalle?id=…
// o /solve sin conexión funciona aunque nunca se hayan cargado como navegación completa.
const PRECACHE = [
  "/offline",
  "/scan",
  "/graficar",
  "/solve",
  "/historial",
  "/historial/detalle",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== SHELL_CACHE && k !== STATIC_CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

function storable(response) {
  return (
    response.ok &&
    response.status === 200 &&
    response.type === "basic" &&
    !response.redirected &&
    !/no-store/i.test(response.headers.get("Cache-Control") || "")
  );
}

async function put(cacheName, request, response) {
  if (!storable(response)) return;
  const cache = await caches.open(cacheName);
  await cache.put(request, response);
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  await put(STATIC_CACHE, request, response.clone());
  return response;
}

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    await put(SHELL_CACHE, request, response.clone());
    return response;
  } catch {
    // ignoreSearch: /historial/detalle?id=A y ?id=B comparten la misma página (el id lo lee el cliente).
    return (
      (await caches.match(request, { ignoreSearch: true })) ||
      (await caches.match("/offline")) ||
      Response.error()
    );
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // la API siempre va directa a la red
  if (request.headers.has("RSC") || url.searchParams.has("_rsc")) return; // payloads de React Server Components
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(request));
  } else if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
  }
});
