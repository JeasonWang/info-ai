import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import { adminTokenStorage } from '@/stores/authStore'

describe('LoginView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('logs in administrator and stores token', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/login', name: 'login', component: LoginView },
        { path: '/dashboard', name: 'dashboard', component: { template: '<div />' } },
      ],
    })
    const push = vi.spyOn(router, 'push')
    await router.push('/login')
    await router.isReady()
    vi.stubGlobal('fetch', vi.fn(async () => {
      return new Response(JSON.stringify({
        code: 0,
        message: 'success',
        data: {
          token: 'admin-token',
          user: { id: 1, email: 'admin@info-daren.local', role: 'admin' },
        },
      }))
    }))

    const wrapper = mount(LoginView, {
      global: {
        plugins: [router],
      },
    })

    await wrapper.get('input[type="email"]').setValue('admin@info-daren.local')
    await wrapper.get('input[type="password"]').setValue('Admin123456')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(adminTokenStorage.get()).toBe('admin-token')
    expect(push).toHaveBeenCalledWith({ name: 'dashboard' })
  })
})
