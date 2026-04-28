import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 4173,
    host: '0.0.0.0',
    proxy: {
      '/generate': 'http://localhost:5000',
      '/memory': 'http://localhost:5000'
    }
  }
});
