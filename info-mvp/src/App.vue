<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { getCurrentUser } from '@/services/api'
import { useUserStore } from '@/stores/user'

onLaunch(() => {
  const store = useUserStore()
  if (store.token) {
    getCurrentUser()
      .then((user) => store.setUser(user))
      .catch(() => store.clearAuth())
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
  background-color: #f3ece1;
  color: #1f2633;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  box-sizing: border-box;

  /* Brand */
  --brand-primary: #f05a3d;
  --brand-accent: #f05a3d;
  --brand-accent-light: rgba(240, 90, 61, 0.1);
  --brand-soft: #fff2ea;
  --brand-warm-bg: #f3ece1;

  /* Data highlights */
  --heat-gradient-start: #f6a23a;
  --heat-gradient-end: #f04f3a;
  --freshness-color: #0f9f78;

  /* Surfaces */
  --bg-color: #f3ece1;
  --card-bg: #ffffff;
  --surface-elevated: #fffaf5;

  /* Text */
  --text-primary: #1f2633;
  --text-secondary: #526070;
  --text-muted: #8b7568;
  --text-inverse: #ffffff;

  /* Borders */
  --border-color: #eadfd5;
  --divider: #f1e7dd;

  /* Radius */
  --radius-sm: 8rpx;
  --radius-md: 16rpx;
  --radius-lg: 24rpx;
  --radius-pill: 9999rpx;

  /* Shadows */
  --shadow-sm: 0 8rpx 24rpx rgba(106, 70, 43, 0.08);
  --shadow-md: 0 12rpx 36rpx rgba(106, 70, 43, 0.1);
  --shadow-lg: 0 16rpx 44rpx rgba(106, 70, 43, 0.14);

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

  /* Category colors (semantic) */
  --cat-blue: #f05a3d;
  --cat-purple: #b85c38;
  --cat-teal: #0f9f78;
  --cat-orange: #f6a23a;
  --cat-rose: #ef476f;
  --cat-tech: #4A90D9;
  --cat-finance: #F5A623;
  --cat-sport: #34C759;
  --cat-society: #D0021B;
  --cat-ent: #BD10E0;
  --cat-global: #50E3C2;

  /* Evolution stage colors */
  --stage-emerging: #34C759;
  --stage-spreading: #F5A623;
  --stage-confirmed: #4A90D9;
  --stage-reversal: #D0021B;
  --stage-cooling: #8b7568;

  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-base: 0.25s ease;
  --transition-slow: 0.4s ease;
}

/* #ifdef H5 */
html,
body,
#app,
uni-page-body,
uni-page-wrapper {
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  box-sizing: border-box;
}
/* #endif */
</style>
