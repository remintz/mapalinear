import { defaultCache } from '@serwist/next/worker';
import type { PrecacheEntry, SerwistGlobalConfig } from 'serwist';
import {
  Serwist,
  StaleWhileRevalidate,
  NetworkFirst,
  CacheFirst,
  ExpirationPlugin,
} from 'serwist';

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: WorkerGlobalScope & typeof globalThis;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    // HTML pages - NetworkFirst so they work offline after first visit
    {
      matcher: ({ request }) => request.mode === 'navigate',
      handler: new NetworkFirst({
        cacheName: 'pages-cache',
        plugins: [
          new ExpirationPlugin({
            maxEntries: 30,
            maxAgeSeconds: 7 * 24 * 60 * 60,
          }),
        ],
        networkTimeoutSeconds: 5,
      }),
    },
    // Next.js RSC data requests (client-side navigation)
    {
      matcher: ({ request }) =>
        request.headers.get('RSC') === '1' ||
        request.headers.get('Next-Router-State-Tree') !== null,
      handler: new NetworkFirst({
        cacheName: 'rsc-cache',
        plugins: [
          new ExpirationPlugin({
            maxEntries: 30,
            maxAgeSeconds: 24 * 60 * 60,
          }),
        ],
        networkTimeoutSeconds: 5,
      }),
    },
    // Auth session - cache so page loads offline
    {
      matcher: /\/api\/auth\/session$/,
      handler: new NetworkFirst({
        cacheName: 'auth-session',
        plugins: [
          new ExpirationPlugin({
            maxEntries: 1,
            maxAgeSeconds: 7 * 24 * 60 * 60,
          }),
        ],
        networkTimeoutSeconds: 3,
      }),
    },
    // API: maps list
    {
      matcher: /\/api\/maps\/?$/,
      handler: new StaleWhileRevalidate({
        cacheName: 'api-maps-list',
        plugins: [
          new ExpirationPlugin({
            maxEntries: 5,
            maxAgeSeconds: 24 * 60 * 60,
          }),
        ],
      }),
    },
    // API: individual map
    {
      matcher: /\/api\/maps\/[^/]+$/,
      handler: new NetworkFirst({
        cacheName: 'api-maps-detail',
        plugins: [
          new ExpirationPlugin({
            maxEntries: 30,
            maxAgeSeconds: 7 * 24 * 60 * 60,
          }),
        ],
        networkTimeoutSeconds: 5,
      }),
    },
    // Google Fonts stylesheets
    {
      matcher: /^https:\/\/fonts\.googleapis\.com\/.*/i,
      handler: new StaleWhileRevalidate({
        cacheName: 'google-fonts-stylesheets',
      }),
    },
    // Google Fonts webfont files
    {
      matcher: /^https:\/\/fonts\.gstatic\.com\/.*/i,
      handler: new CacheFirst({
        cacheName: 'google-fonts-webfonts',
        plugins: [
          new ExpirationPlugin({
            maxEntries: 30,
            maxAgeSeconds: 365 * 24 * 60 * 60,
          }),
        ],
      }),
    },
    // Default caching from serwist/next
    ...defaultCache,
  ],
});

serwist.addEventListeners();
