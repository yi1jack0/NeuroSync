<script lang="ts">
  import { app, BUILTIN } from '../state/app.svelte';
  import { band, CATEGORY_ORDER } from '../domain/bands';
  import { presetCategory, type Preset } from '../domain/preset';
  import Icon from './Icon.svelte';
  import { i18n, t } from '../lib/i18n.svelte';
  const label = (p: Preset) => {
    const b = p.channels.find((c) => c.kind === 'binaural');
    return b ? `${i18n.band(p.band)} · ${+b.beat_hz.toFixed(2)} Hz` : i18n.band(p.band);
  };

  let query = $state('');
  let actionsFor = $state<string | null>(null);

  const groups = $derived.by(() => {
    const q = query.trim().toLowerCase();
    const hit = (p: Preset) => !q || [p.name, i18n.name(p.name), band(p.band).label, i18n.band(p.band)].some((s) => s.toLowerCase().includes(q));
    const map = new Map<string, { p: Preset; user: boolean }[]>();
    for (const p of BUILTIN) if (hit(p)) map.set(presetCategory(p, false), [...(map.get(presetCategory(p, false)) ?? []), { p, user: false }]);
    for (const p of app.user) if (hit(p)) map.set('My Presets', [...(map.get('My Presets') ?? []), { p, user: true }]);
    const order = [...CATEGORY_ORDER, ...[...map.keys()].filter((k) => !CATEGORY_ORDER.includes(k) && k !== 'My Presets'), 'My Presets'];
    return order.filter((k) => map.has(k)).map((k) => ({ name: k, items: map.get(k)! }));
  });
</script>

<nav class="lib glass region-lib" class:open={app.libraryOpen} aria-label={t('region.library')}>
  <div class="head">
    <span class="caps">{t('lib.title')}</span>
    <button class="icon-btn" aria-label={t('lib.new')} title={t('lib.newTip')} onclick={() => app.newSession()}><Icon name="plus" size={16} /></button>
    <button class="icon-btn close" aria-label={t('lib.close')} onclick={() => (app.libraryOpen = false)}><Icon name="close" size={16} /></button>
  </div>
  <input class="search" type="search" placeholder={t('lib.search')} aria-label={t('lib.search')} bind:value={query} />
  <div class="list">
    {#each groups as g (g.name)}
      <div class="group" role="group" aria-label={i18n.category(g.name)}>
        <div class="gname">{i18n.category(g.name)}</div>
        {#each g.items as { p, user } (p.name + user)}
          {@const current = p.name === app.loadedName}
          <div class="item" class:current style:--dot={band(p.band).color}>
            <button class="load" aria-current={current ? 'true' : undefined} onclick={() => app.loadPreset(p)}
              aria-label={[i18n.name(p.name), label(p).replace('Hz', i18n.lang === 'zh' ? '赫兹' : 'hertz'), current ? t('lib.loaded') : ''].filter(Boolean).join(i18n.lang === 'zh' ? '，' : ', ')}
              title={i18n.description(p.name, p.description)}>
              <i aria-hidden="true"></i>
              <span><span class="name">{i18n.name(p.name)}</span><small>{label(p)}</small></span>
            </button>
            <button class="icon-btn more" aria-label={t('lib.actions', { name: i18n.name(p.name) })} aria-expanded={actionsFor === p.name + user}
              onclick={() => (actionsFor = actionsFor === p.name + user ? null : p.name + user)}><Icon name="more" size={16} /></button>
          </div>
          {#if actionsFor === p.name + user}
            <div class="actions">
              <button class="btn" onclick={() => { actionsFor = null; void app.sharePreset(p); }}><Icon name="share" />{t('lib.share')}</button>
              <button class="btn" onclick={() => { actionsFor = null; app.exportPreset(p); }}><Icon name="download" />{t('lib.export')}</button>
              {#if user}<button class="btn danger" onclick={() => { actionsFor = null; void app.deletePreset(p); }}><Icon name="trash" />{t('lib.delete')}</button>{/if}
            </div>
          {/if}
        {/each}
      </div>
    {:else}
      <p class="faint empty">{t('lib.none', { q: query })}</p>
    {/each}
  </div>
  <p class="faint foot">{t('lib.foot')}</p>
</nav>

<style>
  .lib { padding: 16px 12px 12px; display: flex; flex-direction: column; gap: 10px; overflow: hidden; }
  .head { display: flex; align-items: center; padding-left: 6px; }
  .head .caps { flex: 1; }
  .close { display: none; }
  .search { background: rgba(0,0,0,.22); border: 1px solid var(--line); border-radius: 10px; padding: 9px 12px; min-height: 40px; }
  .list { flex: 1; overflow-y: auto; margin: 0 -4px; padding: 0 4px; scrollbar-width: thin; }
  .gname { margin: 12px 0 4px; padding-left: 12px; font-size: 10.5px; font-weight: 700; letter-spacing: 1.6px; color: var(--faint); text-transform: uppercase; }
  :global(:lang(zh)) .gname { letter-spacing: .6px; font-size: 11.5px; }
  .item { position: relative; display: flex; align-items: center; border-radius: 10px; }
  .item:hover { background: var(--panel-hover); }
  .item.current { background: var(--accent-soft); }
  .item.current::before { content: ""; position: absolute; left: 0; top: 12px; bottom: 12px; width: 3px; border-radius: 2px; background: var(--accent); }
  .load { flex: 1; display: flex; gap: 12px; align-items: center; padding: 8px 4px 8px 14px; min-height: 50px; text-align: left;
    background: none; border: 0; border-radius: 10px; }
  .load i { width: 8px; height: 8px; border-radius: 50%; background: var(--dot); flex: none;
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--dot) 22%, transparent); }
  .name { display: block; }
  small { display: block; color: var(--dim); font-size: 11.5px; }
  .more { width: 34px; height: 34px; opacity: 0; color: var(--dim); }
  .item:hover .more, .more:focus-visible, .more[aria-expanded="true"] { opacity: 1; }
  .actions { display: flex; gap: 6px; padding: 4px 8px 8px 34px; flex-wrap: wrap; }
  .actions .btn { display: flex; gap: 6px; align-items: center; padding: 5px 10px; font-size: 12.5px; }
  .actions :global(svg) { width: 15px; height: 15px; }
  .danger { color: var(--danger); }
  .empty { padding: 16px 12px; }
  .foot { text-align: center; }
  @media (hover: none) { .more { opacity: 1; } }
  @media (max-width: 1199px) { .close { display: inline-grid; } }
  @media (max-width: 767px), (orientation: landscape) and (max-height: 500px) { .close { display: none; } .lib { border-radius: var(--radius); } }
</style>
