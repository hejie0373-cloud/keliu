import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  root: __dirname,
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 1200,
    rolldownOptions: {
      onLog(level, log, handler) {
        const file = log.loc?.file || log.id || ''
        if (log.code === 'INVALID_ANNOTATION' && file.includes('node_modules/@vueuse/core')) {
          return
        }
        handler(level, log)
      },
      output: {
        manualChunks(id) {
          const normalizedId = id.replaceAll('\\', '/')
          if (!normalizedId.includes('/node_modules/')) return
          if (normalizedId.includes('/node_modules/echarts/') || normalizedId.includes('/node_modules/zrender/')) {
            return 'echarts'
          }
          if (normalizedId.includes('/node_modules/element-plus/') || normalizedId.includes('/node_modules/@element-plus/')) {
            return 'element-plus'
          }
          if (
            normalizedId.includes('/node_modules/vue') ||
            normalizedId.includes('/node_modules/@vue/') ||
            normalizedId.includes('/node_modules/vue-router/') ||
            normalizedId.includes('/node_modules/pinia/')
          ) {
            return 'vue-vendor'
          }
          if (
            normalizedId.includes('/node_modules/gsap/') ||
            normalizedId.includes('/node_modules/qrcode/') ||
            normalizedId.includes('/node_modules/three/')
          ) {
            return 'visual-vendor'
          }
          return 'vendor'
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8009',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://127.0.0.1:8009',
        ws: true,
      },
    },
  },
})
