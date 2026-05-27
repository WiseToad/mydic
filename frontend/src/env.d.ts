/// <reference types="vite/client" />

declare module 'virtual:app-version' {
  /** Version string read from VERSION.txt — inlined at build time, HMR-enabled in dev. */
  export const version: string
}
