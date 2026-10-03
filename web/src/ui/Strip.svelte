<script lang="ts">
  // One mixer channel: native range input (keyboard + screen readers for free) with a
  // spoken value, optional band label, mute, pan and remove.
  import Icon from './Icon.svelte';
  interface Props {
    label: string; icon: string; min: number; max: number; step: number; value: number;
    fmt: (v: number) => string; spoken: (v: number) => string; onchange: (v: number) => void;
    generator?: boolean; bandLabel?: string; bandColor?: string;
    muted?: boolean; onmute?: (m: boolean) => void; pan?: number; onpan?: (p: number) => void; onremove?: () => void;
  }
  let { label, icon, min, max, step, value, fmt, spoken, onchange, generator = false, bandLabel, bandColor,
        muted, onmute, pan, onpan, onremove }: Props = $props();
  const pct = $derived(((value - min) / (max - min)) * 100);
  const id = `s-${Math.random().toString(36).slice(2, 8)}`;
</script>

<div class="strip" class:gen={generator} role="group" aria-labelledby="{id}-l">
  <div class="head">
    <span class="ic"><Icon name={icon} size={18} /></span>
    {#if onremove}
      <button class="rm icon-btn" onclick={onremove} aria-label="Remove {label}" title="Remove"><Icon name="close" size={13} /></button>
    {/if}
  </div>
  <span class="lbl" id="{id}-l">{label}</span>
  <span class="val mono">{fmt(value)}</span>
  {#if bandLabel}<span class="band" style:color={bandColor}>{bandLabel}</span>{/if}
  <div class="fader">
    <input type="range" class="vertical" {min} {max} {step} {value} style:--p="{pct}%"
      aria-labelledby="{id}-l" aria-valuetext={spoken(value) + (bandLabel ? `, ${bandLabel.toLowerCase()} band` : '')}
      disabled={muted === true} oninput={(e) => onchange(+(e.currentTarget as HTMLInputElement).value)} />
  </div>
  {#if pan !== undefined && onpan}
    <input type="range" class="pan" min="-1" max="1" step="0.05" value={pan} style:--p="{(pan + 1) * 50}%"
      aria-label="{label} pan" aria-valuetext={pan === 0 ? 'centre' : pan < 0 ? `${Math.round(-pan * 100)} percent left` : `${Math.round(pan * 100)} percent right`}
      ondblclick={() => onpan(0)} oninput={(e) => onpan(+(e.currentTarget as HTMLInputElement).value)} title="Pan (double-click to centre)" />
  {/if}
  {#if onmute}
    <button class="icon-btn mute" aria-pressed={muted} aria-label="Mute {label}" onclick={() => onmute(!muted)}
      style:color={muted ? 'var(--danger)' : 'var(--dim)'}><Icon name={muted ? 'mute' : 'volume'} size={17} /></button>
  {/if}
</div>

<style>
  .strip { width: 86px; flex: none; padding: 10px 6px; display: flex; flex-direction: column; align-items: center; gap: 4px;
    border-radius: 12px; background: var(--panel); border: 1px solid var(--line); transition: border-color .15s; }
  .strip:hover { border-color: var(--line-top); }
  .gen { background: color-mix(in srgb, var(--accent) 6%, transparent); border-color: color-mix(in srgb, var(--accent) 22%, transparent); }
  .head { display: flex; align-items: center; justify-content: center; gap: 2px; height: 22px; }
  .ic { color: var(--accent); display: grid; }
  .rm { width: 24px; height: 24px; color: var(--faint); }
  .lbl { font-size: 11.5px; color: var(--dim); text-align: center; line-height: 1.2; min-height: 28px; display: flex; align-items: center; }
  .val { font-weight: 600; font-size: 13.5px; }
  .band { font-size: 10.5px; font-weight: 700; letter-spacing: 1px; transition: color .6s; }
  .fader { flex: 1; min-height: 110px; display: flex; justify-content: center; padding: 6px 0; }
  .pan { width: 64px; height: 24px; --p: 50%; }
  .mute { width: 36px; height: 36px; }
  @media (max-width: 1199px) { .fader { min-height: 96px; max-height: 130px; } }
  @media (max-width: 767px) {
    .strip { width: 100%; flex-direction: row; flex-wrap: wrap; padding: 6px 10px 6px 12px; gap: 4px 10px; min-height: 52px; }
    .head { display: none; }
    .lbl { width: 84px; min-height: 0; text-align: left; justify-content: flex-start; order: 1; }
    .fader { order: 2; flex: 1; min-height: 0; padding: 0; }
    .fader input { writing-mode: horizontal-tb; direction: ltr; width: 100%; height: 36px; min-height: 0; }
    .val { order: 3; width: 64px; text-align: right; font-size: 13px; }
    .band { order: 4; width: 100%; padding-left: 94px; margin-top: -6px; font-size: 9.5px; }
    .mute { order: 5; }
    .pan { display: none; }
    .rm { display: grid; order: 6; }
    .head:has(.rm) { display: contents; }
    .head:has(.rm) .ic { display: none; }
  }
  @media (max-width: 767px) {
    .fader input::-webkit-slider-runnable-track { width: auto; height: 6px;
      background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 35%, transparent), var(--accent) var(--p), rgba(255,255,255,.09) var(--p)); }
    .fader input::-webkit-slider-thumb { margin-left: 0; margin-top: -9px; width: 24px; height: 24px; }
  }
</style>
