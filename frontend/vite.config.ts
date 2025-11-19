import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite' // Tailwind CSS Vite 필드 프로세스 자동 통합


// https://vite.dev/config/
export default defineConfig({
  plugins: [
  tailwindcss()
  ],
})
