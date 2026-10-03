# NeuroSync Web

Browser version of NeuroSync: TypeScript + Svelte 5 + Vite, Web Audio API, offline PWA.
The plan and design are in [`../docs/WEB_PLAN.md`](../docs/WEB_PLAN.md); the go-live steps are in [`../docs/WEB_LAUNCH.md`](../docs/WEB_LAUNCH.md).

```bash
npm ci
npm run dev          # http://localhost:5173  (syncs presets + sounds from the desktop package first)
npm test             # unit tests (Vitest), incl. golden values from the Python engine
npm run check        # svelte-check / TypeScript, fails on warnings
npm run build        # production build + 70 KB bundle budget  -> dist/
npm run e2e          # Playwright: desktop, phone, production/offline (needs `npx playwright install chromium`)
npm run cf:dev       # build + serve with Cloudflare's runtime (wrangler) on :8787
```

Hosting: Cloudflare Workers (static assets), configured in `wrangler.jsonc`. Cloudflare deploys it automatically on push (see `../docs/WEB_LAUNCH.md`).

```
```

| Path | What |
|---|---|
| `src/audio/` | Web Audio engine. `graph.ts` (nodes, output chain, fades), `engine.ts` (lifecycle, timer on the audio clock), `buffers.ts` (noise / ambience / own files), `platform.ts` (phone + browser workarounds), `dsp.ts` (pure maths) |
| `src/domain/` | Limits, bands, preset schema: ports of the Python domain, checked by `golden.test.ts` |
| `src/state/app.svelte.ts` | All app state and actions |
| `src/ui/` | Svelte components |
| `src/lib/` | Settings, IndexedDB, share links, files, offline/service worker, `i18n.svelte.ts` (English + 简体中文) |
| `scripts/` | `sync-shared` (presets + ambience from `../src/neurosync`), `transcode-aac` (Safari copies), `check-size`, `make-icons`, `screens` |
| `test/harness.*` | Test-only page that renders the real audio graph offline for Playwright |

**Shared data:** presets and ambience have a single source in the desktop package. After changing them:
- run `npm run sync`
- run `npm run transcode` if the sounds changed (needs ffmpeg), and commit the `.m4a` files
- run `python tools/export_golden.py` if engine rules changed (CI fails on drift)

**Languages:** English and Simplified Chinese, in `src/lib/i18n.svelte.ts`.
- First visit follows the browser language; the user can switch from the ⋯ menu or the welcome screen, and the choice is saved.
- Built-in preset and sound names are translated for display only. Stored data keeps the canonical English names, so presets, links and files work across languages.
- `i18n.test.ts` fails if a Chinese string is missing or its `{placeholders}` differ from the English ones.
