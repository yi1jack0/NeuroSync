<script lang="ts">
  // Native <dialog>: focus trap + inert background for free. The safety notice cannot be
  // dismissed except by acknowledging it, and no audio can start before that.
  import { app } from '../state/app.svelte';
  import Icon from './Icon.svelte';
  let safety = $state<HTMLDialogElement>(), keys = $state<HTMLDialogElement>();

  $effect(() => {
    const want = app.dialog;
    if (want === 'disclaimer' && !safety?.open) safety?.showModal();
    if (want !== 'disclaimer' && safety?.open) safety.close();
    if (want === 'shortcuts' && !keys?.open) keys?.showModal();
    if (want !== 'shortcuts' && keys?.open) keys.close();
  });
  const SHORTCUTS: [string, string][] = [
    ['Space', 'Play / pause'], ['Shift + Space', 'Stop with fade-out'], ['M', 'Mute master'],
    ['Ctrl/⌘ + ↑ ↓', 'Master volume'], ['T', 'Sleep timer'], ['S', 'Save as preset'], ['N', 'New custom session'],
    ['/', 'Search presets'], ['↑ ↓ ← → PgUp PgDn', 'Adjust the focused slider'], ['Esc', 'Close menus and dialogs'], ['Enter on the orb (or click it)', 'Change orb speed'], ['?', 'This help'],
  ];
  const first = $derived(!app.settings.disclaimerAccepted);
</script>

<dialog bind:this={safety} class="card" aria-labelledby="safety-title" oncancel={(e) => e.preventDefault()}>
  {#if first}
    <p class="kicker">Welcome to NeuroSync</p>
    <p class="intro">Binaural beats play a slightly different tone in each ear. Your brain perceives the difference as a gentle
      pulse that can support focus, relaxation or sleep. Everything runs on your device: no account, no tracking.</p>
  {/if}
  <div class="h"><span class="ic"><Icon name="headphones" size={34} /></span><h2 id="safety-title">Before you begin</h2></div>
  <ul>
    <li><b>Use stereo headphones.</b> <span>Binaural beats only exist when each ear hears its own tone. Speakers mix them.</span></li>
    <li><b>Start quiet.</b> <span>Begin at a low volume and raise it slowly to a comfortable level.</span></li>
    <li><b>Never while driving</b> <span>or doing anything that needs your full attention.</span></li>
    <li><b>Check with a doctor first</b> <span>if you have epilepsy, a seizure disorder, a heart condition, or are pregnant.</span></li>
  </ul>
  <p class="faint">NeuroSync is a relaxation and focus tool, not a medical device.</p>
  <div class="actions"><button class="btn primary" onclick={() => app.acceptDisclaimer()}>I understand — continue</button></div>
</dialog>

<dialog bind:this={keys} class="card" aria-labelledby="keys-title" onclose={() => app.dialog === 'shortcuts' && (app.dialog = 'none')}
  onclick={(e) => e.target === keys && (app.dialog = 'none')}>
  <h2 id="keys-title">Keyboard shortcuts</h2>
  <dl>
    {#each SHORTCUTS as [k, d]}<dt><kbd>{k}</kbd></dt><dd>{d}</dd>{/each}
  </dl>
  <div class="actions"><button class="btn" onclick={() => (app.dialog = 'none')}>Done</button></div>
</dialog>

<style>
  .card { margin: auto; width: min(500px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); overflow: auto; padding: 28px 30px 24px;
    background: var(--surface); color: var(--text); border: 1px solid var(--line-top); border-radius: 20px; }
  .card::backdrop { background: rgba(4,5,7,.75); backdrop-filter: blur(4px); }
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
