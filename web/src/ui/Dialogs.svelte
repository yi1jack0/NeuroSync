<script lang="ts">
  // Native <dialog>: focus trap + inert background for free. The safety notice cannot be
  // dismissed except by acknowledging it, and no audio can start before that.
  import { app } from '../state/app.svelte';
  import Icon from './Icon.svelte';
  import { LANGS, t, type Key } from '../lib/i18n.svelte';
  let safety = $state<HTMLDialogElement>(), keys = $state<HTMLDialogElement>();

  $effect(() => {
    const want = app.dialog;
    if (want === 'disclaimer' && !safety?.open) safety?.showModal();
    if (want !== 'disclaimer' && safety?.open) safety.close();
    if (want === 'shortcuts' && !keys?.open) keys?.showModal();
    if (want !== 'shortcuts' && keys?.open) keys.close();
  });
  const SHORTCUTS: [string, Key][] = [
    ['Space', 'keys.play'], ['Shift + Space', 'keys.stop'], ['M', 'keys.mute'],
    ['Ctrl/⌘ + ↑ ↓', 'keys.vol'], ['T', 'keys.timer'], ['S', 'keys.save'], ['N', 'keys.new'],
    ['/', 'keys.search'], ['↑ ↓ ← → PgUp PgDn', 'keys.slider'], ['Esc', 'keys.esc'], ['Enter', 'keys.orb'], ['?', 'keys.help'],
  ];
  const first = $derived(!app.settings.disclaimerAccepted);
</script>

<dialog bind:this={safety} class="card" aria-labelledby="safety-title" oncancel={(e) => e.preventDefault()}>
  {#if first}
    <div class="langs" role="radiogroup" aria-label="Language · 语言">
      {#each LANGS as l (l.id)}
        <button class="chip" role="radio" aria-checked={app.settings.lang === l.id} lang={l.html} onclick={() => app.setLang(l.id, false)}>{l.label}</button>
      {/each}
    </div>
    <p class="kicker">{t('dlg.welcome')}</p>
    <p class="intro">{t('dlg.intro')}</p>
  {/if}
  <div class="h"><span class="ic"><Icon name="headphones" size={34} /></span><h2 id="safety-title">{t('dlg.title')}</h2></div>
  <ul>
    <li><b>{t('dlg.s1t')}</b> <span>{t('dlg.s1')}</span></li>
    <li><b>{t('dlg.s2t')}</b> <span>{t('dlg.s2')}</span></li>
    <li><b>{t('dlg.s3t')}</b> <span>{t('dlg.s3')}</span></li>
    <li><b>{t('dlg.s4t')}</b> <span>{t('dlg.s4')}</span></li>
  </ul>
  <p class="faint">{t('dlg.note')}</p>
  <div class="actions"><button class="btn primary" onclick={() => app.acceptDisclaimer()}>{t('dlg.ok')}</button></div>
</dialog>

<dialog bind:this={keys} class="card" aria-labelledby="keys-title" onclose={() => app.dialog === 'shortcuts' && (app.dialog = 'none')}
  onclick={(e) => e.target === keys && (app.dialog = 'none')}>
  <h2 id="keys-title">{t('keys.title')}</h2>
  <dl>
    {#each SHORTCUTS as [k, d]}<dt><kbd>{k}</kbd></dt><dd>{t(d)}</dd>{/each}
  </dl>
  <div class="actions"><button class="btn" onclick={() => (app.dialog = 'none')}>{t('keys.done')}</button></div>
</dialog>

<style>
  .card { margin: auto; width: min(500px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); overflow: auto; padding: 28px 30px 24px;
    background: var(--surface); color: var(--text); border: 1px solid var(--line-top); border-radius: 20px; }
  .card::backdrop { background: rgba(4,5,7,.75); backdrop-filter: blur(4px); }
  .langs { display: flex; gap: 6px; justify-content: flex-end; margin: -10px -8px 10px 0; }
  .langs .chip { border-radius: 14px; padding: 4px 12px; min-height: 32px; background: var(--panel); border: 1px solid var(--line); font-size: 12.5px; }
  .langs .chip[aria-checked="true"] { background: var(--accent-soft); border-color: var(--accent-line); color: var(--accent); }
  .kicker { color: var(--accent); font-weight: 600; letter-spacing: .5px; margin-bottom: 6px; }
  .intro { color: var(--dim); margin-bottom: 18px; }
  .h { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
  .ic { color: var(--accent); display: grid; }
  h2 { font-size: 22px; font-weight: 300; }
  ul { list-style: none; display: grid; gap: 12px; margin-bottom: 14px; }
  li span { color: var(--dim); }
  .actions { display: flex; justify-content: flex-end; margin-top: 18px; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 9px 18px; margin-top: 14px; align-items: center; }
  dd { color: var(--dim); }
  kbd { font-family: var(--mono); font-size: 12px; padding: 2px 8px; border: 1px solid var(--line-top); border-bottom-width: 2px;
    border-radius: 6px; background: rgba(255,255,255,.05); white-space: nowrap; }
</style>
