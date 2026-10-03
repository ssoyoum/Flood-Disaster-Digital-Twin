/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  /** GA4 measurement ID, e.g. G-XXXXXXX. Analytics stays off when unset. */
  readonly VITE_GA4_ID?: string;
  /** Meta Pixel ID (digits). The pixel stays off when unset. */
  readonly VITE_META_PIXEL_ID?: string;
  /** Search Console HTML-tag token, injected into index.html at build time. */
  readonly VITE_GSC_VERIFICATION?: string;
  /** Contact shown on the privacy page. */
  readonly VITE_PRIVACY_CONTACT?: string;
}
