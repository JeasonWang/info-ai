<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import { getLowQualityInfos, getQualitySnapshots } from '@/services/adminApi'
import type { LowQualityInfo, QualitySnapshot } from '@/types/admin'

const snapshots = ref<QualitySnapshot[]>([])
const lowQualityInfos = ref<LowQualityInfo[]>([])

onMounted(async () => {
  const [snapshotItems, lowQualityItems] = await Promise.all([getQualitySnapshots(20), getLowQualityInfos(20)])
  snapshots.value = snapshotItems
  lowQualityInfos.value = lowQualityItems
})
</script>

<template>
  <section class="panel-grid">
    <DataPanel title="数据质量快照" :status="`${snapshots.length} 条`">
      <ul v-if="snapshots.length" class="data-list">
        <li v-for="item in snapshots" :key="`${item.category_code}-${item.snapshot_at}`">
          <strong>{{ item.category_code }} · {{ item.total_count }} 条</strong>
          <span>重复 {{ item.duplicate_title_count }} / 缺正文 {{ item.empty_content_count }} / 缺实体 {{ item.missing_entity_count }}</span>
        </li>
      </ul>
      <EmptyState v-else title="暂无质量快照" description="质量任务写入后会展示质量变化。" />
    </DataPanel>

    <DataPanel title="低质量内容" :status="`${lowQualityInfos.length} 条`">
      <ul v-if="lowQualityInfos.length" class="data-list">
        <li v-for="item in lowQualityInfos" :key="item.id">
          <strong>{{ item.title }}</strong>
          <span>{{ item.issue_reason }} · 质量 {{ item.detail_score }} · 正文 {{ item.detail_content_length }} 字</span>
          <small>{{ item.category_name }} / {{ item.channel_name }} · {{ item.updated_at }}</small>
        </li>
      </ul>
      <EmptyState v-else title="暂无低质量内容" description="当前没有命中正文为空、详情评分偏低或关键实体缺失的内容。" />
    </DataPanel>
  </section>
</template>
