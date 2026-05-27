import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

const versionFile = path.resolve(__dirname, '../VERSION.txt')

export default defineConfig({
  plugins: [
    vue(),
    // Exposes VERSION.txt as a virtual module.
    // In production: version string is inlined at build time.
    // In development: fs.watch invalidates the module and triggers HMR
    //   whenever VERSION.txt changes on disk — no server restart needed.
    {
      name: 'virtual-version',
      resolveId: (id) => id === 'virtual:app-version' ? '\0virtual:app-version' : undefined,
      load(id) {
        if (id !== '\0virtual:app-version') return
        const v = fs.readFileSync(versionFile, 'utf-8').trim()
        return `export const version = ${JSON.stringify(v)}`
      },
      configureServer(server) {
        fs.watch(versionFile, () => {
          const mod = server.moduleGraph.getModuleById('\0virtual:app-version')
          if (mod) server.moduleGraph.invalidateModule(mod)
          server.hot.send({ type: 'full-reload' })
        })
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // /api/* in dev → http://localhost:8000/*
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
