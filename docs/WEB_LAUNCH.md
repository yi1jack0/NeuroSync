# NeuroSync Web: going live on neurosync.ejai.ai (Cloudflare Workers)

The app is a static site in `web/` (build output `web/dist`). Nothing is published until you do steps 1–2 below.
Your landing page on `ejai.ai` (Firebase Hosting, repo `ejacklab/ejai-landing-page`) is **not affected**: only the
`neurosync` subdomain is added.

## Hosting choice

**Cloudflare Workers with static assets**, which Cloudflare recommends for new sites. Static files are free with no bandwidth cap, and the DNS for ejai.ai is already in the same account.

The app has no server code; the Worker only serves files from `web/dist`. The config is in `web/wrangler.jsonc`, and it has been tested locally in Cloudflare's runtime (`wrangler dev`):
- the security headers from `_headers` are applied
- unknown paths serve the app
- the sounds have correct types
- the production e2e suite passes, including offline use

## 1. Connect the repo (one time, about 5 minutes)

1. In the Cloudflare dashboard, go to **Workers & Pages → Create → Import a repository** (Continue with GitHub), and allow access to **`yi1jack0/NeuroSync`**.
2. Configure the project:

   | Setting | Value |
   |---|---|
   | Project / Worker name | `neurosync`. Must match `"name"` in `web/wrangler.jsonc`. |
   | Production branch | the branch you release from (recommended: `main`) |
   | Root directory / path (under *Advanced*) | `web` |
   | Build command | `npm ci && npm run build` |
   | Deploy command | `npx wrangler deploy` (the default) |
   | Non-production branch deploy command | `npx wrangler versions upload` (the default: gives each branch a preview URL) |

   - Node 22 is pinned by `web/.node-version`.
   - The build reads the shared presets and sounds from `../src/neurosync/…`. That works because the whole repo is cloned.
3. Click **Deploy**. After 1–2 minutes the app is live at `https://neurosync.<your-subdomain>.workers.dev`. Try it on your phone and computer.

## 2. Attach the domain

In the Worker, go to **Settings → Domains & Routes → Add → Custom domain** and enter `neurosync.ejai.ai`.

Because ejai.ai's DNS is in the same Cloudflare account, the DNS record and HTTPS certificate are created automatically. The landing page on `ejai.ai` (Firebase Hosting) is not touched.

From then on, every push to the production branch redeploys, and every other branch or PR gets a preview URL.

Optional local check before pushing: `cd web && npm run cf:dev`, which builds and serves the app on http://localhost:8787 with Cloudflare's runtime. Then run `PROD_URL=http://localhost:8787 npx playwright test --project=prod`.

## 3. Verify after the first deploy

- [ ] `https://neurosync.ejai.ai` loads and shows the welcome + safety notice.
- [ ] Response headers include the strict `Content-Security-Policy` from `web/public/_headers`. Check in DevTools → Network → document → Headers.
- [ ] After a minute, the top bar shows **Offline ready**. Turn on airplane mode, reload, and confirm it still plays.
- [ ] `https://neurosync.ejai.ai/privacy.html` loads.

## 4. Real-device checklist (required before announcing; phones are a v1 requirement)

These are the items no emulator can prove. Use the preview URL or the live site.

**iPhone (iOS 16.4 or newer), Safari**

- [ ] Play *River Focus* **with the ring/silent switch set to silent**. Sound must still play (the app declares a "playback" audio session).
- [ ] **Lock the screen for 2 minutes.** Audio continues, and the lock screen shows NeuroSync with play/pause controls.
- [ ] **Sleep test:** *Delta Sleep*, timer **45m**, fade **5 min**, lock the phone. The audio fades and stops at about 45:00, with no sudden cut.
- [ ] The sounds play: Safari picks the AAC (`.m4a`) copies automatically.
- [ ] Add to Home Screen (⋯ → Install on this iPhone → follow the hint). The app opens full-screen and works in airplane mode.
- [ ] A phone call or a Siri interruption shows the "Playback was paused by your browser" banner, and *Resume* works.

**Android phone, Chrome**

- [ ] Same lock-screen, sleep-timer and interruption tests as above.
- [ ] ⋯ → **Install app** installs it, and the installed app works offline.
- [ ] Output device selection appears only where the browser supports it. Picking Bluetooth headphones switches the output.

**Desktop browsers**

- [ ] Chrome or Edge: the output device picker lists your headphones/DAC after the one-time permission prompt.
- [ ] Firefox and Safari (macOS): all three workflows work. The device picker is hidden where unsupported.
- [ ] Windows High Contrast mode: the app switches to the high-contrast theme automatically.
- [ ] A screen reader pass (NVDA on Windows or VoiceOver on Mac/iPhone): sliders announce values like "10.5 hertz beat, alpha band", and the toasts are spoken.

If the iPhone lock-screen test fails on a specific iOS version, report the version. The fallback is a documented limitation ("keep the screen on" hint), not a blocker for desktop users.
