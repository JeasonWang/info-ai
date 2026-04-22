<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import { getQualitySnapshots } from '@/services/adminApi'
import type { QualitySnapshot } from '@/types/admin'

const snapshots = ref<QualitySnapshot[]>([])

onMounted(async () => {
  snapshots.value = await getQualitySnapshots(20)
})
</script>

<template>
  <DataPanel title="数据质量快照" :status="`${snapshots.length} 条`">
    <ul v-if="snapshots.length" class="data-list">
      <li v-for="item in snapshots" :key="`${item.category_code}-${item.snapshot_at}`">
        <strong>{{ item.category_code }} · {{ item.total_count }} 条</strong>
        <span>重复 {{ item.duplicate_title_count }} / 缺正文 {{ item.empty_content_count }} / 缺实体 {{ item.missing_entity_count }}</span>
      </li>
    </ul>
    <EmptyState v-else title="暂无质量快照" description="质量任务写入后会展示质量变化。" />
  </DataPanel>
</template>
