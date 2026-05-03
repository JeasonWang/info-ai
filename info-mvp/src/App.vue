<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { useUserStore } from '@/stores/user'

onLaunch(() => {
  const store = useUserStore()
  if (store.token) {
    uni.request({
      url: `${import.meta.env.VITE_API_BASE_URL || '/api'}/v1/me`,
      header: { Authorization: `Bearer ${store.token}` },
      success: (res) => {
        if (res.statusCode !== 200) {
          store.clearAuth()
        }
      },
      fail: () => {
        store.clearAuth()
      },
    })
  }
})
</script>

<template>
  <view>
    <slot />
  </view>
</template>

<style>
@import '@dcloudio/uni-ui/lib/uni-icons/uniicons.css';

page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background-color: #f7f8fa;
  color: #1d2129;

  /* Brand */
  --brand-primary: #2563eb;
  --brand-accent: #2563eb;
  --brand-accent-light: rgba(37, 99, 235, 0.08);

  /* Data highlights */
  --heat-gradient-start: #f59e0b;
  --heat-gradient-end: #ef4444;
  --freshness-color: #10b981;

  /* Surfaces */
  --bg-color: #f7f8fa;
  --card-bg: #ffffff;
  --surface-elevated: #ffffff;

  /* Text */
  --text-primary: #1d2129;
  --text-secondary: #4e5969;
  --text-muted: #86909c;
  --text-inverse: #ffffff;

  /* Borders */
  --border-color: #e5e6eb;
  --divider: #f2f3f5;

  /* Radius */
  --radius-sm: 8rpx;
  --radius-md: 16rpx;
  --radius-lg: 24rpx;
  --radius-pill: 9999rpx;

  /* Shadows */
  --shadow-sm: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8rpx 32rpx rgba(0, 0, 0, 0.08);

  /* Spacing */
  --space-xs: 8rpx;
  --space-sm: 16rpx;
  --space-md: 24rpx;
  --space-lg: 32rpx;
  --space-xl: 48rpx;

  /* Typography scale */
  --text-xs: 22rpx;
  --text-sm: 24rpx;
  --text-base: 28rpx;
  --text-lg: 32rpx;
  --text-xl: 36rpx;
  --text-2xl: 44rpx;

  /* Category accent colors (cycled for strips) */
  --cat-blue: #2563eb;
  --cat-purple: #7c3aed;
  --cat-teal: #0d9488;
  --cat-orange: #ea580c;
  --cat-rose: #e11d48;

  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-base: 0.25s ease;
  --transition-slow: 0.4s ease;
}
</style>
