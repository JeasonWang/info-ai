<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import PageTabs from '@/components/PageTabs.vue'
import PaginationControl from '@/components/PaginationControl.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { getChannelHealth, getCrawlRuns, getCrawlTasks, rebuildEvents, triggerCrawlTask, updateCrawlTaskConfig } from '@/services/adminApi'
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

const editIntervals = ref<Record<string, number>>({})
const editActive = ref<Record<string, number>>({})
const savingTask = ref<string | null>(null)
const taskMessage = ref('')

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
  for (const t of taskItems) {
    if (!(t.channel_code in editIntervals.value)) {
      editIntervals.value[t.channel_code] = t.effective_interval_minutes
    }
    if (!(t.channel_code in editActive.value)) {
      editActive.value[t.channel_code] = t.is_active
    }
  }
}

async function saveTaskConfig(channelCode: string) {
  const interval = editIntervals.value[channelCode]
  const active = editActive.value[channelCode]
  if (!interval || interval < 1) {
    taskMessage.value = '间隔分钟数必须大于 0'
    return
  }
  savingTask.value = channelCode
  taskMessage.value = ''
  try {
    await updateCrawlTaskConfig(channelCode, { effective_interval_minutes: interval, is_active: active })
    taskMessage.value = `${channelCode} 配置已保存，调度器将在下个周期生效`
    await loadData()
  } catch (e: any) {
    taskMessage.value = e?.message || '保存失败'
  } finally {
    savingTask.value = null
  }
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
      <div class="action-groups">
        <div class="action-group">
          <h4 class="action-group-title">单渠道采集</h4>
          <p class="action-group-desc">立即触发指定渠道的一次完整采集（列表抓取 + 详情入库），不影响调度周期</p>
          <div class="action-strip">
            <button
              v-for="item in pagedActionTasks"
              :key="item.task_code"
              type="button"
              :disabled="isRunning"
              @click="runAction(() => triggerCrawlTask(item.channel_code))"
            >
              {{ item.channel_name }}
            </button>
          </div>
          <PaginationControl v-model:page="actionPage" :page-size="pageSize" :total="tasks.length" />
        </div>
        <div class="action-group">
          <h4 class="action-group-title">全局操作</h4>
          <p class="action-group-desc">重新扫描所有原始内容，按时间、实体、关键词重新聚合生成事件</p>
          <div class="action-strip">
            <button type="button" :disabled="isRunning" @click="runAction(rebuildEvents)">重建事件</button>
          </div>
        </div>
      </div>
      <p class="action-message">{{ actionMessage }}</p>
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
        <li v-for="item in pagedTasks" :key="item.task_code" class="task-row">
          <div class="task-info">
            <strong>{{ item.task_name }}</strong>
            <StatusBadge :label="item.status === 'active' ? '运行中' : '已暂停'" :tone="item.status === 'active' ? 'success' : 'muted'" />
          </div>
          <div class="task-detail">
            <span>{{ item.channel_name }} · 当前 {{ item.schedule_value }}</span>
            <span class="task-time">上次 {{ item.last_run_at || '无' }} · 下次 {{ item.next_run_at || '待定' }}</span>
          </div>
          <div class="task-edit">
            <div class="task-config-row">
              <label class="task-config-label">间隔(分钟)</label>
              <input
                type="number"
                class="task-config-input"
                :value="editIntervals[item.channel_code]"
                min="1"
                max="1440"
                @input="editIntervals[item.channel_code] = Number(($event.target as HTMLInputElement).value)"
              />
            </div>
            <div class="task-config-row">
              <label class="task-config-label">状态</label>
              <select
                class="task-config-select"
                :value="editActive[item.channel_code]"
                @change="editActive[item.channel_code] = Number(($event.target as HTMLSelectElement).value)"
              >
                <option :value="1">启用</option>
                <option :value="0">停用</option>
              </select>
            </div>
            <button
              type="button"
              class="button"
              :disabled="savingTask === item.channel_code"
              @click="saveTaskConfig(item.channel_code)"
            >
              {{ savingTask === item.channel_code ? '保存中...' : '保存' }}
            </button>
          </div>
        </li>
      </ul>
      <p v-if="taskMessage" class="action-message">{{ taskMessage }}</p>
      <PaginationControl v-model:page="tasksPage" :page-size="pageSize" :total="tasks.length" />
      <EmptyState v-if="!pagedTasks.length" title="暂无采集任务" description="启动调度器后会同步渠道任务。" />
    </DataPanel>
  </section>
</template>
