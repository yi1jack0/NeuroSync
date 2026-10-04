<script lang="ts">
  import { app } from '../state/app.svelte';
  import { binauralOf } from '../domain/preset';
  import Orb from './Orb.svelte';
  import Icon from './Icon.svelte';
  import { ORB_SPEEDS } from '../domain/bands';
  import { fmtTime } from './format';
  import { i18n, t } from '../lib/i18n.svelte';

  const b = $derived(binauralOf(app.draft));
  const status = $derived.by(() => {
    switch (app.status) {
      case 'playing': return app.remaining !== null && app.timerMinutes > 0 ? t('st.playingLeft', { t: fmtTime(app.remaining) }) : t('st.playing');
      case 'fading': return t('st.fading');
      case 'paused': return t('st.paused');
      case 'loading': return t('st.loading');
      case 'stopped': return t('st.stopped');
      default: return t('st.ready');
    }
  });
  const hint = $derived(app.isPlaying ? t('st.hintPause') : app.status === 'paused' ? t('st.hintResume') : t('st.hintStart'));
</script>

<section class="stage region-stage" aria-label={t('region.now')}>
  {#if app.pendingShare}
    <div class="banner glass" role="status">
      <span>{t('st.shared')} <b>{i18n.name(app.pendingShare.name)}</b></span>
      <button class="btn primary" onclick={() => app.acceptShare(true)}>{t('st.addShared')}</button>
      <button class="btn" onclick={() => app.acceptShare(false)}>{t('st.justPlay')}</button>
    </div>
  {/if}
  {#if app.interrupted}
    <div class="banner glass" role="alert">
      <span>{t('st.interrupted')}</span>
      <button class="btn primary" onclick={() => app.resumeAfterInterruption()}>{t('st.resume')}</button>
    </div>
  {/if}
  <span class="chip">{i18n.bandUpper(app.band.name)} · {app.band.low}–{app.band.high} Hz</span>
  <h1 class="title">{i18n.name(app.draft.name)}{#if app.dirty}<span class="edited"> · {t('st.edited')}</span>{/if}</h1>
  <p class="meta">{b ? t('st.meta', { base: b.base_hz, beat: b.beat_hz }) : t('st.ambienceOnly')}</p>
  <button class="orb" onclick={() => app.cycleOrbSpeed()} title={t('orb.tip')}
    aria-label={t('orb.label', { speed: t(`speed.${ORB_SPEEDS[app.settings.orbSpeed]?.name ?? 'Calm'}` as 'speed.Calm') })}>
    <Orb color={app.settings.highContrast ? '#ffffff' : app.bandColor} liquid={app.settings.theme === 'pour'} beat={b?.beat_hz ?? 1} playing={app.status === 'playing'}
      reduceMotion={app.settings.reduceMotion} flat={app.settings.highContrast} speed={app.settings.orbSpeed} />
  </button>
  <p class="status" aria-live="polite">{status}</p>
  {#if b}
    <div class="listen" role="radiogroup" aria-label={t('ls.label')}>
      {#each [['headphones', 'headphones', 'ls.headphones'], ['speaker', 'speaker', 'ls.speaker']] as const as [id, icon, key] (id)}
        <button role="radio" aria-checked={app.speakerMode === (id === 'speaker')} onclick={() => app.setListening(id)}>
          <Icon name={icon} size={15} />{t(key)}</button>
      {/each}
    </div>
  {/if}
  <p class="hint">{hint}</p>
</section>

<style>
  .stage { display: flex; flex-direction: column; align-items: center; padding: 22px 8px 18px; text-align: center; position: relative; }
  .chip { color: var(--band, var(--accent)); background: color-mix(in srgb, var(--band, var(--accent)) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--band, var(--accent)) 42%, transparent); border-radius: 12px;
    padding: 3px 12px; font-size: 12px; font-weight: 600; letter-spacing: 1px; }
  .title { font-size: 30px; font-weight: 300; margin-top: 12px; line-height: 1.2; }
  .edited { color: var(--dim); font-size: .8em; }
  .meta { color: var(--dim); font-size: 14px; margin-top: 2px; }
  .orb { flex: 1; width: 100%; min-height: 200px; background: none; border: 0; padding: 0; cursor: pointer; border-radius: 24px;
    -webkit-tap-highlight-color: transparent; }
  .orb:focus-visible { outline: 2px solid var(--focus); outline-offset: -6px; }
  .status { color: var(--dim); }
  .listen { display: inline-flex; gap: 2px; padding: 2px; margin-top: 8px; border-radius: 16px;
    border: 1px solid var(--line, rgba(255,255,255,.12)); background: color-mix(in srgb, var(--surface, #111) 60%, transparent); }
  .listen button { display: inline-flex; align-items: center; gap: 5px; min-height: 30px; padding: 4px 12px; border: 0;
    border-radius: 14px; background: none; color: var(--dim); font: inherit; font-size: 12.5px; cursor: pointer; }
  .listen button[aria-checked='true'] { color: var(--text, #fff); background: color-mix(in srgb, var(--accent) 22%, transparent); }
  .listen button:focus-visible { outline: 2px solid var(--focus); outline-offset: 1px; }
  .hint { color: var(--faint); font-size: 12.5px; margin-top: 2px; }
  .banner { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; padding: 10px 14px;
    margin-bottom: 14px; border-radius: 12px; background: var(--surface); }
  @media (orientation: landscape) and (max-height: 500px) {
    /* info on the left, orb on the right: uses the wide, short screen */
    .stage { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); grid-template-rows: auto auto auto 1fr auto auto;
      column-gap: 12px; align-items: center; padding: 4px; text-align: left; }
    .stage > :global(*) { grid-column: 1; }
    .chip { justify-self: start; grid-row: 2; }
    .title { font-size: 22px; margin-top: 6px; grid-row: 3; }
    .meta { grid-row: 4; align-self: start; }
    .status { grid-row: 5; }
    .listen { grid-row: 6; justify-self: start; margin-top: 4px; }
    .orb { grid-column: 2; grid-row: 1 / 7; height: 100%; min-height: 0; }
    .banner { grid-row: 1; grid-column: 1 / 3; margin-bottom: 4px; }
  }
  @media (max-width: 767px), (orientation: landscape) and (max-height: 500px) {
    .stage { padding: 12px 4px; } .title { font-size: 24px; } .hint { display: none; }
  }
</style>
