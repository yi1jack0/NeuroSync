# NeuroSync Web — Plan & Design

*Same product, same rules, in the browser. Offline-capable, no accounts, no tracking.*

Status: **proposal for review**. Mockups: `docs/screenshots/web-*.png`
(source: `web/design/mockup.html`, a static, non-functional layout prototype).

---

## 1. Goals and non-goals

**Goals**
1. Feature parity with the desktop app for the three core workflows (Quick Focus, Biohacker, Sleep).
2. Works on desktop *and* phones/tablets, installable as a PWA, fully usable offline after the first visit.
3. Same safety rules, same preset format: a preset exported from desktop imports on the web and vice versa.
4. Static hosting only. No backend, no cookies, no analytics, no third-party requests.

**Non-goals (v1)**
- Accounts, cloud sync, social sharing beyond copy-a-link.
- WASAPI exclusive mode, system tray, guaranteed latency/CPU numbers (browser limits; desktop keeps these).
- Rewriting the desktop app. Both apps live in this repo and share data, not code.

## 2. What carries over from desktop

| Asset | Reuse |
|---|---|
| `docs/DESIGN.md` | Visual language, motion rules, flows, accessibility spec: reused as-is, adapted for responsive layouts (§6). |
| Theme tokens (band colours, palette) | Ported to CSS custom properties. |
| Built-in presets `src/neurosync/app/builtin/*.json` | Copied into the web build at build time: **one source of truth**. |
| Ambience `src/neurosync/assets/ambience/` + `catalog.json` | Same files, plus an AAC fallback (§4.4). Same `asset:<id>` references. |
| Business rules (`domain/limits.py`) | Re-implemented in TS, then checked against **golden values exported from Python** (§8). |
| Python tests | Become the spec for the TS tests: same cases, same numbers. |

## 3. Stack (recommendation)

| Choice | Pick | Why |
|---|---|---|
| Language | **TypeScript** (strict) | The audio maths and preset schema benefit from types. |
| UI | **Svelte 5** | Small runtime (~10 KB), built-in transitions fit the calm-motion spec, simple reactive state for a single-screen app. React or Preact would also work, but ship more code for no gain here. |
| Build | **Vite** | Fast dev server, static output, first-class PWA plugin. |
| Audio | **Web Audio API** (no library) | Everything needed is native: oscillators, gain ramps on the audio clock, sample-accurate looping. |
| Offline | **vite-plugin-pwa** (Workbox) | Precaches the app shell; ambience is cached on first use. |
| Tests | **Vitest** (unit) + **Playwright** (e2e, Chromium is preinstalled here) | Audio can be tested headlessly with `OfflineAudioContext` + FFT. |
| Hosting | **Cloudflare Pages** on your domain **ejai.ai** (registrar and DNS already at Cloudflare) | Free, automatic HTTPS, global CDN, a preview URL per branch. Static only, no server. Publishing waits for your go-ahead. |

Repo layout: `web/` alongside the Python package.

```
web/
  src/
    audio/      engine.ts (graph), binaural.ts, noise.ts, ambience.ts, fade.ts, loop.ts
    domain/     limits.ts, bands.ts, preset.ts (schema + validation), golden.test.ts
    state/      session.svelte.ts (play/pause/timer), settings.ts, library.ts (IndexedDB)
    ui/         TopBar, Library, Stage/Orb, Mixer/Strip, TimerPopover, Toast, Disclaimer, Shortcuts
    lib/        share.ts (preset <-> URL), keyboard.ts, a11y.ts
  public/ambience/          (generated at build from src/neurosync/assets/ambience)
  scripts/sync-shared.mjs   copies presets + ambience, transcodes AAC fallback
  e2e/                      Playwright specs
```

## 4. Audio engine design

### 4.1 Graph

