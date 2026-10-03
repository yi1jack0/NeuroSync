# NeuroSync Web: going live on neurosync.ejai.ai

The app is a static site in `web/` (build output `web/dist`). Nothing is published until you do steps 1–3 below.
Your landing page on `ejai.ai` (Firebase Hosting, repo `ejacklab/ejai-landing-page`) is **not affected**: only the
`neurosync` subdomain is added.

## 1. Connect Cloudflare Pages (one time, about 5 minutes)

1. Open the Cloudflare dashboard, then go to **Workers & Pages → Create → Pages → Connect to Git**.
2. Authorise GitHub and pick **`yi1jack0/NeuroSync`**.
3. Enter the build settings:

   | Setting | Value |
   |---|---|
   | Production branch | the branch you release from (e.g. `main` once you merge) |
   | Framework preset | None |
   | Root directory | `web` |
   | Build command | `npm ci && npm run build` |
   | Build output directory | `dist` |
   | Environment variable | `NODE_VERSION` = `22` |

   The build reads the shared presets and sounds from `../src/neurosync/…`. That works because Cloudflare clones the whole repo.
4. Click **Save and Deploy**. Every branch and pull request also gets a private preview URL (`<branch>.<project>.pages.dev`).

## 2. Attach the domain

In the Pages project, go to **Custom domains → Set up a custom domain** and enter `neurosync.ejai.ai`.

Because ejai.ai already uses Cloudflare DNS, Cloudflare creates the `CNAME` record and the HTTPS certificate automatically, usually within minutes. The existing `ejai.ai` / `www` records are not touched.

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
