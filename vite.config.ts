import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

const backendTarget = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

const apiProxy = {
  '/api': {
    target: backendTarget,
    changeOrigin: true,
  },
  '/health': {
    target: backendTarget,
    changeOrigin: true,
  },
};

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      port: 3000,
      proxy: apiProxy,
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    preview: {
      port: 3000,
      proxy: apiProxy,
    },
  };
});
