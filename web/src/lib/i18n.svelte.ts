// English + Simplified Chinese. `t(key, params)` is reactive: components re-render on switch.
// Built-in preset / sound / band names are translated for display only; stored data keeps the
// canonical English names so presets, links and files stay compatible across languages.
import type { BandName } from '../domain/bands';

export type Lang = 'en' | 'zh';
export const LANGS: { id: Lang; label: string; html: string }[] = [
  { id: 'en', label: 'English', html: 'en' },
  { id: 'zh', label: '简体中文', html: 'zh-Hans' },
];

const en = {
  // regions
  'region.transport': 'Transport', 'region.library': 'Preset library', 'region.now': 'Now playing', 'region.mixer': 'Mixer',
  'region.sections': 'Sections',
  'tab.library': 'Library', 'tab.now': 'Now', 'tab.mixer': 'Mixer',
  // transport
  'tp.openLibrary': 'Open library', 'tp.stop': 'Stop with fade-out', 'tp.stopTip': 'Stop (Shift+Space)',
  'tp.play': 'Play', 'tp.pause': 'Pause', 'tp.playTip': 'Play / pause (Space)',
  'timer.title': 'Sleep timer', 'timer.tip': 'Sleep timer (T)', 'timer.duration': 'Duration', 'timer.off': 'Off',
  'timer.offA11y': 'Timer off', 'timer.min': '{m}m', 'timer.minA11y': '{m} minutes', 'timer.custom': 'Custom',
  'timer.customA11y': 'Custom minutes', 'timer.minUnit': 'min', 'timer.fadeOver': 'Fade out over', 'timer.fadeA11y': 'Fade minutes',
  'timer.note': 'Audio always fades for at least 3 seconds. The timer keeps running in a background tab.',
  'off.ready': 'Offline ready', 'off.caching': 'Caching…', 'off.readyTip': 'Everything is cached: works offline',
  'off.cachingTip': 'Caching for offline use…',
  'vol.mute': 'Mute', 'vol.muteTip': 'Mute (M)', 'vol.master': 'Master volume', 'vol.masterText': '{n} percent of safe maximum',
  'vol.percent': '{n} percent',
  'dev.output': 'Output device', 'dev.outputNamed': 'Output device: {name}', 'dev.default': 'System default',
  // menu
  'menu.menu': 'Menu', 'menu.save': 'Save as preset', 'menu.new': 'New custom session', 'menu.share': 'Share current preset (link)',
  'menu.export': 'Export preset file', 'menu.import': 'Import preset file', 'menu.hc': 'High contrast', 'menu.rm': 'Reduce motion',
  'menu.install': 'Install app', 'menu.installIos': 'Install on this iPhone', 'menu.iosHint': 'To install: tap Share, then “Add to Home Screen”',
  'menu.shortcuts': 'Keyboard shortcuts', 'menu.safety': 'Safety information', 'menu.privacy': 'Privacy: nothing leaves your device',
  'menu.language': 'Language', 'menu.design': 'Design', 'design.classic': 'Classic', 'design.pour': 'Liquid',
  // library
  'lib.title': 'Library', 'lib.new': 'New custom session', 'lib.newTip': 'New custom session (N)', 'lib.close': 'Close library',
  'lib.search': 'Search presets', 'lib.loaded': 'loaded', 'lib.actions': 'Actions for {name}', 'lib.share': 'Share',
  'lib.export': 'Export', 'lib.delete': 'Delete', 'lib.none': 'No presets match “{q}”.',
  'lib.foot': 'Share or export from ⋯ · Import via the main menu',
  'cat.Sleep': 'Sleep', 'cat.Meditate': 'Meditate', 'cat.Focus': 'Focus', 'cat.Creativity': 'Creativity', 'cat.My Presets': 'My Presets',
  // stage
  'st.playing': 'Playing', 'st.playingLeft': 'Playing · {t} remaining', 'st.fading': 'Fading out…', 'st.paused': 'Paused',
  'st.loading': 'Loading sounds…', 'st.stopped': 'Session ended', 'st.ready': 'Ready',
  'st.hintPause': 'Space to pause', 'st.hintResume': 'Space to resume', 'st.hintStart': 'Press Space or ▶ to begin · ? for shortcuts',
  'st.shared': 'Shared preset:', 'st.addShared': 'Add to My Presets', 'st.justPlay': 'Just play it',
  'st.interrupted': 'Playback was paused by your browser or device.', 'st.resume': 'Resume',
  'st.edited': 'edited', 'st.meta': '{base} Hz carrier · {beat} Hz beat', 'st.ambienceOnly': 'Ambience only',
  'orb.label': 'Visualizer speed: {speed}. Activate to change', 'orb.tip': "Click to change the orb's speed",
  'orb.img': 'Visualizer pulsing at {p} per second, synced to a {b} hertz beat',
  'speed.Slow': 'Slow', 'speed.Calm': 'Calm', 'speed.Lively': 'Lively',
  // mixer
  'mx.title': 'Mixer', 'mx.collapse': 'Collapse mixer', 'mx.expand': 'Expand mixer', 'mx.name': 'Preset name',
  'mx.nameA11y': 'New preset name', 'mx.saveBtn': 'Save', 'mx.cancel': 'Cancel', 'mx.unsaved': 'Unsaved changes',
  'mx.save': 'Save as preset', 'mx.saveTip': 'Save as preset (S)', 'mx.generator': 'Custom generator',
  'mx.base': 'Base', 'mx.beat': 'Beat', 'mx.tone': 'Tone', 'mx.baseSpoken': '{v} hertz carrier', 'mx.beatSpoken': '{v} hertz beat',
  'mx.bandSuffix': ', {band} band', 'mx.tip': 'Beat = right ear − left ear. A base of 100–400 Hz gives the clearest beat. Use headphones.',
  'mx.addTone': 'Add binaural tone', 'mx.ambience': 'Ambience', 'mx.addSound': 'Add sound', 'mx.noise': 'Noise',
  'mx.ownFile': 'Your own sound file…', 'mx.empty': 'No ambience yet. Add river, sea or noise to mask distractions.',
  'mx.custom': '{name} (custom)',
  'strip.remove': 'Remove {label}', 'strip.removeTip': 'Remove', 'strip.pan': '{label} pan', 'strip.panTip': 'Pan (double-click to centre)',
  'strip.centre': 'centre', 'strip.left': '{n} percent left', 'strip.right': '{n} percent right', 'strip.mute': 'Mute {label}',
  // dialogs
  'dlg.welcome': 'Welcome to NeuroSync',
  'dlg.intro': 'Binaural beats play a slightly different tone in each ear. Your brain perceives the difference as a gentle pulse that can support focus, relaxation or sleep. Everything runs on your device: no account, no tracking.',
  'dlg.title': 'Before you begin',
  'dlg.s1t': 'Use stereo headphones.', 'dlg.s1': 'Binaural beats only exist when each ear hears its own tone. Speakers mix them.',
  'dlg.s2t': 'Start quiet.', 'dlg.s2': 'Begin at a low volume and raise it slowly to a comfortable level.',
  'dlg.s3t': 'Never while driving', 'dlg.s3': 'or doing anything that needs your full attention.',
  'dlg.s4t': 'Check with a doctor first', 'dlg.s4': 'if you have epilepsy, a seizure disorder, a heart condition, or are pregnant.',
  'dlg.note': 'NeuroSync is a relaxation and focus tool, not a medical device.', 'dlg.ok': 'I understand — continue',
  'keys.title': 'Keyboard shortcuts', 'keys.done': 'Done',
  'keys.play': 'Play / pause', 'keys.stop': 'Stop with fade-out', 'keys.mute': 'Mute master', 'keys.vol': 'Master volume',
  'keys.timer': 'Sleep timer', 'keys.save': 'Save as preset', 'keys.new': 'New custom session', 'keys.search': 'Search presets',
  'keys.slider': 'Adjust the focused slider', 'keys.esc': 'Close menus and dialogs', 'keys.orbKey': 'Enter on the orb (or click it)',
  'keys.orb': 'Change orb speed', 'keys.help': 'This help',
  // toasts
  'ts.complete': 'Session complete — audio stopped', 'ts.builtin': "Built-in presets can't be overwritten — choose another name",
  'ts.noStorage': 'Saving needs browser storage (unavailable here)', 'ts.updated': 'Updated “{name}”', 'ts.saved': 'Saved “{name}” to My Presets',
  'ts.deleted': 'Deleted “{name}”', 'ts.undo': 'Undo', 'ts.restored': 'Restored “{name}”', 'ts.exported': 'Exported “{name}”',
  'ts.exportedDropped': 'Exported ({n} device-only sound(s) left out)', 'ts.imported': 'Imported “{name}”',
  'ts.badFile': "That file isn't a valid NeuroSync preset", 'ts.linkCopied': 'Link copied to clipboard',
  'ts.linkCopiedDropped': 'Link copied (device-only sounds left out)', 'ts.badLink': 'That share link is damaged or incomplete',
  'ts.addedShared': 'Added “{name}” to My Presets', 'ts.soundFailed': "Couldn't open that sound: {e}", 'ts.tooBig': 'That file is larger than 25 MB',
  'ts.noSoundStorage': 'This browser cannot store sounds (private mode?)', 'ts.added': 'Added {name}', 'ts.removed': 'Removed {name}',
  'ts.output': 'Output: {name}', 'ts.outputFail': "Couldn't switch output device", 'ts.orb': 'Orb speed: {name}',
  'ts.audioError': 'Audio problem: {msg}', 'ts.language': 'Language: English',
  'ls.label': 'Listening on', 'ls.headphones': 'Headphones', 'ls.speaker': 'Speaker',
  'ts.speaker': 'Speaker mode: a soft pulse instead of the binaural beat, so the sound never drops out.',
  'ts.headphones': 'Headphones mode: the true binaural beat (each ear hears its own tone).',
  // misc
  'title.idle': 'NeuroSync — Tune your mind', 'title.playing': '▶ {name} · NeuroSync', 'untitled': 'Untitled session',
  'customSession': 'Custom session',
};
export type Key = keyof typeof en;

