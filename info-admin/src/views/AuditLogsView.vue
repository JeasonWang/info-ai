<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import { getAuditLogs } from '@/services/adminApi'
import type { AuditLog } from '@/types/admin'

const logs = ref<AuditLog[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    logs.value = await getAuditLogs(50)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <DataPanel title="审计日志" :status="loading ? '加载中' : `${logs.length} 条`">
    <ul v-if="logs.length" class="data-list">
      <li v-for="item in logs" :key="item.id">
        <strong>{{ item.admin_email }} · {{ item.action }}</strong>
        <span>{{ item.created_at }} · IP {{ item.ip_address || '未知' }}</span>
        <small v-if="item.target_type || item.target_id">{{ item.target_type || '对象' }} {{ item.target_id }}</small>
      </li>
    </ul>
    <EmptyState v-else title="暂无审计日志" description="管理员访问和配置操作会自动写入审计记录。" />
  </DataPanel>
</template>
