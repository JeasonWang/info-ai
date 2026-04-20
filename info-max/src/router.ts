import { createRouter, createWebHistory, type RouteLocationNormalized, type RouteRecordRaw, type RouterScrollBehavior } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('./views/HomeView.vue'),
  },
  {
    path: '/info/:id',
    name: 'detail',
    component: () => import('./views/InfoDetailView.vue'),
    props: true,
  },
  {
    path: '/events/:id',
    name: 'event-detail',
    component: () => import('./views/EventDetailView.vue'),
    props: true,
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('./views/SettingsView.vue'),
  },
]

export const appScrollBehavior: RouterScrollBehavior = (
  _to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  savedPosition,
) => {
  // 返回上一页时优先恢复浏览器记住的位置，避免用户重新回到列表顶部。
  if (savedPosition) {
    return savedPosition
  }
  return { top: 0 }
}

export function createAppRouter() {
  return createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior: appScrollBehavior,
  })
}