```
OscillatorNode L (base) ──┐
                          ├─ ChannelMerger(2) ─ Gain(tone) ─┐
OscillatorNode R (base+beat)┘                               │
AudioBufferSource (noise, loop) ─ Gain ─ StereoPanner ──────┼─ Gain(master ≤ 0.85) ─ Gain(fade) ─ DynamicsCompressor (safety limiter) ─ destination
AudioBufferSource (ambience, loop) ─ Gain ─ StereoPanner ───┘
```

- **Binaural:** two `OscillatorNode`s merged into exact left and right channels, so each ear gets one pure tone.
  - Frequency changes use `setTargetAtTime` (about 20 ms), so live slider drags never click.
  - The tone strip is never panned, which keeps the left/right separation intact.
- **Noise beds:** white, pink and brown are generated once by FFT shaping in a **Web Worker**, as on desktop.
  - The result is circular, so it loops seamlessly in an `AudioBufferSource` with `loop = true`.
  - Rendering 20 s × 3 colours takes about 150 ms off the main thread.
- **Ambience:** fetch the file, `decodeAudioData`, then apply the same **equal-power tail-into-head crossfade** as `make_loopable()`, then loop it sample-accurately.
  - Decoded buffers are cached per sound id, so two strips share the RAM.
- **Per-channel gain/mute/pan:** `GainNode` plus `StereoPannerNode`, with all changes ramped over 15–30 ms.

### 4.2 Safety rules, enforced in code (not just in the UI)

| Rule | Web implementation |
|---|---|
| Base 50–1000 Hz, beat 0.1–40 Hz | `domain/limits.ts` clamps every write, so preset imports and URL-shared presets are clamped too. |
| Master gain ≤ 0.85 | The master `GainNode` value is clamped. A `DynamicsCompressor` (threshold −3 dBFS, ratio 20, fast attack) acts as a brick-wall safety net when many tracks are summed. |
| Log fade-out ≥ 3 s on stop/timer | `exponentialRampToValueAtTime` on the fade gain (linear in dB, like `LogFade`), from 1 to 0.001 over max(fade, 3 s), then `stop()`. |
| Headphone disclaimer | A modal `<dialog>` shown before the **first** AudioContext is ever started. Its acknowledgement is stored locally. |

### 4.3 Timer that survives background tabs

Browsers throttle `setTimeout` in background tabs, so the session timer **must not** depend on it.

- When the timer is set, the fade ramp and the source `stop()` are **scheduled ahead on the AudioContext clock**: the fade starts at `t0 + duration − fade`.
- The audio thread then carries out the end of the session even if JS is throttled.
- The countdown UI simply reads `ctx.currentTime` on each animation frame.
- On pause, the scheduled ramp is cancelled, and it is re-scheduled on resume.

### 4.4 Browser support and codecs

| Concern | Plan |
|---|---|
| Autoplay policy | The AudioContext is created and resumed on the first Play or acknowledge click, which is always a user gesture. |
| Ogg on Safari | Support varies by Safari version. The build also emits an **AAC `.m4a`** for each sound (ffmpeg in CI), and `canPlayType` picks one. AAC encoder priming at the start is hidden by the loop crossfade. |
| Output device choice | `AudioContext.setSinkId` (Chrome/Edge). Device names need a one-time media permission in Chrome; we ask only when the user opens the selector. Firefox uses `selectAudioOutput()`. If neither exists, the selector is hidden. |
| Phone lock screen | Route the master output to a `MediaStreamDestination` played by a hidden `<audio>` element and register the **Media Session API** (title, play/pause/stop). This keeps audio alive on iOS/Android when the screen locks and adds lock-screen controls. **This is the riskiest item, so it gets a spike in Phase 1.** |
| Minimum targets | Last 2 versions of Chrome, Edge, Firefox and Safari; iOS 16.4+ and Android Chrome. |

## 5. State and data

- **Settings**, in localStorage:
  - master volume, last preset, disclaimer acknowledged, fade length
  - high-contrast override, reduce-motion override
  - output device id