const zh: Record<Key, string> = {
  'region.transport': '播放控制', 'region.library': '预设库', 'region.now': '正在播放', 'region.mixer': '混音器', 'region.sections': '页面',
  'tab.library': '预设库', 'tab.now': '播放', 'tab.mixer': '混音',
  'tp.openLibrary': '打开预设库', 'tp.stop': '淡出并停止', 'tp.stopTip': '停止（Shift+空格）',
  'tp.play': '播放', 'tp.pause': '暂停', 'tp.playTip': '播放 / 暂停（空格）',
  'timer.title': '睡眠定时', 'timer.tip': '睡眠定时（T）', 'timer.duration': '时长', 'timer.off': '关闭',
  'timer.offA11y': '关闭定时', 'timer.min': '{m}分', 'timer.minA11y': '{m} 分钟', 'timer.custom': '自定义',
  'timer.customA11y': '自定义分钟数', 'timer.minUnit': '分钟', 'timer.fadeOver': '淡出时长', 'timer.fadeA11y': '淡出分钟数',
  'timer.note': '声音停止前至少会淡出 3 秒。即使标签页在后台，定时器也会继续运行。',
  'off.ready': '可离线使用', 'off.caching': '正在缓存…', 'off.readyTip': '已全部缓存：可离线使用', 'off.cachingTip': '正在缓存以便离线使用…',
  'vol.mute': '静音', 'vol.muteTip': '静音（M）', 'vol.master': '主音量', 'vol.masterText': '安全上限的百分之 {n}', 'vol.percent': '百分之 {n}',
  'dev.output': '输出设备', 'dev.outputNamed': '输出设备：{name}', 'dev.default': '系统默认',
  'menu.menu': '菜单', 'menu.save': '保存为预设', 'menu.new': '新建自定义会话', 'menu.share': '分享当前预设（链接）',
  'menu.export': '导出预设文件', 'menu.import': '导入预设文件', 'menu.hc': '高对比度', 'menu.rm': '减少动态效果',
  'menu.install': '安装应用', 'menu.installIos': '安装到这台 iPhone', 'menu.iosHint': '安装方法：点按“分享”，再选择“添加到主屏幕”',
  'menu.shortcuts': '键盘快捷键', 'menu.safety': '安全须知', 'menu.privacy': '隐私：所有数据都留在你的设备上', 'menu.language': '语言', 'menu.design': '设计风格', 'design.classic': '经典', 'design.pour': '流体',
  'lib.title': '预设库', 'lib.new': '新建自定义会话', 'lib.newTip': '新建自定义会话（N）', 'lib.close': '关闭预设库',
  'lib.search': '搜索预设', 'lib.loaded': '已加载', 'lib.actions': '“{name}”的操作', 'lib.share': '分享',
  'lib.export': '导出', 'lib.delete': '删除', 'lib.none': '没有与“{q}”匹配的预设。',
  'lib.foot': '在 ⋯ 中分享或导出 · 通过主菜单导入',
  'cat.Sleep': '睡眠', 'cat.Meditate': '冥想', 'cat.Focus': '专注', 'cat.Creativity': '创造力', 'cat.My Presets': '我的预设',
  'st.playing': '正在播放', 'st.playingLeft': '正在播放 · 剩余 {t}', 'st.fading': '正在淡出…', 'st.paused': '已暂停',
  'st.loading': '正在加载声音…', 'st.stopped': '本次会话已结束', 'st.ready': '准备就绪',
  'st.hintPause': '按空格键暂停', 'st.hintResume': '按空格键继续', 'st.hintStart': '按空格键或 ▶ 开始 · 按 ? 查看快捷键',
  'st.shared': '收到分享的预设：', 'st.addShared': '添加到我的预设', 'st.justPlay': '直接播放',
  'st.interrupted': '播放已被浏览器或设备暂停。', 'st.resume': '继续播放',
  'st.edited': '已修改', 'st.meta': '载波 {base} Hz · 节拍 {beat} Hz', 'st.ambienceOnly': '仅环境音',
  'orb.label': '视觉效果速度：{speed}。点按可切换', 'orb.tip': '点按切换光球速度',
  'orb.img': '视觉效果每秒脉动 {p} 次，与 {b} 赫兹节拍同步',
  'speed.Slow': '慢速', 'speed.Calm': '平缓', 'speed.Lively': '活跃',
  'mx.title': '混音器', 'mx.collapse': '收起混音器', 'mx.expand': '展开混音器', 'mx.name': '预设名称',
  'mx.nameA11y': '新预设名称', 'mx.saveBtn': '保存', 'mx.cancel': '取消', 'mx.unsaved': '有未保存的更改',
  'mx.save': '保存为预设', 'mx.saveTip': '保存为预设（S）', 'mx.generator': '自定义生成器',
  'mx.base': '基频', 'mx.beat': '节拍', 'mx.tone': '音调', 'mx.baseSpoken': '载波 {v} 赫兹', 'mx.beatSpoken': '节拍 {v} 赫兹',
  'mx.bandSuffix': '，{band}', 'mx.tip': '节拍 = 右耳频率 − 左耳频率。基频在 100–400 Hz 时节拍最清晰。请佩戴耳机。',
  'mx.addTone': '添加双耳节拍音', 'mx.ambience': '环境音', 'mx.addSound': '添加声音', 'mx.noise': '噪声',
  'mx.ownFile': '你自己的声音文件…', 'mx.empty': '还没有环境音。添加河流、海浪或噪声来屏蔽干扰。',
  'mx.custom': '{name}（自定义）',
  'strip.remove': '移除{label}', 'strip.removeTip': '移除', 'strip.pan': '{label}声像', 'strip.panTip': '声像（双击居中）',
  'strip.centre': '居中', 'strip.left': '偏左百分之 {n}', 'strip.right': '偏右百分之 {n}', 'strip.mute': '静音{label}',
  'dlg.welcome': '欢迎使用 NeuroSync',
  'dlg.intro': '双耳节拍会让左右耳各听到一个略有差别的音调，大脑会把两者的差异感知为一种柔和的脉动，可帮助专注、放松或入睡。一切都在你的设备上运行：无需账户，没有追踪。',
  'dlg.title': '开始之前',
  'dlg.s1t': '请使用立体声耳机。', 'dlg.s1': '只有左右耳分别听到各自的音调时，才会产生双耳节拍。扬声器会把它们混在一起。',
  'dlg.s2t': '从小音量开始。', 'dlg.s2': '先用较低的音量，再慢慢调到舒适的水平。',
  'dlg.s3t': '切勿在驾驶时使用，', 'dlg.s3': '也不要在任何需要全神贯注的时候使用。',
  'dlg.s4t': '请先咨询医生：', 'dlg.s4': '如果你患有癫痫或其他发作性疾病、心脏病，或正在怀孕。',
  'dlg.note': 'NeuroSync 是放松与专注工具，不是医疗设备。', 'dlg.ok': '我已了解，继续',
  'keys.title': '键盘快捷键', 'keys.done': '完成',
  'keys.play': '播放 / 暂停', 'keys.stop': '淡出并停止', 'keys.mute': '主音量静音', 'keys.vol': '主音量',
  'keys.timer': '睡眠定时', 'keys.save': '保存为预设', 'keys.new': '新建自定义会话', 'keys.search': '搜索预设',
  'keys.slider': '调节当前选中的滑块', 'keys.esc': '关闭菜单和对话框', 'keys.orbKey': '在光球上按回车（或点按光球）',
  'keys.orb': '切换光球速度', 'keys.help': '显示本帮助',
  'ts.complete': '会话结束，声音已停止', 'ts.builtin': '内置预设不能被覆盖，请换一个名称',
  'ts.noStorage': '保存需要浏览器存储（此处不可用）', 'ts.updated': '已更新“{name}”', 'ts.saved': '已将“{name}”保存到我的预设',
  'ts.deleted': '已删除“{name}”', 'ts.undo': '撤销', 'ts.restored': '已恢复“{name}”', 'ts.exported': '已导出“{name}”',
  'ts.exportedDropped': '已导出（{n} 个仅存于本设备的声音未包含）', 'ts.imported': '已导入“{name}”',
  'ts.badFile': '这不是有效的 NeuroSync 预设文件', 'ts.linkCopied': '链接已复制到剪贴板',
  'ts.linkCopiedDropped': '链接已复制（仅存于本设备的声音未包含）', 'ts.badLink': '这个分享链接已损坏或不完整',
  'ts.addedShared': '已将“{name}”添加到我的预设', 'ts.soundFailed': '无法打开这个声音：{e}', 'ts.tooBig': '文件超过 25 MB',
  'ts.noSoundStorage': '此浏览器无法存储声音（是否处于无痕模式？）', 'ts.added': '已添加{name}', 'ts.removed': '已移除{name}',
  'ts.output': '输出：{name}', 'ts.outputFail': '无法切换输出设备', 'ts.orb': '光球速度：{name}',
  'ts.audioError': '音频出现问题：{msg}', 'ts.language': '语言：简体中文',
  'ls.label': '收听方式', 'ls.headphones': '耳机', 'ls.speaker': '扬声器',
  'ts.speaker': '扬声器模式：用柔和的脉动代替双耳节拍，声音不会再断断续续。',
  'ts.headphones': '耳机模式：真正的双耳节拍（左右耳各听一个音）。',
  'title.idle': 'NeuroSync — 调频你的心', 'title.playing': '▶ {name} · NeuroSync', 'untitled': '未命名会话',
  'customSession': '自定义会话',
};

