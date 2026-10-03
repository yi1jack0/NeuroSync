<script lang="ts">
  // Stroke icons on a 24-unit grid (same glyph set as the desktop app).
  let { name, size = 18 }: { name: string; size?: number } = $props();
  const P: Record<string, string> = {
    play: '<path d="M8 5.5 18.5 12 8 18.5z" fill="currentColor" stroke="none"/>',
    pause: '<rect x="7" y="5.5" width="3.6" height="13" rx="1.2" fill="currentColor" stroke="none"/><rect x="13.4" y="5.5" width="3.6" height="13" rx="1.2" fill="currentColor" stroke="none"/>',
    stop: '<rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" stroke="none"/>',
    timer: '<circle cx="12" cy="13" r="7.5"/><path d="M12 13V9M12 13l2.5 1.5M10 3.5h4"/>',
    more: '<circle cx="6" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="18" cy="12" r="1.3" fill="currentColor"/>',
    plus: '<path d="M12 6v12M6 12h12"/>', close: '<path d="M7 7l10 10M17 7 7 17"/>',
    volume: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a7.5 7.5 0 0 1 0 11"/>',
    mute: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15 9.5l5 5M20 9.5l-5 5"/>',
    headphones: '<path d="M4 16a8 8 0 0 1 16 0"/><rect x="3.5" y="12" width="4" height="7" rx="1.5"/><rect x="16.5" y="12" width="4" height="7" rx="1.5"/>',
    wave: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>', noise: '<path d="M5 8v8M8 6v12M11 9v6M14 5v14M17 8v8M20 10v4"/>',
    orb: '<circle cx="12" cy="12" r="6" fill="currentColor"/>', file: '<path d="M6 3.5h8l4.5 4.5v12.5H6z"/><path d="M14 3.5V8h4.5"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', library: '<path d="M4 6h16M4 12h16M4 18h10"/>',
    mixer: '<path d="M6 4v16M12 4v16M18 4v16"/><circle cx="6" cy="14" r="2" fill="var(--bg)"/><circle cx="12" cy="8" r="2" fill="var(--bg)"/><circle cx="18" cy="16" r="2" fill="var(--bg)"/>',
    now: '<circle cx="12" cy="12" r="7"/>', share: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 10.8l7.6-3.6M8.2 13.2l7.6 3.6"/>',
    download: '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>', upload: '<path d="M12 20V9M7 13.5l5-5 5 5M5 4h14"/>',
    trash: '<path d="M5 7h14M10 7V4.5h4V7M7 7l1 13h8l1-13"/>', save: '<path d="M6 4h12v16l-6-4.5L6 20z"/>',
    keyboard: '<rect x="3" y="6.5" width="18" height="11" rx="2"/><path d="M7 10h.01M10.5 10h.01M14 10h.01M17.5 10h.01M8 14h8"/>',
    device: '<rect x="6" y="3.5" width="12" height="17" rx="2.5"/><circle cx="12" cy="14" r="3"/><circle cx="12" cy="7.5" r=".9" fill="currentColor"/>',
    contrast: '<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/>',
    motion: '<path d="M3 12h4l2-5 4 10 2-5h6"/>', install: '<rect x="5" y="3" width="14" height="18" rx="2.5"/><path d="M12 8v7M9 12l3 3 3-3"/>',
    chevron: '<path d="M7 10l5 5 5-5"/>', check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  };
</script>

<svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" stroke-width="1.8"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{@html P[name] ?? ''}</svg>