- **User presets** and imported sound files: in IndexedDB, using the exact desktop JSON schema. Custom audio files are stored as Blobs.
- **Share a preset** works with no server: the preset JSON is compressed into the URL fragment, `…/#p=<base64url(deflate(json))>`.
  - The fragment is never sent to the host.
  - Opening the link shows "Add *Deep Work Rain* to My Presets?" (an inline banner, not a modal).
  - Shared presets **cannot reference local files**. Any such channel is dropped, with a toast saying so.
- **Import/Export:** `.json` files are identical to desktop's.

## 6. UX design

The visual language is unchanged from `DESIGN.md`: charcoal background, the band-driven accent, glass panels, the breathing orb and calm motion. The web version gets **real** frosted glass (`backdrop-filter`), which Qt could not do.

### 6.1 Responsive layouts

| Width | Layout |
|---|---|
| **≥ 1200 px** (desktop) | Same three columns as desktop: Library · Stage · Mixer. The top bar holds the transport. |
| **768–1199 px** (tablet) | Library becomes a slide-over drawer (☰). Stage is centred. The Mixer becomes a **bottom drawer**: a peek handle shows level meters, swipe or click to open the faders (this is the brief's "bottom drawer" option). |
| **< 768 px** (phone) | Single column with a bottom tab bar: **Library / Now / Mixer**. A sticky mini-transport sits above the tab bar (play/pause, timer, countdown). Faders become horizontal for thumb reach. |

Mockups: `docs/screenshots/web-desktop.png`, `web-tablet.png`, `web-phone.png` (Now tab), `web-phone-mixer.png` (Mixer tab).

### 6.2 Web-specific UX decisions

- **First visit:**
  - A short welcome card says what binaural beats are, then shows the safety notice.
  - The safety notice must be acknowledged before any sound.
  - Then the library opens, pre-selected on *Alpha Focus*.
- **"Install app" hint:** a subtle chip in the ⋯ menu when the browser supports installation. Never a popup.
- **Offline indicator:** a quiet dot in the top bar ("Available offline ✓" once all sounds are cached).
- **Background-tab honesty:** if the browser suspends audio (some mobile cases), the app shows "Playback was paused by your browser — tap to resume" when the user returns.
- **Shortcuts:** identical to desktop (Space, Ctrl/⌘+Space, M, Ctrl/⌘+↑/↓, F1 …). They are disabled while typing in a text field.
- **Motion:**
  - `prefers-reduced-motion` freezes the orb and turns transitions into fades.
  - The orb pulse is octave-folded to ≤ 1.25 Hz, as on desktop, so it never flickers.

### 6.3 Accessibility

- Every fader is a native `<input type="range">` (vertical via `writing-mode`). It gets keyboard and screen-reader support for free, plus `aria-valuetext` such as "10.5 hertz, Alpha band".
- `forced-colors: active` (Windows High Contrast) and `prefers-contrast: more` switch to the high-contrast theme automatically. A manual toggle remains.
- Toasts go to an `aria-live="polite"` region. The disclaimer is a native `<dialog>`, which traps focus.
- Touch targets are ≥ 44 px on phone layouts. All text meets WCAG AA contrast against the glass panels.

## 7. Performance budgets

| Metric | Budget |
|---|---|
| JS + CSS (gzipped, first load) | ≤ 70 KB |
| First paint on mid-range phone, 4G | ≤ 1.5 s |
| Ambience | Lazy: fetched when first used. Then cached for offline use (~1.5 MB Ogg or ~1.2 MB AAC). |
| Audio thread | Native nodes only, no ScriptProcessor and no AudioWorklet needed. CPU is typically < 2 % on desktop Chrome. |
| Visualizer | `requestAnimationFrame` at 30 fps, paused when the tab is hidden or the orb is off-screen. |

## 8. Testing strategy

1. **Golden values from Python.** A small script exports reference numbers from the desktop engine as `web/src/domain/golden.json`. Vitest checks the TS ports against them. This keeps the two apps behaving the same. The numbers cover:
   - fade curve samples
   - clamp results
   - band lookups
   - loop-crossfade output on a fixed input
   - preset parsing
2. **Audio unit tests:** render the graph in an `OfflineAudioContext`, then use an FFT to check:
   - left = 200 Hz and right = 210 Hz
   - master peak ≤ 0.85
   - the fade is monotonic and ≥ 3 s
   - the timer ends audio at the scheduled time
3. **E2E (Playwright, Chromium):** all three user workflows, keyboard-only navigation, the disclaimer gate, a share-link round trip, and offline reload. Run with the service worker on, network off.
4. **Accessibility:** axe-core scan in e2e. Manual NVDA and VoiceOver pass before launch.
5. **CI:** a GitHub Actions job runs lint, typecheck, unit and e2e tests on every push to `web/**`, then a production build plus a bundle-size check.

## 9. Milestones

| Phase | Scope | Exit criteria |
|---|---|---|
| **1. Foundations + risk spikes** | Vite/Svelte/TS scaffold, shared-data sync script, `domain/` ports + golden tests. **Spikes:** iOS lock-screen playback, Safari codec fallback, `setSinkId`. | Golden tests green; spike results documented with a go/no-go on each. |
| **2. Audio engine** | Binaural, noise worker, ambience loader + crossfade, mixer graph, limiter, scheduled fades/timer. | OfflineAudioContext tests green; the engine can be played from a dev page. |
| **3. Desktop layout UI** | Top bar, library, stage + orb, mixer strips, timer popover, toasts, disclaimer, shortcuts, theme + band accent. | The three workflows pass in e2e at desktop width. |
| **4. Responsive + PWA** | Tablet drawer, phone tabs + mini transport, Media Session, service worker, install hint, offline indicator. | Offline e2e green; tested on a real iPhone and an Android phone. |
| **5. Sharing + polish** | Share links, import/export, IndexedDB custom sounds, high-contrast/forced-colors, axe pass, perf budget. | Accessibility and performance budgets met. |
| **6. Launch** | Cloudflare Pages project connected to this repo (build `web/`, output `web/dist`); custom domain on ejai.ai; security headers (`_headers`: strict CSP, no third-party origins); README; privacy statement ("nothing leaves your device"). | You approve publishing. |

## 10. Decisions needed from you

1. **Framework:** Svelte 5 (recommended) or React?
2. **Hosting:** ✅ decided: Cloudflare Pages on **ejai.ai**. Still open: which address?
   - `neurosync.ejai.ai` (recommended): keeps the root domain free for anything else, and the app's offline cache and install scope stay cleanly separate.
   - `ejai.ai` itself, if the domain is dedicated to NeuroSync.
   - `ejai.ai/neurosync`: works, but is the most fiddly for an installable app.
3. **Mobile priority:** should phones get full parity in v1 (as planned), or desktop browsers first with phones in v1.1? The lock-screen spike decides how hard phones are.
4. **Ambience fallback:** OK to add AAC copies (~1.2 MB more in the repo/build), so Safari users get the sounds?

## 11. Hosting setup (Cloudflare Pages + ejai.ai)

Done by you in the Cloudflare dashboard when we reach Phase 6. Nothing is published before then.

1. **Workers & Pages → Create → Pages → Connect to Git**, then pick `yi1jack0/NeuroSync`.
2. Set the build options:
   - root directory `web`
   - build command `npm ci && npm run build`
   - output `dist`
   - production branch = whichever branch you choose to release from
3. **Custom domains → Set up a custom domain** → e.g. `neurosync.ejai.ai`. Cloudflare creates the DNS record and certificate itself, because the domain is already in your account.
4. Every other branch and every PR gets its own preview URL (`<branch>.<project>.pages.dev`). This lets us test on real phones before anything reaches ejai.ai.

The repo will carry `web/public/_headers` with a strict Content-Security-Policy:
- `default-src 'self'`, with no external origins
- `Permissions-Policy` limited to what the app uses
- long cache lifetimes for hashed assets and the ambience files

The headers enforce the "nothing leaves your device" promise technically, not just in a privacy statement.
