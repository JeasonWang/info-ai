import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { requireAdminAuth } from '@/router/guards'

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: '/dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/crawl-runs',
        name: 'crawl-runs',
        component: () => import('@/views/CrawlRunsView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/data-quality',
        name: 'data-quality',
        component: () => import('@/views/DataQualityView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/categories',
        name: 'categories',
        component: () => import('@/views/CategoriesView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/channels',
        name: 'channels',
        component: () => import('@/views/ChannelsView.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/audit-logs',
        name: 'audit-logs',
        component: () => import('@/views/AuditLogsView.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },
]

export function createAdminRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes,
  })
  router.beforeEach(requireAdminAuth)
  return router
}
