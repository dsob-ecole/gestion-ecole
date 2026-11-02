// GestionÉcole — téléphone : l'application est gardée dans le téléphone pour marcher sans Internet.
// Changer VERSION à chaque mise à jour : le téléphone prendra la nouvelle version à la prochaine connexion.
const VERSION = "gestionecole-tel-v1.3";
const FICHIERS = ["./", "./index.html", "./manifest.webmanifest", "./icone-192.png", "./icone-512.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(FICHIERS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(cles => Promise.all(cles.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, {ignoreSearch: true}).then(garde => {
    const reseau = fetch(e.request).then(rep => {
      if (rep && rep.ok) { const copie = rep.clone(); caches.open(VERSION).then(c => c.put(e.request, copie)); }
      return rep;
    }).catch(() => garde);
    return garde || reseau;           // sans Internet : la version gardée ; avec Internet : mise à jour en arrière-plan
  }));
});
