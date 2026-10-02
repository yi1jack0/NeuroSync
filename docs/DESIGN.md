# NeuroSync Studio — UI / UX Design

*Clinical yet calming. Minimal, dark, scientifically grounded.*

Screenshots: `docs/screenshots/` (regenerate: `QT_QPA_PLATFORM=offscreen python scripts/screenshots.py`).

## 1. Principles
1. **Calm by default** — nothing blinks, nothing pops up. State changes ease over 150–900 ms.
2. **One accent, driven by the science** — the whole UI tints to the *current brainwave band*
   (Delta purple → Theta lavender → Alpha cyan → Beta mint → Gamma amber). Drag the Beat
   slider across 4 Hz and the app re-colours itself: the interface teaches the bands.
3. **Audio is the product, UI is the remote** — the UI never does audio maths; it edits a
   draft `Preset` and the live mixer in lock-step (`app/transport.py`).
4. **Safe by construction** — sliders can't exceed the limits (base 50–1000 Hz, beat 0.1–40 Hz,
   master 100 % = 0.85 gain). Stop/quit always fade ≥ 3 s.
5. **Keyboard and screen-reader complete** — every control reachable and named.

## 2. Layout (min 1160×740, designed at 1360×840)
```
┌────────────────────────────── Top bar ──────────────────────────────┐
│ ◉ NeuroSync     ■  ▶  ⏱ 44:58      🔈──●── 41%  [Output ▾]  ⋯  ▭ │
├──────────┬───────────────────────────────────────┬─────────────────┤
│ LIBRARY  │          ALPHA · 8–14 Hz              │ MIXER  [Save ▸] │
│ search   │          Alpha Focus                  │ CUSTOM GENERATOR│
│ SLEEP    │      200 Hz carrier · 10 Hz beat      │ Base  Beat Tone │
│ MEDITATE │                                       │ │     │    │   │
│ FOCUS    │              (  orb  )                │ ─────────────── │
│ CREATIVE │                                       │ AMBIENCE  + Add │
│ MY PRESETS│     Playing · 44:58 remaining        │ Pink  Brown …   │
└──────────┴───────────────────────────────────────┴─────────────────┘
```
| Region | Contents |
|---|---|
| **Top bar** | Wordmark · Stop · Play/Pause (52 px accent button) · Sleep-timer popover + countdown · Mute · Master slider (% of safe max) · Output device · ⋯ menu · Minimize-to-tray |
| **Library** (258 px) | Search; presets grouped Sleep / Meditate / Focus / Creativity / My Presets; band-coloured dot, Hz subtitle, accent tab on the loaded preset; context menu (Load, Export, Delete+Undo) |
| **Center stage** | Band chip, title, carrier/beat readout, breathing orb, status line + hint |
| **Mixer** (418 px) | *Custom Generator*: Base, Beat (live band label), Tone-level faders. *Ambience*: one strip per sound (fader, pan, mute, remove) + “Add sound” |

## 3. Visual language
* **Surfaces** — charcoal `#121417` over an *aurora* backdrop (soft blooms in the band colour,
  vignette). Panels = 4.5 % white fill + 1 px hairline + brighter top edge = frosted glass.
  (Qt has no backdrop blur, so glass is simulated; it stays cheap and consistent.)
* **Type** — Segoe UI Variable (Windows) → Inter → system. Light 22 pt title, 8 pt tracked
  caps for section labels, monospaced numerals for values so digits don't jitter.
* **Accent tokens** — Delta `#7B61FF` · Theta `#B18CFF` · Alpha `#2DD4E8` · Beta `#3EE0A1` · Gamma `#F7B955`.
* **Icons** — painted vector glyphs (`ui/icons.py`), 1.8 px round strokes, DPI-independent.

## 4. Motion & feedback
| Element | Behaviour |
|---|---|
| **Orb** | Breathes at the beat **folded down by octaves to ≤ 1.25 Hz** (a 40 Hz beat shows a 1.25 Hz pulse — never a flicker, photosensitivity-safe). Three ripples travel outward per pulse. Dim and still when paused; zero paint cost when hidden. |
| **Sliders** | Hover halo, press-grow, and a **detent pulse** — a ring flash as the handle crosses a band boundary (4/8/14/30 Hz) or pan centre. Double-click pan to re-centre. Value readouts update live. |
| **Theme** | Accent cross-fades over 700–900 ms when the band changes. |
| **Presets** | Switching while playing **equal-power crossfades** (350 ms); pause/resume ramps 120 ms. |
| **Toasts** | Bottom-centre, 2.8 s, fade in/out; actions (e.g. *Undo* after delete) stay 5 s. Never modal. |
| **Save** | Header morphs *inline* into a name field + Save (no dialog). “Save as preset” turns accent-filled when the draft has unsaved edits; title shows “· edited”. |

## 5. Flows
* **Quick Focus** — launch → library already on last preset → `Space`. Volume restored from settings.
* **Biohacker** — `Ctrl+N` (blank binaural) → drag Base to 200, Beat to 10.5 (accent follows band)
  → *Add sound* → Brown/Pink noise → balance faders → `Ctrl+S`, type “Deep Work Rain”, `Enter` → toast.
* **Sleep** — pick *Delta Sleep* → ⏱ **45m**, “Fade out over 5 min” → `Ctrl+M` to tray. Countdown
  runs in the tray tooltip; at 40:00 audio fades logarithmically; at 45:00 the output device is
  released and a tray notification says “Session complete”.
* **First launch** — in-window safety card (headphones, volume, driving, medical). Cannot be
  dismissed except by “I understand”; UI behind it is disabled. Re-openable from ⋯ menu.

## 6. Accessibility
* **Keyboard** — everything focusable with visible rings; `F6` jumps Library → Transport → Mixer;
  arrows/PgUp/PgDn on sliders; `F1` lists all shortcuts (Space, Ctrl+Space, M, Ctrl+↑/↓, Ctrl+T,
  Ctrl+S, Ctrl+N, Ctrl+M, Ctrl+F, Ctrl+Q).
* **Screen readers** — all controls have names; sliders carry spoken descriptions
  (“10.5 hertz beat, Alpha band”); presets read “Alpha Focus, Alpha 10 hertz”; toasts are announced.
* **High contrast** (`Ctrl+Shift+H`) — pure black, white 2 px borders, yellow accent/focus,
  no glass, flat orb. **Reduce motion** stops orb animation.
* **Colour is never the only signal** — bands are also named in text (chip, strip label).

## 7. Windows integration
Tray icon (tinted to the band) with Show / Play-Pause / Stop / Quit; closing the window keeps
playing in the tray (first time shows a hint; toggle in ⋯). Quit hides instantly then fades audio.
Output selector prefers WASAPI devices; *WASAPI exclusive mode* toggle in ⋯.

## 8. Code map
```
ui/theme.py       tokens, band colours, palettes (dark / high-contrast), QSS
ui/icons.py       painted icons
ui/widgets.py     GlowSlider, OrbVisualizer, AuroraBackground, Toast, Overlay
ui/panels.py      TopBar (+TimerPopover), PresetLibrary, CenterStage, MixerPanel/ChannelStrip
ui/overlays.py    DisclaimerOverlay, ShortcutsOverlay
ui/main_window.py controller: wiring, tray, shortcuts, theming, device + lifecycle
app/transport.py  live session owner: crossfade, pause ramp, channel editing
app/settings.py   persisted preferences
```

## 9. Known gaps / next
Only the Water ambience (river, sea) is bundled so far - rain & café still to come; un-hide the sidebar on
narrow windows; installer (PyInstaller/MSIX); verify tray + WASAPI on real Windows.
