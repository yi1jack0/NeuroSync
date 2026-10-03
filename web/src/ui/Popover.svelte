<script lang="ts">
  // Anchored popover: click-outside and Escape close it; focus moves inside on open
  // and returns to the trigger on close.
  import type { Snippet } from 'svelte';
  let { open = $bindable(false), align = 'end', up = false, label, children, trigger }:
    { open?: boolean; align?: 'start' | 'end' | 'center'; up?: boolean; label: string; children: Snippet; trigger: Snippet<[() => void, boolean]> } = $props();
  let root: HTMLElement, panel = $state<HTMLElement>();
  const toggle = () => (open = !open);

  $effect(() => {
    if (!open) return;
    queueMicrotask(() => (panel?.querySelector<HTMLElement>('button,input,[tabindex]') ?? panel)?.focus());
    const down = (e: PointerEvent) => { if (!root.contains(e.target as Node)) open = false; };
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { open = false; root.querySelector<HTMLElement>('button')?.focus(); e.stopPropagation(); }
    };
    document.addEventListener('pointerdown', down, true);
    document.addEventListener('keydown', key, true);
    return () => { document.removeEventListener('pointerdown', down, true); document.removeEventListener('keydown', key, true); };
  });
</script>

<div class="anchor" bind:this={root}>
  {@render trigger(toggle, open)}
  {#if open}
    <div class="pop {align}" class:up bind:this={panel} role="dialog" aria-label={label} tabindex="-1">{@render children()}</div>
  {/if}
</div>

<style>
  .anchor { position: relative; display: inline-flex; }
  .pop { top: calc(100% + 8px); }
  .pop.up { top: auto; bottom: calc(100% + 8px); }
  .end { right: 0; } .start { left: 0; } .center { left: 50%; transform: translateX(-50%); }
  @media (max-width: 767px) {
    .pop { position: fixed; left: 10px !important; right: 10px !important; top: auto !important; bottom: calc(76px + env(safe-area-inset-bottom)) !important;
      transform: none !important; max-height: 70dvh; overflow: auto; }
  }
</style>
