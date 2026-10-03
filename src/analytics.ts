/*
 * GA4와 메타 픽셀 로더.
 *
 * 빌드 환경변수(VITE_GA4_ID, VITE_META_PIXEL_ID)가 없으면 아무 스크립트도 붙지 않는다.
 * 값이 있어도 방문자가 동의 배너에서 "동의"를 누르기 전까지는 불러오지 않는다.
 * 화면 이동은 해시 라우트(#cases, #event/...)라서 페이지뷰를 직접 보낸다.
 */

type Consent = "granted" | "denied";

const CONSENT_KEY = "floodops-analytics-consent";
const GA4_PATTERN = /^G-[A-Z0-9]{4,20}$/;
const PIXEL_PATTERN = /^\d{6,20}$/;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
    fbq?: ((...args: unknown[]) => void) & { queue?: unknown[]; loaded?: boolean; version?: string; push?: unknown; callMethod?: (...args: unknown[]) => void };
    _fbq?: unknown;
  }
}

export type AnalyticsIds = { ga4?: string; pixel?: string };

export function configuredIds(env: { VITE_GA4_ID?: string; VITE_META_PIXEL_ID?: string } = import.meta.env): AnalyticsIds {
  const ga4 = env.VITE_GA4_ID?.trim();
  const pixel = env.VITE_META_PIXEL_ID?.trim();
  // Only well-formed IDs are used, so a typo in the build env can never inject arbitrary script text.
  return {
    ga4: ga4 && GA4_PATTERN.test(ga4) ? ga4 : undefined,
    pixel: pixel && PIXEL_PATTERN.test(pixel) ? pixel : undefined,
  };
}

export function analyticsConfigured(ids: AnalyticsIds = configuredIds()): boolean {
  return Boolean(ids.ga4 || ids.pixel);
}

export function readConsent(): Consent | null {
  try {
    const value = window.localStorage.getItem(CONSENT_KEY);
    return value === "granted" || value === "denied" ? value : null;
  } catch {
    return null;
  }
}

export function writeConsent(value: Consent) {
  try {
    window.localStorage.setItem(CONSENT_KEY, value);
  } catch {
    /* storage blocked: the choice lasts for this page view only */
  }
}

let loaded = false;

function addScript(src: string) {
  const script = document.createElement("script");
  script.async = true;
  script.src = src;
  document.head.appendChild(script);
}

export function loadAnalytics(ids: AnalyticsIds = configuredIds()) {
  if (loaded || readConsent() !== "granted" || !analyticsConfigured(ids)) return;
  loaded = true;
  if (ids.ga4) {
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      // gtag.js reads the arguments object itself, as in Google's snippet.
      // eslint-disable-next-line prefer-rest-params
      window.dataLayer!.push(arguments);
    };
    window.gtag("js", new Date());
    window.gtag("config", ids.ga4, { send_page_view: false, anonymize_ip: true });
    addScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(ids.ga4)}`);
  }
  if (ids.pixel && !window.fbq) {
    const fbq = function (...args: unknown[]) {
      if (fbq.callMethod) fbq.callMethod(...args);
      else fbq.queue!.push(args);
    } as NonNullable<Window["fbq"]>;
    fbq.queue = [];
    fbq.loaded = true;
    fbq.version = "2.0";
    window.fbq = fbq;
    window._fbq = fbq;
    window.fbq("init", ids.pixel);
    addScript("https://connect.facebook.net/en_US/fbevents.js");
  }
}

/** Send one page view for the current hash route. */
export function trackPageView(route: string) {
  if (!loaded) return;
  const path = `/${route.replace(/^#\/?/, "")}`;
  window.gtag?.("event", "page_view", { page_path: path, page_location: window.location.href, page_title: document.title });
  window.fbq?.("track", "PageView");
}
