<script setup lang="ts">
defineProps<{
  label: string
  tone?: 'success' | 'warning' | 'muted' | 'error'
}>()
</script>

<template>
  <span class="status-badge" :class="tone || 'muted'">{{ label }}</span>
</template>

<style scoped>
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.success {
  background: #f0f9ff;
  color: #67c23a;
}

.status-badge.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-badge.error {
  background: #fef0f0;
  color: #f56c6c;
}

.status-badge.muted {
  background: #f4f4f5;
  color: #909399;
}
</style>
