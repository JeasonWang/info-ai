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
        meta: { requiresAuth: true, title: '首页总览' },
      },
      {
        path: '/crawl-runs',
        redirect: '/crawl-runs/health',
      },
      {
        path: '/crawl-runs/health',
        name: 'crawl-runs-health',
        component: () => import('@/views/CrawlRunsView.vue'),
        meta: { requiresAuth: true, title: '渠道健康', section: 'health' },
      },
      {
        path: '/crawl-runs/runs',
        name: 'crawl-runs-history',
        component: () => import('@/views/CrawlRunsView.vue'),
        meta: { requiresAuth: true, title: '采集运行日志', section: 'runs' },
      },
      {
        path: '/crawl-runs/tasks',
        name: 'crawl-runs-tasks',
        component: () => import('@/views/CrawlRunsView.vue'),
        meta: { requiresAuth: true, title: '采集任务配置', section: 'tasks' },
      },
      {
        path: '/crawl-runs/actions',
        name: 'crawl-runs-actions',
        component: () => import('@/views/CrawlRunsView.vue'),
        meta: { requiresAuth: true, title: '手动采集', section: 'actions' },
      },
      {
        path: '/data-quality',
        redirect: '/data-quality/report',
      },
      {
        path: '/data-quality/report',
        name: 'data-quality-report',
        component: () => import('@/views/DataQualityView.vue'),
        meta: { requiresAuth: true, title: '渠道质量报告', section: 'report' },
      },
      {
        path: '/data-quality/snapshots',
        name: 'data-quality-snapshots',
        component: () => import('@/views/DataQualityView.vue'),
        meta: { requiresAuth: true, title: '质量快照', section: 'snapshots' },
      },
      {
        path: '/data-quality/low-quality',
        name: 'data-quality-low-quality',
        component: () => import('@/views/DataQualityView.vue'),
        meta: { requiresAuth: true, title: '低质量内容', section: 'low-quality' },
      },
      {
        path: '/data-quality/actions',
        name: 'data-quality-actions',
        component: () => import('@/views/DataQualityView.vue'),
        meta: { requiresAuth: true, title: '质量治理工具', section: 'actions' },
      },
      {
        path: '/detail-jobs',
        redirect: '/detail-jobs/overview',
      },
      {
        path: '/detail-jobs/overview',
        name: 'detail-jobs-overview',
        component: () => import('@/views/DetailJobsView.vue'),
        meta: { requiresAuth: true, title: '详情补偿总览', section: 'overview' },
      },
      {
        path: '/detail-jobs/pending',
        name: 'detail-jobs-pending',
        component: () => import('@/views/DetailJobsView.vue'),
        meta: { requiresAuth: true, title: '待处理详情任务', section: 'pending' },
      },
      {
        path: '/detail-jobs/failed',
        name: 'detail-jobs-failed',
        component: () => import('@/views/DetailJobsView.vue'),
        meta: { requiresAuth: true, title: '失败详情任务', section: 'failed' },
      },
      {
        path: '/categories',
        name: 'categories',
        component: () => import('@/views/CategoriesView.vue'),
        meta: { requiresAuth: true, title: '分类管理' },
      },
      {
        path: '/channels',
        name: 'channels',
        component: () => import('@/views/ChannelsView.vue'),
        meta: { requiresAuth: true, title: '渠道管理' },
      },
      {
        path: '/audit-logs',
        name: 'audit-logs',
        component: () => import('@/views/AuditLogsView.vue'),
        meta: { requiresAuth: true, title: '审计日志' },
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
