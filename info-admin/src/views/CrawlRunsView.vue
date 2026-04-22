<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { getCrawlRuns, getCrawlTasks } from '@/services/adminApi'
import type { CrawlRunSummary, CrawlTask } from '@/types/admin'

const runs = ref<CrawlRunSummary[]>([])
const tasks = ref<CrawlTask[]>([])

onMounted(async () => {
  const [runItems, taskItems] = await Promise.all([getCrawlRuns(20), getCrawlTasks()])
  runs.value = runItems
  tasks.value = taskItems
})
</script>

<template>
  <section class="panel-grid">
    <DataPanel title="采集运行日志" :status="`${runs.length} 条`">
      <ul v-if="runs.length" class="data-list">
        <li v-for="item in runs" :key="`${item.channel_code}-${item.started_at}`">
          <strong>{{ item.channel_code }} · {{ item.started_at }}</strong>
          <span>入库 {{ item.saved_count }} / 清洗 {{ item.cleaned_count }} / 详情失败 {{ item.detail_failed_count }}</span>
        </li>
      </ul>
      <EmptyState v-else title="暂无运行日志" description="等待调度器写入 crawl_run_log。" />
    </DataPanel>

    <DataPanel title="采集任务" :status="`${tasks.length} 个`">
      <ul v-if="tasks.length" class="data-list">
        <li v-for="item in tasks" :key="item.task_code">
          <strong>{{ item.task_name }}</strong>
          <span>{{ item.channel_name }} · {{ item.schedule_value }}</span>
          <StatusBadge :label="item.status" :tone="item.status === 'active' ? 'success' : 'muted'" />
        </li>
      </ul>
      <EmptyState v-else title="暂无采集任务" description="启动调度器后会同步渠道任务。" />
    </DataPanel>
  </section>
</template>
