import { defineConfig, type Plugin } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { VitePWA } from 'vite-plugin-pwa';

// Strict CSP: nothing but this origin. Also served as an HTTP header by Cloudflare
// (public/_headers); the meta copy makes `vite preview` and the e2e tests enforce it too.
export const CSP = [
  "default-src 'self'", "script-src 'self'", "style-src 'self'", "img-src 'self' data:", "media-src 'self' blob:",
  "connect-src 'self'", "worker-src 'self'", "manifest-src 'self'", "font-src 'self'", "object-src 'none'",
  "base-uri 'none'", "form-action 'none'",
].join('; ');

const cspMeta = (): Plugin => ({
  name: 'csp-meta', apply: 'build',
  transformIndexHtml: (html) => html.replace('<meta charset="utf-8">', `<meta charset="utf-8">\n  <meta http-equiv="Content-Security-Policy" content="${CSP}">`),
});

export default defineConfig({
  plugins: [
    svelte(),
    cspMeta(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false,
      includeAssets: ['icons/favicon.svg', 'icons/apple-touch-icon.png'],
      manifest: {
        name: 'NeuroSync — Tune your mind', short_name: 'NeuroSync',
        description: 'Binaural beats and calming ambience for focus, meditation and sleep. Works offline; nothing leaves your device.',
        start_url: '/', scope: '/', display: 'standalone', orientation: 'any',
        background_color: '#121417', theme_color: '#121417', categories: ['health', 'lifestyle', 'music'],
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,webmanifest}'],
        globIgnores: ['ambience/**', 'test/**'],
        navigateFallback: '/index.html',
        clientsClaim: true, skipWaiting: true, cleanupOutdatedCaches: true,
        runtimeCaching: [{
          urlPattern: ({ url }) => url.pathname.startsWith('/ambience/'),
          handler: 'CacheFirst',
          options: { cacheName: 'ambience', expiration: { maxEntries: 32 } },
        }],
      },
    }),
  ],
  build: { target: 'es2022', sourcemap: false },
  test: { include: ['src/**/*.test.ts'] },
} as never);
