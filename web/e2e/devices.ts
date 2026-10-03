// Samsung Galaxy S25 Ultra (SM-S938B), default FHD+ resolution (1080 x 2340 px, DPR 2.625).
// Viewports: Chrome/Samsung Internet tab (toolbars visible) vs installed app (standalone).
const UA = 'Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/28.0 Chrome/130.0.0.0 Mobile Safari/537.36';
const base = { userAgent: UA, deviceScaleFactor: 2.625, isMobile: true, hasTouch: true, defaultBrowserType: 'chromium' as const };
export const S25_ULTRA = { ...base, viewport: { width: 412, height: 777 } };
export const S25_ULTRA_APP = { ...base, viewport: { width: 412, height: 891 } };
export const S25_ULTRA_LANDSCAPE = { ...base, viewport: { width: 845, height: 360 } };
export const S25_ULTRA_LANDSCAPE_APP = { ...base, viewport: { width: 891, height: 412 } };
