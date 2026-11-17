import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8765', ws: true, changeOrigin: false } } },
  build: {
    outDir: '../agentrader/web_assets', emptyOutDir: true,
    rolldownOptions: {
      output: {
        // Stable library chunks can be reused when application code changes.
        codeSplitting: {
          groups: [
            { name: 'react-runtime', test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: 'chart-engine', test: /[\\/]node_modules[\\/](lightweight-charts|fancy-canvas)[\\/]/ },
          ],
        },
      },
    },
  },
});
