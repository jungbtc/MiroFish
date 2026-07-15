import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const v2ApiKey = process.env.V2_API_KEY || rootEnv.V2_API_KEY || ''

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@locales': path.resolve(__dirname, '../locales')
      }
    },
    server: {
      host: process.env.VITE_HOST || rootEnv.VITE_HOST || '127.0.0.1',
      port: 3000,
      open: true,
      proxy: {
        '/api/v2': {
          target: 'http://localhost:5001',
          changeOrigin: true,
          secure: false,
          headers: v2ApiKey ? { 'X-MiroFish-Key': v2ApiKey } : {}
        },
        '/api': {
          target: 'http://localhost:5001',
          changeOrigin: true,
          secure: false
        }
      }
    }
  }
})
