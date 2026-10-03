<script lang="ts">
  import { app } from '../state/app.svelte';
  import { fly } from 'svelte/transition';
</script>

<div class="toasts" role="status" aria-live="polite">
  {#each app.toasts as t (t.id)}
    <div class="toast" transition:fly={{ y: 12, duration: 200 }}>
      <i aria-hidden="true"></i><span>{t.text}</span>
      {#if t.action}<button onclick={() => { t.action?.run(); app.toasts = app.toasts.filter((x) => x.id !== t.id); }}>{t.action.label}</button>{/if}
    </div>
  {/each}
</div>

<style>
  .toasts { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%); z-index: 60; display: grid; gap: 8px; justify-items: center; pointer-events: none; }
  .toast { pointer-events: auto; display: flex; gap: 12px; align-items: center; padding: 10px 14px 10px 16px; border-radius: 12px;
    background: var(--surface); border: 1px solid var(--line-top); box-shadow: 0 12px 40px rgba(0,0,0,.45); max-width: calc(100vw - 24px); }
  i { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); flex: none; }
  button { background: none; border: 0; color: var(--accent); font-weight: 600; padding: 4px 8px; }
  @media (max-width: 1199px) { .toasts { bottom: auto; top: 90px; } }
  @media (max-width: 767px) { .toasts { top: auto; bottom: calc(80px + env(safe-area-inset-bottom)); } }
</style>
