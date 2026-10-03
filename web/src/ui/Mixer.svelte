<script lang="ts">
  import { app, CATALOG } from '../state/app.svelte';
  import { bandForFrequency } from '../domain/bands';
  import { BASE_FREQ_MAX_HZ, BASE_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ, BEAT_FREQ_MIN_HZ } from '../domain/limits';
  import Icon from './Icon.svelte';
  import Popover from './Popover.svelte';
  import Strip from './Strip.svelte';

  let addOpen = $state(false);
  let name = $state('');
  let nameInput = $state<HTMLInputElement>();

  const genIndex = $derived(app.draft.channels.findIndex((c) => c.kind === 'binaural'));
  const gen = $derived(genIndex >= 0 ? app.draft.channels[genIndex] : undefined);
  const ambience = $derived(app.draft.channels.map((c, i) => ({ c, i })).filter(({ i }) => i !== genIndex));
  const pct = (v: number) => `${Math.round(v * 100)}%`;
  const spokenPct = (v: number) => `${Math.round(v * 100)} percent`;

  $effect(() => {
    if (app.saving) {
      name = app.user.some((p) => p.name === app.draft.name) ? app.draft.name
        : app.draft.name === 'Untitled session' ? '' : `${app.draft.name} (custom)`;
      queueMicrotask(() => { nameInput?.focus(); nameInput?.select(); });
    }
  });
  function add(key: string) { addOpen = false; void app.addChannel(key); }
</script>

