<script lang="ts">
  import { app } from '../state/app.svelte';
  import Icon from './Icon.svelte';
  import Popover from './Popover.svelte';
  import { fmtTime } from './format';
  import { isIos, isStandalone, offlineSupported } from '../lib/offline';
  import { LANGS, t } from '../lib/i18n.svelte';
  const iosInstall = isIos() && !isStandalone();

  let timerOpen = $state(false), menuOpen = $state(false), deviceOpen = $state(false);
  let custom = $state(0);
  let fadeOn = $state(app.settings.fadeMinutes > 0);
  let fadeMin = $state(app.settings.fadeMinutes || 5);
  const CHOICES = [0, 15, 30, 45, 60, 90];

  function applyTimer(minutes: number) {
    app.setTimer(minutes, fadeOn ? Math.min(fadeMin, minutes || fadeMin) : 0);
  }
  const countdown = $derived(app.remaining !== null && app.timerMinutes > 0 ? fmtTime(app.remaining) : '');
  const deviceName = $derived(app.devices.find((d) => d.id === app.settings.sinkId)?.label ?? t('dev.default'));
</script>

<header class="top glass region-top" aria-label={t('region.transport')}>
  <button class="icon-btn burger" aria-label={t('tp.openLibrary')} onclick={() => (app.libraryOpen = true)}><Icon name="menu" /></button>
  <div class="brand"><span class="dot-orb" aria-hidden="true"></span><span>Neuro<b>Sync</b></span></div>
  <div class="spacer"></div>

  <button class="icon-btn hide-phone" aria-label={t('tp.stop')} title={t('tp.stopTip')} onclick={() => app.stop()}
    disabled={!app.isPlaying && app.status !== 'paused'}><Icon name="stop" /></button>
  <button class="play" aria-label={app.isPlaying ? t('tp.pause') : t('tp.play')} title={t('tp.playTip')}
    onclick={() => app.toggle()} disabled={app.status === 'loading'}>
    {#if app.status === 'loading'}<span class="spin" aria-hidden="true"></span>{:else}<Icon name={app.isPlaying ? 'pause' : 'play'} size={22} />{/if}
  </button>

  <Popover bind:open={timerOpen} label={t('timer.title')} align="center">
    {#snippet trigger(toggle, open)}
      <button class="icon-btn" data-timer aria-label={t('timer.title')} aria-expanded={open} title={t('timer.tip')} onclick={toggle}
        aria-pressed={app.timerMinutes > 0}><Icon name="timer" /></button>
    {/snippet}
    <div class="timer">
      <div class="caps">{t('timer.title')}</div>
      <div class="chips" role="radiogroup" aria-label={t('timer.duration')}>
        {#each CHOICES as m}
          <button class="chip" role="radio" aria-checked={app.timerMinutes === m && !custom}
            aria-label={m ? t('timer.minA11y', { m }) : t('timer.offA11y')}
            onclick={() => { custom = 0; applyTimer(m); }}>{m ? t('timer.min', { m }) : t('timer.off')}</button>
        {/each}
      </div>
      <label class="row">{t('timer.custom')}
        <input type="number" min="0" max="720" bind:value={custom} onchange={() => applyTimer(custom || 0)} aria-label={t('timer.customA11y')} />
        <span class="faint">{t('timer.minUnit')}</span></label>
      <label class="row"><input type="checkbox" bind:checked={fadeOn} onchange={() => applyTimer(app.timerMinutes)} /> {t('timer.fadeOver')}
        <input type="number" min="1" max="30" bind:value={fadeMin} disabled={!fadeOn} onchange={() => applyTimer(app.timerMinutes)} aria-label={t('timer.fadeA11y')} />
        <span class="faint">{t('timer.minUnit')}</span></label>
      <p class="faint">{t('timer.note')}</p>
    </div>
  </Popover>
  <span class="count mono" aria-live="off">{countdown}</span>
  <div class="spacer"></div>

  {#if offlineSupported}
    <div class="offline hide-phone" role="status" title={app.offlineReady ? t('off.readyTip') : t('off.cachingTip')}>
      <i class:ready={app.offlineReady}></i><span>{app.offlineReady ? t('off.ready') : t('off.caching')}</span>
    </div>
  {/if}
  <button class="icon-btn hide-phone mutebtn" aria-label={t('vol.mute')} aria-pressed={app.muted} onclick={() => app.toggleMute()} title={t('vol.muteTip')}>
    <Icon name={app.muted ? 'mute' : 'volume'} /></button>
  <input class="master hide-phone" type="range" min="0" max="100" step="1" value={app.masterPct} style:--p="{app.masterPct}%"
    aria-label={t('vol.master')} aria-valuetext={t('vol.masterText', { n: app.masterPct })}
    oninput={(e) => app.setMasterPct(+(e.currentTarget as HTMLInputElement).value)} />
  <span class="pct mono hide-phone">{app.masterPct}%</span>

  {#if app.canChooseOutput}
    <Popover bind:open={deviceOpen} label={t('dev.output')}>
      {#snippet trigger(toggle, open)}
        <button class="btn device hide-phone" aria-expanded={open} aria-label={t('dev.outputNamed', { name: deviceName })}
          onclick={() => { toggle(); if (!open) void app.refreshDevices(true); }}>
          <Icon name="device" /><span>{deviceName}</span><Icon name="chevron" /></button>
      {/snippet}
      <button class="menu-item" onclick={() => { void app.chooseDevice(''); deviceOpen = false; }}>{t('dev.default')}
        {#if !app.settings.sinkId}<span class="check"><Icon name="check" size={16} /></span>{/if}</button>
      {#each app.devices as d (d.id)}
        <button class="menu-item" onclick={() => { void app.chooseDevice(d.id); deviceOpen = false; }}>{d.label}
          {#if app.settings.sinkId === d.id}<span class="check"><Icon name="check" size={16} /></span>{/if}</button>
      {/each}
    </Popover>
  {/if}

  <Popover bind:open={menuOpen} label={t('menu.menu')}>
    {#snippet trigger(toggle, open)}
      <button class="icon-btn" aria-label={t('menu.menu')} aria-expanded={open} onclick={toggle}><Icon name="more" /></button>
    {/snippet}
    <div class="phone-only volrow">
      <button class="icon-btn" aria-label={t('vol.mute')} aria-pressed={app.muted} onclick={() => app.toggleMute()}><Icon name={app.muted ? 'mute' : 'volume'} /></button>
      <input type="range" min="0" max="100" value={app.masterPct} style:--p="{app.masterPct}%" aria-label={t('vol.master')}
        aria-valuetext={t('vol.percent', { n: app.masterPct })} oninput={(e) => app.setMasterPct(+(e.currentTarget as HTMLInputElement).value)} />
      <span class="mono">{app.masterPct}%</span>
    </div>
    <button class="menu-item" onclick={() => { menuOpen = false; app.saving = true; app.tab = 'mixer'; }}><Icon name="save" />{t('menu.save')}</button>
    <button class="menu-item" onclick={() => { menuOpen = false; app.newSession(); }}><Icon name="plus" />{t('menu.new')}</button>
    <button class="menu-item" onclick={() => { menuOpen = false; void app.sharePreset(); }}><Icon name="share" />{t('menu.share')}</button>
    <button class="menu-item" onclick={() => { menuOpen = false; app.exportPreset(); }}><Icon name="download" />{t('menu.export')}</button>
    <button class="menu-item" onclick={() => { menuOpen = false; void app.importPreset(); }}><Icon name="upload" />{t('menu.import')}</button>
    <div class="menu-sep"></div>
    <button class="menu-item" role="menuitemcheckbox" aria-checked={app.settings.highContrast}
      onclick={() => app.setPref('highContrast', !app.settings.highContrast)}><Icon name="contrast" />{t('menu.hc')}
      {#if app.settings.highContrast}<span class="check"><Icon name="check" size={16} /></span>{/if}</button>
    <button class="menu-item" role="menuitemcheckbox" aria-checked={app.settings.reduceMotion}
      onclick={() => app.setPref('reduceMotion', !app.settings.reduceMotion)}><Icon name="motion" />{t('menu.rm')}
      {#if app.settings.reduceMotion}<span class="check"><Icon name="check" size={16} /></span>{/if}</button>
    {#if app.installPrompt}
      <button class="menu-item" onclick={() => { menuOpen = false; void app.install(); }}><Icon name="install" />{t('menu.install')}</button>
    {:else if iosInstall}
      <button class="menu-item" onclick={() => { menuOpen = false; app.toast(t('menu.iosHint')); }}><Icon name="install" />{t('menu.installIos')}</button>
    {/if}
    <div class="menu-sep"></div>
    <div class="menu-section" id="lang-label">{t('menu.language')} · Language</div>
    <div class="langs" role="radiogroup" aria-labelledby="lang-label">
      {#each LANGS as l (l.id)}
        <button class="chip" role="radio" aria-checked={app.settings.lang === l.id} lang={l.html}
          onclick={() => app.setLang(l.id)}>{l.label}</button>
      {/each}
    </div>
    <div class="menu-sep"></div>
    <button class="menu-item" onclick={() => { menuOpen = false; app.dialog = 'shortcuts'; }}><Icon name="keyboard" />{t('menu.shortcuts')}</button>
    <button class="menu-item" onclick={() => { menuOpen = false; app.dialog = 'disclaimer'; }}><Icon name="headphones" />{t('menu.safety')}</button>
    <a class="menu-item" href={app.settings.lang === 'zh' ? '/privacy.html#zh' : '/privacy.html'} target="_blank" rel="noopener"><Icon name="contrast" />{t('menu.privacy')}</a>
  </Popover>
</header>

<style>
  .top { display: flex; align-items: center; gap: 10px; padding: 0 14px 0 18px; border-radius: 14px; }
  @media (orientation: landscape) and (max-height: 500px) {
    .play { width: 40px !important; height: 40px !important; box-shadow: 0 0 0 4px var(--accent-soft) !important; }
    .brand { font-size: 14px !important; }
  }
  .brand { display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 600; letter-spacing: .4px; white-space: nowrap; }
  .brand b { font-weight: 300; color: var(--accent); }
  .dot-orb { width: 24px; height: 24px; border-radius: 50%; flex: none;
    background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--accent) 30%, #fff), var(--accent) 45%, color-mix(in srgb, var(--accent) 35%, #000) 100%); }
  .spacer { flex: 1; }
  .burger, .phone-only { display: none; }
  .play { width: 52px; height: 52px; border-radius: 50%; border: none; background: var(--accent); color: #0B0C0E; flex: none;
    display: grid; place-items: center; box-shadow: 0 0 0 6px var(--accent-soft), 0 6px 30px color-mix(in srgb, var(--accent) 35%, transparent);
    transition: transform .12s, filter .15s; }
  .play:hover { filter: brightness(1.08); } .play:active { transform: scale(.96); }
  .play:focus-visible { outline: 3px solid var(--text); outline-offset: 3px; border-radius: 50%; }
  .spin { width: 20px; height: 20px; border: 2.5px solid #0B0C0E; border-right-color: transparent; border-radius: 50%; animation: s 0.8s linear infinite; }
  @keyframes s { to { transform: rotate(1turn); } }
  .count { color: var(--accent); font-size: 15px; min-width: 64px; }
  .offline { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--dim); white-space: nowrap; }
  .offline i { width: 7px; height: 7px; border-radius: 50%; background: var(--faint); }
  .offline i.ready { background: var(--ok); box-shadow: 0 0 8px var(--ok); }
  .master { width: 150px; height: 28px; }
  .pct { font-weight: 600; width: 42px; }
  .device { display: flex; align-items: center; gap: 8px; max-width: 240px; }
  .device span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .timer { width: 320px; display: grid; gap: 12px; padding: 10px 8px; }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip { border-radius: 14px; padding: 6px 12px; min-height: 36px; background: var(--panel); border: 1px solid var(--line); }
  .chip[aria-checked="true"] { background: var(--accent-soft); border-color: var(--accent-line); color: var(--accent); }
  .row { display: flex; align-items: center; gap: 8px; }
  .row input[type=number] { width: 70px; background: rgba(0,0,0,.25); border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; }
  .row input[type=checkbox] { width: 18px; height: 18px; accent-color: var(--accent); }
  .volrow { align-items: center; gap: 8px; padding: 6px 8px 10px; }
  .langs { display: flex; gap: 6px; padding: 2px 10px 6px; }
  .volrow input { flex: 1; height: 36px; }
  @media (max-width: 1199px) {
    .burger { display: inline-grid; }
    .offline span, .mutebtn { display: none; }
    .master { width: 110px; } .device span { display: none; }
  }
  @media (max-width: 767px), (orientation: landscape) and (max-height: 500px) {
    .top { padding: 0 4px 0 6px; gap: 4px; }
    .hide-phone { display: none !important; }
    .phone-only { display: flex; }
    .burger { display: none; }
    .brand { font-size: 15px; gap: 8px; }
    .play { width: 46px; height: 46px; }
    .count { min-width: 0; font-size: 14px; }
    .timer { width: auto; }
  }
</style>
