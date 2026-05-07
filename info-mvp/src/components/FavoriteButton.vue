<script setup lang="ts">
import { onMounted } from 'vue'
import { useFavorite } from '@/composables/useFavorite'

const props = defineProps<{
  eventId: number
}>()

const { isFavorited, loading, check, toggle } = useFavorite(props.eventId)

onMounted(() => {
  check()
})
</script>

<template>
  <view
    class="favorite-btn"
    :class="{ favorited: isFavorited, 'is-animating': loading }"
    @click="toggle"
  >
    <text class="favorite-icon">{{ isFavorited ? '&#xe618;' : '&#xe619;' }}</text>
    <text class="favorite-label">{{ isFavorited ? '已收藏' : '收藏' }}</text>
  </view>
</template>

<style scoped>
.favorite-btn {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 14rpx 28rpx;
  border-radius: var(--radius-pill);
  background: var(--divider);
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.favorite-btn:active {
  transform: scale(0.9);
}

.favorite-btn.favorited {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  animation: heart-pop 0.4s ease;
}

.favorite-btn.is-animating {
  opacity: 0.7;
}

.favorite-icon {
  font-family: 'uniicons';
  font-size: 26rpx;
  transition: transform var(--transition-fast);
}

.favorite-btn:active .favorite-icon {
  transform: scale(1.2);
}

.favorite-label {
  font-weight: 500;
}

@keyframes heart-pop {
  0% {
    transform: scale(1);
  }
  30% {
    transform: scale(1.15);
  }
  60% {
    transform: scale(0.95);
  }
  100% {
    transform: scale(1);
  }
}
</style>
