<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import PageTabs from '@/components/PageTabs.vue'
import PaginationControl from '@/components/PaginationControl.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { getChannelHealth, getCrawlRuns, getCrawlTasks, rebuildEvents, triggerCrawlTask } from '@/services/adminApi'
import type { ChannelHealth, CrawlRunSummary, CrawlTask } from '@/types/admin'

const route = useRoute()
const runs = ref<CrawlRunSummary[]>([])
const tasks = ref<CrawlTask[]>([])
const healthItems = ref<ChannelHealth[]>([])
const actionMessage = ref('')
const isRunning = ref(false)
const healthPage = ref(1)
const runsPage = ref(1)
const tasksPage = ref(1)
const actionPage = ref(1)
const pageSize = 8

const section = computed(() => String(route.meta.section || 'health'))
const tabs = [
  { to: '/crawl-runs/health', label: '渠道健康', description: '完整率、成功率、风险' },
  { to: '/crawl-runs/runs', label: '运行日志', description: '最近采集结果' },
  { to: '/crawl-runs/tasks', label: '任务配置', description: '调度间隔与状态' },
  { to: '/crawl-runs/actions', label: '手动采集', description: '补采和重建事件' },
]
const pagedHealthItems = computed(() => pageSlice(healthItems.value, healthPage.value))
const pagedRuns = computed(() => pageSlice(runs.value, runsPage.value))
const pagedTasks = computed(() => pageSlice(tasks.value, tasksPage.value))
const pagedActionTasks = computed(() => pageSlice(tasks.value, actionPage.value))

async function loadData() {
  const [runItems, taskItems, channelHealthItems] = await Promise.all([getCrawlRuns(50), getCrawlTasks(), getChannelHealth()])
  runs.value = runItems
  tasks.value = taskItems
  healthItems.value = channelHealthItems
}

function pageSlice<T>(items: T[], page: number) {
  const start = (page - 1) * pageSize
  return items.slice(start, start + pageSize)
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

function healthTone(level: ChannelHealth['health_level']) {
  if (level === 'healthy') {
    return 'success'
  }
  if (level === 'warning') {
    return 'warning'
  }
  return 'muted'
}

function healthLabel(level: ChannelHealth['health_level']) {
  return {
    healthy: '健康',
    warning: '关注',
    risk: '风险',
  }[level]
}

function freshnessText(item: ChannelHealth) {
  const latestInfo = item.latest_info_at || '暂无资讯'
  const latestEvent = item.latest_event_at || '暂无事件'
  return `资讯 ${latestInfo} · 事件 ${latestEvent}`
}

function qualityText(item: ChannelHealth) {
  return `内容均长 ${item.average_content_length || 0} · 低完整 ${item.incomplete_info_count || 0}/${item.info_count || 0}`
}

function issueText(item: ChannelHealth) {
  if (item.top_failure_reasons?.length) {
    return `失败原因：${item.top_failure_reasons.join('、')}`
  }
  return item.last_issue || `最近运行 ${item.last_run_at || '暂无记录'}`
}
</script>

<template>
  <section class="page-stack">
    <PageTabs :items="tabs" />

    <DataPanel v-if="section === 'actions'" title="采集操作栏" status="人工触发">
      <div class="action-strip">
        <button
          v-for="item in pagedActionTasks"
          :key="item.task_code"
          type="button"
          :disabled="isRunning"
          @click="runAction(() => triggerCrawlTask(item.channel_code))"
        >
          立即采集 {{ item.channel_name }}
        </button>
        <button type="button" :disabled="isRunning" @click="runAction(rebuildEvents)">重建事件</button>
      </div>
      <PaginationControl v-model:page="actionPage" :page-size="pageSize" :total="tasks.length" />
      <p class="action-message">{{ actionMessage || '用于手动补采重点渠道，或在数据治理后重新生成事件流。' }}</p>
    </DataPanel>

    <DataPanel v-if="section === 'health'" title="渠道健康表" :status="`${healthItems.length} 个渠道`">
      <ul v-if="pagedHealthItems.length" class="data-list data-list--health">
        <li v-for="item in pagedHealthItems" :key="item.channel_code">
          <strong>{{ item.channel_name }}</strong>
          <span>健康 {{ item.health_score }} · 成功率 {{ item.success_rate }}% · 详情完整 {{ item.detail_complete_rate }}%</span>
          <span>{{ freshnessText(item) }}</span>
          <span>{{ qualityText(item) }} · 活跃事件 {{ item.active_event_count || 0 }}</span>
          <StatusBadge :label="healthLabel(item.health_level)" :tone="healthTone(item.health_level)" />
          <small>{{ issueText(item) }}</small>
        </li>
      </ul>
      <PaginationControl v-model:page="healthPage" :page-size="pageSize" :total="healthItems.length" />
      <EmptyState v-if="!pagedHealthItems.length" title="暂无渠道健康数据" description="采集任务运行后会自动计算成功率、完整率和风险状态。" />
    </DataPanel>

    <DataPanel v-if="section === 'runs'" title="采集运行日志" :status="`${runs.length} 条`">
      <ul v-if="pagedRuns.length" class="data-list">
        <li v-for="item in pagedRuns" :key="`${item.channel_code}-${item.started_at}`">
          <strong>{{ item.channel_code }} · {{ item.started_at }}</strong>
          <span>入库 {{ item.saved_count }} / 清洗 {{ item.cleaned_count }} / 详情失败 {{ item.detail_failed_count }}</span>
        </li>
      </ul>
      <PaginationControl v-model:page="runsPage" :page-size="pageSize" :total="runs.length" />
      <EmptyState v-if="!pagedRuns.length" title="暂无运行日志" description="等待调度器写入 crawl_run_log。" />
    </DataPanel>

    <DataPanel v-if="section === 'tasks'" title="采集任务配置" :status="`${tasks.length} 个`">
      <ul v-if="pagedTasks.length" class="data-list">
        <li v-for="item in pagedTasks" :key="item.task_code">
          <strong>{{ item.task_name }}</strong>
          <span>{{ item.channel_name }} · {{ item.schedule_value }}</span>
          <StatusBadge :label="item.status" :tone="item.status === 'active' ? 'success' : 'muted'" />
        </li>
      </ul>
      <PaginationControl v-model:page="tasksPage" :page-size="pageSize" :total="tasks.length" />
      <EmptyState v-if="!pagedTasks.length" title="暂无采集任务" description="启动调度器后会同步渠道任务。" />
    </DataPanel>
  </section>
</template>