<aside class="mix glass region-mix" class:open={app.mixerOpen} aria-label="Mixer">
  <button class="drawer-handle" aria-label={app.mixerOpen ? 'Collapse mixer' : 'Expand mixer'} aria-expanded={app.mixerOpen}
    onclick={() => (app.mixerOpen = !app.mixerOpen)}><span></span></button>
  <div class="head">
    {#if app.saving}
      <form class="saveform" onsubmit={(e) => { e.preventDefault(); void app.savePreset(name); }}>
        <input bind:this={nameInput} bind:value={name} maxlength="48" placeholder="Preset name" aria-label="New preset name"
          onkeydown={(e) => e.key === 'Escape' && (app.saving = false)} />
        <button class="btn primary" type="submit" disabled={!name.trim()}>Save</button>
        <button class="icon-btn" type="button" aria-label="Cancel" onclick={() => (app.saving = false)}><Icon name="close" size={16} /></button>
      </form>
    {:else}
      <span class="caps">Mixer</span>
      {#if app.dirty}<span class="dirty" title="Unsaved changes" aria-label="Unsaved changes">●</span>{/if}
      <span class="spacer"></span>
      <button class="btn" class:primary={app.dirty} onclick={() => (app.saving = true)} title="Save as preset (S)">Save as preset</button>
    {/if}
  </div>

  <div class="body">
    <section aria-label="Custom generator">
      <div class="caps sub">Custom generator</div>
      {#if gen}
        <div class="row">
          <Strip label="Base" icon="wave" generator min={BASE_FREQ_MIN_HZ} max={BASE_FREQ_MAX_HZ} step={1} value={gen.base_hz}
            fmt={(v) => `${v.toFixed(0)} Hz`} spoken={(v) => `${v.toFixed(0)} hertz carrier`}
            onchange={(v) => app.updateChannel(genIndex, { base_hz: v })} />
          <Strip label="Beat" icon="orb" generator min={BEAT_FREQ_MIN_HZ} max={BEAT_FREQ_MAX_HZ} step={0.1} value={gen.beat_hz}
            fmt={(v) => `${v.toFixed(1)} Hz`} spoken={(v) => `${v.toFixed(1)} hertz beat`}
            bandLabel={bandForFrequency(gen.beat_hz).label.toUpperCase()} bandColor={app.settings.highContrast ? '#ff0' : bandForFrequency(gen.beat_hz).color}
            onchange={(v) => app.updateChannel(genIndex, { beat_hz: v })} />
          <Strip label="Tone" icon="headphones" generator min={0} max={1} step={0.01} value={gen.volume} fmt={pct} spoken={spokenPct}
            muted={gen.muted} onmute={(m) => app.updateChannel(genIndex, { muted: m })}
            onchange={(v) => app.updateChannel(genIndex, { volume: v })} />
          <p class="faint tip">Beat = right ear − left ear. A base of 100–400 Hz gives the clearest beat. Use headphones.</p>
        </div>
      {:else}
        <button class="btn ghost addgen" onclick={() => app.addChannel('binaural')}><Icon name="plus" /> Add binaural tone</button>
      {/if}
    </section>

    <div class="divider"></div>

    <section aria-label="Ambience">
      <div class="subhead">
        <span class="caps">Ambience</span>
        <Popover bind:open={addOpen} label="Add sound" up>
          {#snippet trigger(toggle, open)}
            <button class="btn addbtn" aria-expanded={open} onclick={toggle}><Icon name="plus" size={16} /> Add sound</button>
          {/snippet}
          <div class="menu-section">Noise</div>
          <button class="menu-item" onclick={() => add('pink')}><Icon name="noise" />Pink noise</button>
          <button class="menu-item" onclick={() => add('brown')}><Icon name="noise" />Brown noise</button>
          <button class="menu-item" onclick={() => add('white')}><Icon name="noise" />White noise</button>
          {#each [...new Set(CATALOG.map((s) => s.category))] as cat}
            <div class="menu-section">{cat}</div>
            {#each CATALOG.filter((s) => s.category === cat) as s (s.id)}
              <button class="menu-item" title={s.description} onclick={() => add('asset:' + s.id)}><Icon name="wave" />{s.name}</button>
            {/each}
          {/each}
          <div class="menu-sep"></div>
          <button class="menu-item" onclick={() => add('file')}><Icon name="file" />Your own sound file…</button>
        </Popover>
      </div>
      <div class="row amb">
        {#each ambience as { c, i } (c.name + i)}
          <Strip label={c.name} icon={c.kind === 'noise' ? 'noise' : c.path.startsWith('asset:') ? 'wave' : 'file'}
            min={0} max={1} step={0.01} value={c.volume} fmt={pct} spoken={spokenPct}
            muted={c.muted} onmute={(m) => app.updateChannel(i, { muted: m })}
            pan={c.pan} onpan={(p) => app.updateChannel(i, { pan: p })}
            onremove={() => app.removeChannel(i)} onchange={(v) => app.updateChannel(i, { volume: v })} />
        {:else}
          <p class="faint empty">No ambience yet. Add river, sea or noise to mask distractions.</p>
        {/each}
      </div>
    </section>
  </div>
</aside>

<style>
  .mix { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 12px; overflow: hidden; }
  .head { display: flex; align-items: center; gap: 8px; min-height: 40px; }
  .spacer { flex: 1; }
  .dirty { color: var(--accent); font-size: 10px; }
  .saveform { display: flex; gap: 6px; flex: 1; }
  .saveform input { flex: 1; min-width: 0; background: rgba(0,0,0,.25); border: 1px solid var(--line); border-radius: 8px; padding: 7px 10px; }
  .body { flex: 1; display: flex; flex-direction: column; gap: 12px; overflow: auto; min-height: 0; }
  section { display: flex; flex-direction: column; min-height: 0; }
  .sub { margin-bottom: 8px; }
  .subhead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .row { display: flex; gap: 8px; min-height: 280px; }
  .amb { overflow-x: auto; padding-bottom: 4px; scrollbar-width: thin; }
  .tip { width: 90px; flex: none; line-height: 1.35; }
  .divider { height: 1px; background: var(--line); flex: none; }
  .addbtn { display: flex; gap: 6px; align-items: center; padding: 6px 10px; }
  .addgen { min-height: 120px; width: 100%; display: flex; gap: 8px; align-items: center; justify-content: center; }
  .empty { padding: 12px 4px; max-width: 220px; }
  .drawer-handle { display: none; align-self: center; width: 60px; height: 20px; margin: -8px 0 -6px; background: none; border: 0; }
  .drawer-handle span { display: block; width: 44px; height: 5px; margin: auto; border-radius: 3px; background: var(--line-top); }
  @media (max-width: 1199px) {
    .mix { border-radius: 22px 22px var(--radius) var(--radius); padding-top: 10px; max-height: 64px; transition: max-height .3s ease; }
    .mix.open { max-height: 460px; }
    .drawer-handle { display: block; }
    .body { flex-direction: row; justify-content: center; gap: 18px; }
    section[aria-label="Ambience"] { min-width: 230px; }
    .subhead { gap: 12px; }
    .divider { width: 1px; height: auto; }
    .row { min-height: 250px; }
    .tip { display: none; }
  }
  @media (max-width: 767px) {
    .mix, .mix.open { max-height: none; border-radius: var(--radius); }
    .drawer-handle { display: none; }
    .body { flex-direction: column; justify-content: flex-start; gap: 10px; }
    section[aria-label="Ambience"] { min-width: 0; }
    .divider { width: auto; height: 1px; }
    .row { flex-direction: column; min-height: 0; gap: 6px; }
    .amb { overflow: visible; }
    .tip { display: block; width: auto; }
  }
</style>