// Display names for built-in content (canonical English names stay in the data).
const ZH_NAMES: Record<string, string> = {
  'Alpha Focus': 'α 波专注', 'Beta Concentration': 'β 波集中', 'Delta Sleep': 'δ 波睡眠', 'Theta Meditation': 'θ 波冥想',
  'Gamma Creativity': 'γ 波创造力', 'River Focus': '小河专注', 'Seaside Meditation': '海边冥想', 'Deep River Sleep': '深河入眠',
  'Ocean Night': '海洋之夜', 'Untitled session': '未命名会话',
  // channels / sounds
  'Binaural': '双耳节拍', 'Pink Noise': '粉红噪声', 'Brown Noise': '棕色噪声', 'White Noise': '白噪声',
  'Pink noise': '粉红噪声', 'Brown noise': '棕色噪声', 'White noise': '白噪声',
  'Gentle River': '潺潺小河', 'Deep River': '深沉河流', 'Peaceful Sea Waves': '宁静海浪', 'Water': '水声',
};
const ZH_DESCRIPTIONS: Record<string, string> = {
  'Alpha Focus': '200 Hz 载波上的 10 Hz α 波，配柔和的粉红噪声。',
  'Beta Concentration': '18 Hz β 波，适合需要警觉和分析的工作。',
  'Delta Sleep': '深沉棕色噪声下的 2 Hz δ 波。',
  'Theta Meditation': '6 Hz θ 波，帮助深度放松。',
  'Gamma Creativity': '40 Hz γ 波，助力灵感与创造性的心流。',
  'River Focus': '潺潺小河中的 10 Hz α 波。',
  'Seaside Meditation': '6 Hz θ 波，伴随缓慢宁静的海浪。',
  'Deep River Sleep': '宽阔深沉的河流承载着 2 Hz δ 波。',
  'Ocean Night': '2.5 Hz δ 波，配海浪和柔和的棕色噪声底色。',
};
const ZH_SOUND_DESCRIPTIONS: Record<string, string> = {
  'river-gentle': '平静的浅河，轻柔地流过光滑的石头。',
  'river-deep': '宽阔深沉的河流，水流稳定、圆润，带着缓慢漂移的涡流。',
  'sea-calm': '缓慢、轻柔的海浪拍打着宁静的沙滩。',
};
const BAND_LABELS: Record<Lang, Record<BandName, string>> = {
  en: { DELTA: 'Delta', THETA: 'Theta', ALPHA: 'Alpha', BETA: 'Beta', GAMMA: 'Gamma' },
  zh: { DELTA: 'δ 波', THETA: 'θ 波', ALPHA: 'α 波', BETA: 'β 波', GAMMA: 'γ 波' },
};

