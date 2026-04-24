<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import {
  archiveDuplicateTitles,
  archiveLowQualityInfos,
  getLowQualityInfos,
  getQualitySnapshots,
  refreshQuality,
  retryLowQualityDetails,
} from '@/services/adminApi'
import type { LowQualityInfo, QualitySnapshot } from '@/types/admin'

const snapshots = ref<QualitySnapshot[]>([])
const lowQualityInfos = ref<LowQualityInfo[]>([])
const actionMessage = ref('')
const isRunning = ref(false)

async function loadData() {
  const [snapshotItems, lowQualityItems] = await Promise.all([getQualitySnapshots(20), getLowQualityInfos(20)])
  snapshots.value = snapshotItems
  lowQualityInfos.value = lowQualityItems
}

async function runAction(action: () => Promise<{ message: string }>) {
  isRunning.value = true
  actionMessage.value = '正在执行，请稍候...'
  try {
    const result = await action()
    actionMessage.value = result.message || '操作已提交'
    await loadData()
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '操作失败'
  } finally {
    isRunning.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="panel-grid">
    <DataPanel title="质量治理操作" status="人工治理">
      <div class="action-strip">
        <button type="button" :disabled="isRunning" @click="runAction(refreshQuality)">刷新质量</button>
        <button type="button" :disabled="isRunning" @click="runAction(() => retryLowQualityDetails(20))">重抓低完整详情</button>
        <button type="button" :disabled="isRunning" @click="runAction(archiveLowQualityInfos)">归档低质量</button>
        <button type="button" :disabled="isRunning" @click="runAction(archiveDuplicateTitles)">归档重复标题</button>
      </div>
      <p class="action-message">{{ actionMessage || '建议先刷新质量，再重抓低完整详情；仍明显低质或重复的数据再归档。治理动作会触发事件流更新。' }}</p>
    </DataPanel>

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
