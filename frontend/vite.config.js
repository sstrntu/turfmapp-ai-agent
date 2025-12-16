import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  root: './',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        home: resolve(__dirname, './public/home.html'),
        portal: resolve(__dirname, './public/portal.html'),
        profile: resolve(__dirname, './public/profile.html'),
        settings: resolve(__dirname, './public/settings.html'),
        admin: resolve(__dirname, './public/admin.html'),
        'auth-callback': resolve(__dirname, './public/auth-callback.html'),
        'google-callback': resolve(__dirname, './public/google-callback.html')
      },
      output: {
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js'
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./setupTests.js'],
    globals: true,
    include: ['src/**/*.test.{js,jsx,ts,tsx}', 'tests/**/*.test.{js,jsx,ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      reportsDirectory: './coverage'
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3005,
    open: '/public/home.html',
    fs: {
      allow: ['..']
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
