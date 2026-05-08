<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import PageTabs from '@/components/PageTabs.vue'
import PaginationControl from '@/components/PaginationControl.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import {
  batchCancelDetailJobs,
  batchRetryDetailJobs,
  cancelDetailJob,
  getDetailJob,
  getDetailJobReport,
  retryDetailJob,
} from '@/services/adminApi'
import type { DetailJobDetail, DetailJobReport, DetailJobSample } from '@/types/admin'

const route = useRoute()
const report = ref<DetailJobReport | null>(null)
const actionMessage = ref('')
const actingJobId = ref<number | null>(null)
const isBatchRunning = ref(false)
const selectedJob = ref<DetailJobDetail | null>(null)
const pendingPage = ref(1)
const failedPage = ref(1)
const pageSize = 8
const filters = ref({
  channelCode: '',
  failureReason: '',
})

const section = computed(() => String(route.meta.section || 'overview'))
const tabs = [
  { to: '/detail-jobs/overview', label: '补偿总览', description: '队列规模和失败分布' },
  { to: '/detail-jobs/pending', label: '待处理任务', description: '查看、取消积压任务' },
  { to: '/detail-jobs/failed', label: '失败任务', description: '定位失败并重试' },
]
const statusItems = computed(() => Object.entries(report.value?.status_counts || {}))
const channelItems = computed(() => Object.entries(report.value?.channel_counts || {}))
const strategyItems = computed(() => Object.entries(report.value?.strategy_counts || {}))
const failureReasonItems = computed(() => report.value?.top_failure_reasons || [])
const pagedPendingSamples = computed(() => pageSlice(report.value?.pending_samples || [], pendingPage.value))
const pagedFailedSamples = computed(() => pageSlice(report.value?.failed_samples || [], failedPage.value))

async function refreshData() {
  report.value = await getDetailJobReport({
    limit: 50,
    channelCode: filters.value.channelCode,
    failureReason: filters.value.failureReason,
  })
}

function pageSlice<T>(items: T[], page: number) {
  const start = (page - 1) * pageSize
  return items.slice(start, start + pageSize)
}

function statusTone(status: string) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'warning'
  return 'muted'
}

function sampleMeta(item: DetailJobSample) {
  return `${item.channel_code} · ${item.detail_fetch_status} · 策略 ${item.strategy_hint || 'auto'} · 分数 ${item.detail_score} · 尝试 ${item.attempt_count}/${item.max_attempts}`
}

async function runJobAction(item: DetailJobSample, action: 'retry' | 'cancel') {
  actingJobId.value = item.id
  actionMessage.value = ''
  try {
    const result = action === 'retry' ? await retryDetailJob(item.id) : await cancelDetailJob(item.id)
    actionMessage.value = result.message
    await refreshData()
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '详情补偿任务操作失败'
  } finally {
    actingJobId.value = null
  }
}

async function runBatchRetry() {
  if (!filters.value.channelCode && !filters.value.failureReason) {
    actionMessage.value = '请先选择渠道或失败原因，再执行批量重试。'
    return
  }
  isBatchRunning.value = true
  actionMessage.value = ''
  try {
    const result = await batchRetryDetailJobs({
      limit: 50,
      channelCode: filters.value.channelCode,
      failureReason: filters.value.failureReason,
    })
    actionMessage.value = result.message
    await refreshData()
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '详情补偿任务批量重试失败'
  } finally {
    isBatchRunning.value = false
  }
}

async function runBatchCancel() {
  if (!filters.value.channelCode && !filters.value.failureReason) {
    actionMessage.value = '请先选择渠道或失败原因，再执行批量取消。'
    return
  }
  isBatchRunning.value = true
  actionMessage.value = ''
  try {
    const result = await batchCancelDetailJobs({
      limit: 50,
      channelCode: filters.value.channelCode,
      failureReason: filters.value.failureReason,
    })
    actionMessage.value = result.message
    await refreshData()
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '详情补偿任务批量取消失败'
  } finally {
    isBatchRunning.value = false
  }
}

