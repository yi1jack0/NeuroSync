<script lang="ts">
  import { app, type Tab } from '../state/app.svelte';
  import Dialogs from './Dialogs.svelte';
  import Icon from './Icon.svelte';
  import Library from './Library.svelte';
  import Mixer from './Mixer.svelte';
  import Stage from './Stage.svelte';
  import Toasts from './Toasts.svelte';
  import TopBar from './TopBar.svelte';
  import { i18n, t, type Key } from '../lib/i18n.svelte';

  $effect(() => {
    const root = document.documentElement;
    const forced = matchMedia('(prefers-contrast: more)').matches;
    root.classList.toggle('hc', app.settings.highContrast || forced);
    root.style.setProperty('--accent', app.settings.highContrast ? '#FFFF00' : app.band.color);
    document.querySelector('meta[name=theme-color]')?.setAttribute('content', app.settings.highContrast ? '#000000' : '#121417');
  });
  $effect(() => { document.title = app.isPlaying ? t('title.playing', { name: i18n.name(app.draft.name) }) : t('title.idle'); });

  function onKey(e: KeyboardEvent) {
    const t = e.target as HTMLElement;
    const typing = t.matches('input:not([type=range]):not([type=checkbox]), textarea, select, [contenteditable]');
    if (typing || app.dialog !== 'none' || e.altKey) return;
    const mod = e.ctrlKey || e.metaKey;
    // The orb is a button (click = change speed) but Space must still mean play/pause there.
    const onControl = t.matches('button, input, select, a, summary') && !t.closest('button.orb');
    if (e.code === 'Space' && !mod && !onControl) { e.preventDefault(); e.shiftKey ? app.stop() : void app.toggle(); }
    else if (e.code === 'Space' && e.shiftKey && !mod) { e.preventDefault(); app.stop(); }
    else if (mod && e.key === 'ArrowUp') { e.preventDefault(); app.nudgeMaster(5); }
    else if (mod && e.key === 'ArrowDown') { e.preventDefault(); app.nudgeMaster(-5); }
    else if (mod) return;
    else if (e.key === 'm' || e.key === 'M') app.toggleMute();
    else if (e.key === 's' || e.key === 'S') { app.saving = true; app.tab = 'mixer'; app.mixerOpen = true; }
    else if (e.key === 'n' || e.key === 'N') app.newSession();
    else if (e.key === 't' || e.key === 'T') (document.querySelector('[data-timer]') as HTMLElement | null)?.click();
    else if (e.key === '/') { e.preventDefault(); app.libraryOpen = true; app.tab = 'library'; queueMicrotask(() => (document.querySelector('input[type=search]') as HTMLElement | null)?.focus()); }
    else if (e.key === '?' || e.key === 'F1') { e.preventDefault(); app.dialog = 'shortcuts'; }
  }
  const TABS: [Tab, Key, string][] = [['library', 'tab.library', 'library'], ['now', 'tab.now', 'now'], ['mixer', 'tab.mixer', 'mixer']];
</script>

<svelte:window onkeydown={onKey} />
<div class="aurora" aria-hidden="true"></div>
<main class="app" data-tab={app.tab}>
  <TopBar />
  <Library />
  <button class="scrim" class:open={app.libraryOpen} aria-label={t('lib.close')} tabindex="-1" onclick={() => (app.libraryOpen = false)}></button>
  <Stage />
  <Mixer />
  <div class="tabbar" role="tablist" aria-label={t('region.sections')}>
    {#each TABS as [id, label, icon]}
      <button role="tab" aria-selected={app.tab === id} onclick={() => (app.tab = id)}><Icon name={icon} />{t(label)}</button>
    {/each}
  </div>
</main>
<Toasts />
<Dialogs />
