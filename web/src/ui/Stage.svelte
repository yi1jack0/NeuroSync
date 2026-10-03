<script lang="ts">
  import { app } from '../state/app.svelte';
  import { binauralOf } from '../domain/preset';
  import Orb from './Orb.svelte';
  import { fmtTime } from './format';

  const b = $derived(binauralOf(app.draft));
  const status = $derived.by(() => {
    switch (app.status) {
      case 'playing': return app.remaining !== null && app.timerMinutes > 0 ? `Playing · ${fmtTime(app.remaining)} remaining` : 'Playing';
      case 'fading': return 'Fading out…';
      case 'paused': return 'Paused';
      case 'loading': return 'Loading sounds…';
      case 'stopped': return 'Session ended';
      default: return 'Ready';
    }
  });
  const hint = $derived(app.isPlaying ? 'Space to pause' : app.status === 'paused' ? 'Space to resume' : 'Press Space or ▶ to begin · ? for shortcuts');
</script>

<section class="stage region-stage" aria-label="Now playing">
  {#if app.pendingShare}
    <div class="banner glass" role="status">
      <span>Shared preset: <b>{app.pendingShare.name}</b></span>
      <button class="btn primary" onclick={() => app.acceptShare(true)}>Add to My Presets</button>
      <button class="btn" onclick={() => app.acceptShare(false)}>Just play it</button>
    </div>
  {/if}
  {#if app.interrupted}
    <div class="banner glass" role="alert">
      <span>Playback was paused by your browser or device.</span>
      <button class="btn primary" onclick={() => app.resumeAfterInterruption()}>Resume</button>
    </div>
  {/if}
  <span class="chip">{app.band.label.toUpperCase()} · {app.band.low}–{app.band.high} Hz</span>
  <h1 class="title">{app.draft.name}{#if app.dirty}<span class="edited"> · edited</span>{/if}</h1>
  <p class="meta">{b ? `${b.base_hz} Hz carrier · ${b.beat_hz} Hz beat` : 'Ambience only'}</p>
  <div class="orb">
    <Orb color={app.settings.highContrast ? '#ffffff' : app.band.color} beat={b?.beat_hz ?? 1} playing={app.status === 'playing'}
      reduceMotion={app.settings.reduceMotion} flat={app.settings.highContrast} />
  </div>
  <p class="status" aria-live="polite">{status}</p>
  <p class="hint">{hint}</p>
</section>

<style>
  .stage { display: flex; flex-direction: column; align-items: center; padding: 22px 8px 18px; text-align: center; position: relative; }
  .chip { color: var(--accent); background: var(--accent-soft); border: 1px solid var(--accent-line); border-radius: 12px;
    padding: 3px 12px; font-size: 12px; font-weight: 600; letter-spacing: 1px; }
  .title { font-size: 30px; font-weight: 300; margin-top: 12px; line-height: 1.2; }
  .edited { color: var(--dim); font-size: .8em; }
  .meta { color: var(--dim); font-size: 14px; margin-top: 2px; }
  .orb { flex: 1; width: 100%; min-height: 200px; }
  .status { color: var(--dim); }
  .hint { color: var(--faint); font-size: 12.5px; margin-top: 2px; }
  .banner { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; padding: 10px 14px;
    margin-bottom: 14px; border-radius: 12px; background: var(--surface); }
  @media (max-width: 767px) {
    .stage { padding: 12px 4px; } .title { font-size: 24px; } .hint { display: none; }
  }
</style>
