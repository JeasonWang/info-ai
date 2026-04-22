import { describe, expect, it } from 'vitest'
import { createAppRouter } from '@/router'

describe('router scroll behavior', () => {
  it('does not expose admin configuration routes in the user app', () => {
    const routeNames = createAppRouter()
      .getRoutes()
      .map((route) => route.name)

    expect(routeNames).not.toContain('settings')
  })

  it('restores saved position when navigating back', async () => {
    const router = createAppRouter()
    const scrollBehavior = router.options.scrollBehavior

    expect(scrollBehavior).toBeTypeOf('function')

    const result = await scrollBehavior?.(
      { fullPath: '/' } as never,
      { fullPath: '/events/1' } as never,
      { left: 0, top: 1280 },
    )

    expect(result).toEqual({ left: 0, top: 1280 })
  })

  it('scrolls to top for forward navigation', async () => {
    const router = createAppRouter()
    const scrollBehavior = router.options.scrollBehavior

    const result = await scrollBehavior?.(
      { fullPath: '/events/1' } as never,
      { fullPath: '/' } as never,
      null,
    )

    expect(result).toEqual({ top: 0 })
  })
})
