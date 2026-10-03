import { describe, expect, it } from 'vitest';
import { DICTIONARIES, i18n, t } from './i18n.svelte';
import presets from '../generated/presets.json';
import catalog from '../generated/catalog.json';

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(',');

describe('i18n', () => {
  it('every Chinese string exists and uses the same placeholders as English', () => {
    const { en, zh } = DICTIONARIES;
    expect(Object.keys(zh).sort()).toEqual(Object.keys(en).sort());
    for (const k of Object.keys(en) as (keyof typeof en)[]) {
      expect(zh[k].trim(), k).not.toBe('');
      expect(placeholders(zh[k]), k).toBe(placeholders(en[k]));
    }
  });

  it('all built-in presets, sounds and noise names have Chinese display names', () => {
    i18n.lang = 'zh';
    for (const p of presets as { name: string; channels: { name: string }[] }[]) {
      expect(i18n.name(p.name), p.name).not.toBe(p.name);
      for (const c of p.channels) expect(i18n.name(c.name), c.name).not.toBe(c.name);
    }
    for (const s of catalog as { name: string; category: string }[]) {
      expect(i18n.name(s.name)).not.toBe(s.name);
      expect(i18n.name(s.category)).not.toBe(s.category);
    }
    expect(i18n.name('My own preset')).toBe('My own preset');      // user names pass through
    i18n.lang = 'en';
    expect(i18n.name('Alpha Focus')).toBe('Alpha Focus');
  });

  it('fills placeholders', () => {
    i18n.lang = 'zh';
    expect(t('ts.saved', { name: '深度工作' })).toBe('已将“深度工作”保存到我的预设');
    i18n.lang = 'en';
    expect(t('st.meta', { base: 200, beat: 10.5 })).toBe('200 Hz carrier · 10.5 Hz beat');
  });
});
