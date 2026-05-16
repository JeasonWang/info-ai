<script setup lang="ts">
defineProps<{
  activeTab: string
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'tab-change', tab: string): void
  (e: 'ai-click'): void
}>()
</script>

<template>
  <view v-show="visible" class="dock-wrap">
    <view class="dock">
      <view
        class="dock-item"
        :class="{ active: activeTab === 'home' }"
        @click="emit('tab-change', 'home')"
      >
        <text class="dock-icon">&#x25C9;</text>
        <text class="dock-label">情报</text>
      </view>
      <view class="dock-ai" @click="emit('ai-click')">
        <view class="dock-ai-orb">
          <text class="ai-icon">&#x2726;</text>
        </view>
        <text class="dock-label ai-label">智询</text>
      </view>
      <view
        class="dock-item"
        :class="{ active: activeTab === 'profile' }"
        @click="emit('tab-change', 'profile')"
      >
        <text class="dock-icon">&#x25CE;</text>
        <text class="dock-label">我的</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.dock-wrap {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 200;
  display: flex;
  justify-content: center;
  padding: 0 0 calc(16rpx + env(safe-area-inset-bottom));
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.35s;
}

.dock-wrap[hidden] {
  transform: translateY(calc(100% + 40rpx));
  opacity: 0;
}

.dock {
  display: flex;
  align-items: flex-end;
  width: 72%;
  background: rgba(255, 250, 245, 0.82);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-radius: 40rpx;
  padding: 8rpx 0;
  box-shadow: 0 4rpx 32rpx rgba(106, 70, 43, 0.12), 0 0 0 1rpx rgba(234, 223, 213, 0.5);
}

.dock-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  padding: 12rpx 0;
  border-radius: 28rpx;
  transition: all 0.25s;
  position: relative;
}

.dock-icon {
  font-size: 40rpx;
  line-height: 1;
  color: var(--text-muted);
  transition: color 0.25s;
}

.dock-label {
  font-size: 18rpx;
  font-weight: 500;
  color: var(--text-muted);
  transition: color 0.25s;
}

.dock-item.active .dock-icon {
  color: var(--brand-primary);
}

.dock-item.active .dock-label {
  color: var(--brand-primary);
  font-weight: 600;
}

.dock-item.active::before {
  content: '';
  position: absolute;
  inset: 2rpx;
  border-radius: 26rpx;
  background: var(--brand-accent-light);
}

.dock-ai {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: -24rpx;
  position: relative;
  z-index: 1;
}

.dock-ai-orb {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #f05a3d 0%, #ff7a45 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 20rpx rgba(240, 90, 61, 0.35);
  transition: transform 0.3s;
}

.dock-ai-orb:active {
  transform: scale(0.93);
}

.ai-icon {
  font-size: 40rpx;
  line-height: 1;
  color: #fff;
}

.ai-label {
  color: var(--brand-primary);
  margin-top: 4rpx;
}

@keyframes orb-glow {
  0%, 100% { box-shadow: 0 4rpx 20rpx rgba(240, 90, 61, 0.35); }
  50% { box-shadow: 0 4rpx 28rpx rgba(240, 90, 61, 0.45), 0 0 0 6rpx rgba(240, 90, 61, 0.06); }
}

.dock-ai-orb {
  animation: orb-glow 3s ease-in-out infinite;
}
</style>