async function showJobDetail(item: DetailJobSample) {
  actingJobId.value = item.id
  try {
    selectedJob.value = await getDetailJob(item.id)
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '详情补偿任务详情查询失败'
  } finally {
    actingJobId.value = null
  }
}

function clearFilters() {
  filters.value.channelCode = ''
  filters.value.failureReason = ''
  refreshData()
}

onMounted(refreshData)
</script>

<template>
  <div class="page-stack">
    <PageTabs :items="tabs" />

    <DataPanel v-if="section === 'overview'" title="详情补偿队列" :status="report ? `${report.total} 个任务` : '加载中'">
      <div v-if="report" class="metric-grid metric-grid--compact">
        <div class="metric-card">
          <span>队列总量</span>
          <strong>{{ report.total }}</strong>
          <p>包含 pending、running、succeeded、failed 等状态。</p>
        </div>
        <div class="metric-card">
          <span>待处理</span>
          <strong>{{ report.status_counts.pending || 0 }}</strong>
          <p>按优先级和可执行时间进入补偿 worker。</p>
        </div>
        <div class="metric-card">
          <span>失败任务</span>
          <strong>{{ report.status_counts.failed || 0 }}</strong>
          <p>用于定位渠道解析失效、空正文和反爬问题。</p>
        </div>
      </div>
      <EmptyState v-else title="正在加载" description="详情补偿队列报告加载中。" />
    </DataPanel>

    <DataPanel v-if="section !== 'overview'" title="查询条件" :status="filters.channelCode || filters.failureReason ? '已筛选' : '全部任务'">
      <div class="inline-form detail-job-filter">
        <label>
          <span>渠道</span>
          <select v-model="filters.channelCode">
            <option value="">全部渠道</option>
            <option v-for="[channel] in channelItems" :key="channel" :value="channel">{{ channel }}</option>
          </select>
        </label>
        <label>
          <span>失败原因</span>
          <select v-model="filters.failureReason">
            <option value="">全部原因</option>
            <option v-for="item in failureReasonItems" :key="item.reason" :value="item.reason">
              {{ item.reason }}
            </option>
          </select>
        </label>
        <button type="button" @click="refreshData">应用筛选</button>
        <button type="button" class="button--ghost" @click="clearFilters">清空</button>
        <button type="button" :disabled="isBatchRunning" @click="runBatchRetry">批量重试</button>
        <button type="button" class="button--ghost" :disabled="isBatchRunning" @click="runBatchCancel">批量取消</button>
      </div>
      <p class="action-message">{{ actionMessage || '批量操作需要至少选择一个筛选条件，避免误操作全量队列。' }}</p>
    </DataPanel>

    <DataPanel v-if="selectedJob" title="任务详情" :status="selectedJob.status">
      <div class="detail-job-detail">
        <div>
          <strong>{{ selectedJob.title }}</strong>
          <span>{{ selectedJob.channel_code }} · {{ selectedJob.detail_fetch_status }} · 分数 {{ selectedJob.detail_score }}</span>
          <small>{{ selectedJob.last_failure_reason || '暂无失败原因' }} · {{ selectedJob.updated_at }}</small>
        </div>
        <a v-if="selectedJob.source_url" :href="selectedJob.source_url" target="_blank" rel="noreferrer">查看原文</a>
        <pre>{{ selectedJob.content || '暂无正文内容' }}</pre>
      </div>
    </DataPanel>

    <DataPanel v-if="section === 'overview'" title="队列分布" status="按状态 / 渠道">
      <div v-if="report" class="panel-grid panel-grid--split">
        <section>
          <h3>状态分布</h3>
          <ul class="data-list">
            <li v-for="[status, count] in statusItems" :key="status">
              <strong>{{ status }}</strong>
              <span>{{ count }} 个任务</span>
              <StatusBadge :label="status" :tone="statusTone(status)" />
            </li>
          </ul>
        </section>
        <section>
          <h3>渠道分布</h3>
          <ul class="data-list">
            <li v-for="[channel, count] in channelItems" :key="channel">
              <strong>{{ channel }}</strong>
              <span>{{ count }} 个任务</span>
              <StatusBadge label="channel" tone="muted" />
            </li>
          </ul>
        </section>
      </div>
    </DataPanel>

    <DataPanel v-if="section === 'overview'" title="失败原因" :status="`${report?.top_failure_reasons.length || 0} 类`">
      <ul v-if="report?.top_failure_reasons.length" class="data-list">
        <li v-for="item in report.top_failure_reasons" :key="item.reason">
          <strong>{{ item.reason }}</strong>
          <span>{{ item.count }} 次</span>
          <StatusBadge label="reason" tone="warning" />
        </li>
      </ul>
      <EmptyState v-else title="暂无失败原因" description="失败样本出现后会在这里聚合。" />
    </DataPanel>

    <DataPanel v-if="section === 'overview'" title="补偿策略趋势" :status="`${strategyItems.length} 类`">
      <ul v-if="strategyItems.length" class="data-list">
        <li v-for="[strategy, count] in strategyItems" :key="strategy">
          <strong>{{ strategy }}</strong>
          <span>{{ count }} 个任务</span>
          <StatusBadge label="strategy" tone="muted" />
        </li>
      </ul>
      <EmptyState v-else title="暂无策略分布" description="补偿任务生成后会在这里按策略聚合。" />
    </DataPanel>

    <DataPanel v-if="section === 'pending'" title="待处理任务表" :status="`${report?.pending_samples.length || 0} 条`">
      <ul v-if="pagedPendingSamples.length" class="data-list data-list--detail-jobs">
        <li v-for="item in pagedPendingSamples" :key="item.id">
          <strong>{{ item.title }}</strong>
          <span>{{ sampleMeta(item) }}</span>
          <StatusBadge :label="item.status" :tone="statusTone(item.status)" />
          <small>{{ item.last_failure_reason || '等待执行' }} · {{ item.next_run_at }}</small>
          <div class="detail-job-actions">
            <button
              class="button button--ghost"
              type="button"
              :disabled="actingJobId === item.id"
              @click="showJobDetail(item)"
            >
              详情
            </button>
            <button
              class="button button--ghost"
              type="button"
              :disabled="actingJobId === item.id"
              @click="runJobAction(item, 'cancel')"
            >
              取消
            </button>
          </div>
        </li>
      </ul>
      <PaginationControl
        v-model:page="pendingPage"
        :page-size="pageSize"
        :total="report?.pending_samples.length || 0"
      />
      <EmptyState v-if="!pagedPendingSamples.length" title="暂无待处理任务" description="当前没有积压的详情补偿任务。" />
    </DataPanel>

    <DataPanel v-if="section === 'failed'" title="失败任务表" :status="`${report?.failed_samples.length || 0} 条`">
      <ul v-if="pagedFailedSamples.length" class="data-list data-list--detail-jobs">
        <li v-for="item in pagedFailedSamples" :key="item.id">
          <strong>{{ item.title }}</strong>
          <span>{{ sampleMeta(item) }}</span>
          <StatusBadge :label="item.status" tone="warning" />
          <small>{{ item.last_failure_reason || '失败原因缺失' }} · {{ item.next_run_at }}</small>
          <div class="detail-job-actions">
            <button
              class="button button--ghost"
              type="button"
              :disabled="actingJobId === item.id"
              @click="showJobDetail(item)"
            >
              详情
            </button>
            <button
              class="button button--primary"
              type="button"
              :disabled="actingJobId === item.id"
              @click="runJobAction(item, 'retry')"
            >
              重试
            </button>
            <button
              class="button button--ghost"
              type="button"
              :disabled="actingJobId === item.id"
              @click="runJobAction(item, 'cancel')"
            >
              取消
            </button>
          </div>
        </li>
      </ul>
      <PaginationControl
        v-model:page="failedPage"
        :page-size="pageSize"
        :total="report?.failed_samples.length || 0"
      />
      <EmptyState v-if="!pagedFailedSamples.length" title="暂无失败任务" description="达到最大重试次数的任务会在这里展示。" />
    </DataPanel>
  </div>
</template>
