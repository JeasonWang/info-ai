import { createApp } from 'vue'
import App from '@/App.vue'
import { createAdminRouter } from '@/router'
import '@/styles/base.css'

createApp(App).use(createAdminRouter()).mount('#app')