const DICTS: Record<Lang, Record<Key, string>> = { en, zh };
/** Exposed for the completeness test only. */
export const DICTIONARIES = DICTS;

export function detectLang(): Lang {
  const langs = typeof navigator === 'undefined' ? [] : navigator.languages ?? [navigator.language];
  return langs.some((l) => /^zh\b/i.test(l)) ? 'zh' : 'en';
}

class I18n {
  lang = $state<Lang>('en');

  t(key: Key, params: Record<string, string | number> = {}): string {
    const s = DICTS[this.lang][key] ?? en[key];
    return s.replace(/\{(\w+)\}/g, (_, k: string) => String(params[k] ?? `{${k}}`));
  }
  /** Display name for built-in presets / channels / sounds; user-made names pass through unchanged. */
  name(n: string): string { return this.lang === 'zh' ? (ZH_NAMES[n] ?? n) : n; }
  description(presetName: string, fallback: string): string {
    return this.lang === 'zh' ? (ZH_DESCRIPTIONS[presetName] ?? fallback) : fallback;
  }
  soundDescription(id: string, fallback: string): string { return this.lang === 'zh' ? (ZH_SOUND_DESCRIPTIONS[id] ?? fallback) : fallback; }
  band(name: BandName): string { return BAND_LABELS[this.lang][name]; }
  /** Band label for headings like the chip: "ALPHA" in English, "α 波" in Chinese. */
  bandUpper(name: BandName): string { return this.lang === 'zh' ? this.band(name) : this.band(name).toUpperCase(); }
  category(c: string): string { return (DICTS[this.lang] as Record<string, string>)[`cat.${c}`] ?? this.name(c); }
}

export const i18n = new I18n();
export const t = (key: Key, params?: Record<string, string | number>) => i18n.t(key, params);
