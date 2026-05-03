<template>
  <view class="skeleton-list">
    <view v-for="i in 5" :key="i" class="skeleton-card">
      <view class="skeleton-header">
        <view class="skeleton-strip" />
        <view class="skeleton-title-wrap">
          <view class="skeleton-title" />
          <view class="skeleton-title short" />
        </view>
      </view>
      <view class="skeleton-summary" />
      <view class="skeleton-footer">
        <view class="skeleton-badge" />
        <view class="skeleton-badge" />
        <view class="skeleton-stat" />
      </view>
    </view>
  </view>
</template>

<style scoped>
.skeleton-list {
  padding: 0 24rpx;
}

.skeleton-card {
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
  overflow: hidden;
}

.skeleton-header {
  display: flex;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.skeleton-strip {
  width: 6rpx;
  height: 64rpx;
  background: #e5e6eb;
  border-radius: 4rpx;
  flex-shrink: 0;
}

.skeleton-title-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  justify-content: center;
}

.skeleton-title {
  height: 32rpx;
  background: #e5e6eb;
  border-radius: 6rpx;
  width: 85%;
}

.skeleton-title.short {
  width: 60%;
}

.skeleton-summary {
  height: 28rpx;
  background: #e5e6eb;
  border-radius: 6rpx;
  margin-bottom: 20rpx;
  width: 100%;
}

.skeleton-footer {
  display: flex;
  gap: 12rpx;
  align-items: center;
}

.skeleton-badge {
  width: 80rpx;
  height: 28rpx;
  background: #e5e6eb;
  border-radius: 6rpx;
}

.skeleton-stat {
  margin-left: auto;
  width: 100rpx;
  height: 28rpx;
  background: #e5e6eb;
  border-radius: 6rpx;
}

/* Shimmer animation */
.skeleton-strip,
.skeleton-title,
.skeleton-summary,
.skeleton-badge,
.skeleton-stat {
  position: relative;
  overflow: hidden;
}

.skeleton-strip::after,
.skeleton-title::after,
.skeleton-summary::after,
.skeleton-badge::after,
.skeleton-stat::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.5) 50%, transparent 100%);
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
</style>
