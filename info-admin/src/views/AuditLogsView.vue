<script setup lang="ts">
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
</script>

<template>
  <DataPanel title="审计日志" status="待接入">
    <EmptyState title="审计日志接口待接入" description="info-serve 已写入管理操作审计，下一步补充只读查询 API 和页面展示。" />
  </DataPanel>
</template>
