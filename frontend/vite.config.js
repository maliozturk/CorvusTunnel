import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  base: '/app/', // Match the FastAPI static mounting prefix
  build: {
    outDir: '../corvustunnel/static',
    emptyOutDir: false, // Keep manifest.json, sw.js, and icons
  }
})
