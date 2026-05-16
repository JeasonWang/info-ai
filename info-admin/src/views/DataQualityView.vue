<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import MetricCard from '@/components/MetricCard.vue'
import PageTabs from '@/components/PageTabs.vue'
import PaginationControl from '@/components/PaginationControl.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import {
  archiveDuplicateTitles,
  archiveLowQualityInfos,
  enqueueEventAnalysisDetailJobs,
  getChannelQualityReport,
  getEventAnalysisQualityReport,
  getLowQualityInfos,
  getQualitySnapshots,
  prioritizeWeakSourceGovernance,
  rebuildStaleEventAnalysis,
  refreshQuality,
  retryLowQualityDetails,
} from '@/services/adminApi'
import type {
  AdminActionResult,
  ChannelQualityItem,
  ChannelQualityReport,
  EventAnalysisQualityReport,
  EventAnalysisRiskEvent,
  LowQualityInfo,
  QualitySnapshot,
  RetryLowQualitySelectedSample,
} from '@/types/admin'

const route = useRoute()
const snapshots = ref<QualitySnapshot[]>([])
const lowQualityInfos = ref<LowQualityInfo[]>([])
const channelQuality = ref<ChannelQualityReport | null>(null)
const eventAnalysisQuality = ref<EventAnalysisQualityReport | null>(null)
const actionMessage = ref('')
const retrySamples = ref<RetryLowQualitySelectedSample[]>([])
const isRunning = ref(false)
const loadError = ref('')
const channelPage = ref(1)
const snapshotPage = ref(1)
const lowQualityPage = ref(1)
const pageSize = 8

const section = computed(() => String(route.meta.section || 'report'))
const tabs = [
  { to: '/data-quality/report', label: '渠道质量', description: '完整率、可用率、凭证' },
  { to: '/data-quality/snapshots', label: '质量快照', description: '分类维度趋势' },
  { to: '/data-quality/event-analysis', label: '事件分析质量', description: '置信度、回退、弱来源' },
  { to: '/data-quality/low-quality', label: '低质量内容', description: '待重抓样本' },
  { to: '/data-quality/actions', label: '治理工具', description: '刷新、重抓、归档' },
]
const pagedChannels = computed(() => pageSlice(channelQuality.value?.channels || [], channelPage.value))
const riskEvents = computed(() => eventAnalysisQuality.value?.risk_events || [])
const displayQuality = computed(() => eventAnalysisQuality.value?.display_quality || null)
const blockedEventSamples = computed(() => displayQuality.value?.blocked_samples || [])
const pagedSnapshots = computed(() => pageSlice(snapshots.value, snapshotPage.value))
const pagedLowQualityInfos = computed(() => pageSlice(lowQualityInfos.value, lowQualityPage.value))
const channelStatusRows = computed(() => (channelQuality.value?.channels || []).slice(0, 8))
const coreSourceRows = computed(() => channelQuality.value?.core_sources || [])
const analysisRiskRows = computed(() => {
  const summary = eventAnalysisQuality.value?.summary
  if (!summary) return []
  return [
    { label: '缺失分析', count: summary.missing_analysis_count || 0, tone: 'warning' },
    { label: '低置信度', count: summary.low_confidence_count || 0, tone: 'warning' },
    { label: '模型回退', count: summary.fallback_count || 0, tone: 'danger' },
    { label: '展示拦截', count: displayQuality.value?.summary.blocked_count || 0, tone: 'muted' },
  ]
})

async function loadData() {
  loadError.value = ''
  const [snapshotItems, lowQualityItems, channelQualityReport, eventAnalysisReport] = await Promise.all([
    getQualitySnapshots(50),
    getLowQualityInfos(50),
    getChannelQualityReport(5),
    getEventAnalysisQualityReport(50),
  ])
  snapshots.value = snapshotItems
  lowQualityInfos.value = lowQualityItems
  channelQuality.value = channelQualityReport
  eventAnalysisQuality.value = eventAnalysisReport
}

function pageSlice<T>(items: T[], page: number) {
  const start = (page - 1) * pageSize
  return items.slice(start, start + pageSize)
}

async function runAction(action: () => Promise<AdminActionResult>) {
  isRunning.value = true
  actionMessage.value = '正在执行，请稍候...'
  retrySamples.value = []
  try {
    const result = await action()
    actionMessage.value = result.message || '操作已提交'
    retrySamples.value = result.data?.selected_samples || []
    await loadData()
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '操作失败'
  } finally {
    isRunning.value = false
  }
}

onMounted(async () => {
  try {
    await loadData()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '渠道质量报告加载失败'
  }
})

function qualityTone(item: ChannelQualityItem) {
  if (item.usable_ratio >= 70 && item.needs_attention_ratio <= 20) return 'success'
  if (item.usable_ratio >= 45) return 'warning'
  return 'muted'
}

function credentialLabel(item: ChannelQualityItem) {
  const health = item.credential_health?.health
  if (health === 'ready' || health === 'not_required') return health === 'ready' ? '凭证正常' : '无需凭证'
  if (health === 'missing_required') return '缺少凭证'
  return '凭证待查'
}

function credentialTone(item: ChannelQualityItem) {
  const health = item.credential_health?.health
  if (health === 'ready' || health === 'not_required') return 'success'
  if (health === 'missing_required') return 'warning'
  return 'muted'
}

function topFailureText(item: ChannelQualityItem) {
  if (!item.top_failure_reasons.length) return '暂无主要失败原因'
  return item.top_failure_reasons.map((reason) => `${reason.reason} ${reason.count}`).join(' / ')
}

function sourceStatusText(item: ChannelQualityItem) {
  return [
    `完整 ${item.complete_count}`,
    `部分 ${item.partial_count ?? item.high_value_partial_count ?? 0}`,
    `列表 ${item.list_only_count ?? 0}`,
    `失败 ${item.failed_count ?? 0}`,
    `待抓 ${item.pending_count ?? 0}`,
  ].join(' / ')
}

function topStrategyText(item: ChannelQualityItem) {
  if (!item.top_detail_strategies.length) return '暂无详情策略'
  return item.top_detail_strategies.map((strategy) => `${strategy.strategy} ${strategy.count}`).join(' / ')
}

function riskReasonText(sample: { risk_reasons?: string[] }) {
  return sample.risk_reasons?.length ? sample.risk_reasons.join(' / ') : '暂无风险原因'
}

function eventIssueText(item: EventAnalysisRiskEvent) {
  const labels: Record<string, string> = {
    missing_analysis: '缺少分析',
    llm_or_analysis_fallback: '模型回退',
    low_confidence: '置信度低',
    low_quality_score: '质量分低',
    fallback_used: '已使用兜底',
    weak_sources: '弱来源',
    empty_one_line_summary: '摘要为空',
  }
  return item.issue_reasons.map((reason) => labels[reason] || reason).join(' / ')
}

function eventRiskTone(item: EventAnalysisRiskEvent) {
  if (item.risk_score >= 80) return 'warning'
  if (item.risk_score >= 45) return 'muted'
  return 'success'
}

function displayReasonText(reasons: string[]) {
  const labels: Record<string, string> = {
    empty_sources: '无来源',
    single_weak_source: '单一弱来源',
    low_value_content: '低价值内容',
    social_signal_without_fact_source: '社交热度缺事实源',
    missing_complete_source: '缺完整来源',
    missing_usable_source: '缺可用来源',
    mixed_unrelated_sources: '疑似错合并串台',
  }
  return reasons.length ? reasons.map((reason) => labels[reason] || reason).join(' / ') : '暂无拦截原因'
}

function displayStatusTone(status: string) {
  if (status === 'active') return 'success'
  if (status === 'monitoring') return 'warning'
  return 'muted'
}

function percentWidth(value: number | undefined) {
  return `${Math.max(0, Math.min(100, Number(value || 0)))}%`
}

function progressTone(value: number | undefined) {
  const ratio = Number(value || 0)
  if (ratio >= 70) return 'success'
  if (ratio >= 45) return 'warning'
  return 'danger'
}
</script>

<template>
  <section class="page-stack">
    <PageTabs :items="tabs" />

    <p v-if="loadError" class="error-message">{{ loadError }}</p>

    <section class="metric-grid metric-grid--compact">
      <MetricCard
        label="真实内容"
        :value="channelQuality?.summary.real_count ?? 0"
        hint="已排除 seed/mock 数据后的真实采集内容"
      />
      <MetricCard
        label="可用率"
        :value="`${channelQuality?.summary.usable_ratio ?? 0}%`"
        hint="完整详情 + 高分 partial 内容占比"
      />
      <MetricCard
        label="待治理"
        :value="channelQuality?.summary.needs_attention_count ?? 0"
        hint="失败、列表态、短正文或低评分内容"
      />
      <MetricCard
        label="分析风险"
        :value="eventAnalysisQuality?.summary.risk_event_count ?? 0"
        hint="低置信度、模型回退、弱来源或缺失分析事件"
      />
      <MetricCard
        label="展示可用率"
        :value="`${displayQuality?.summary.display_ready_ratio ?? 0}%`"
        hint="展示质量门槛下可进入用户端的信息比例"
      />
    </section>

    <section class="panel-grid">
      <DataPanel v-if="section === 'actions'" title="治理工具栏" status="人工治理">
        <div class="action-strip">
          <button type="button" :disabled="isRunning" @click="runAction(refreshQuality)">刷新质量</button>
          <button type="button" :disabled="isRunning" @click="runAction(() => retryLowQualityDetails(20))">重抓低完整详情</button>
          <button type="button" :disabled="isRunning" @click="runAction(() => enqueueEventAnalysisDetailJobs(20))">补偿分析弱来源</button>
          <button type="button" :disabled="isRunning" @click="runAction(() => prioritizeWeakSourceGovernance(20))">优先治理弱来源</button>
          <button type="button" class="button--ghost" :disabled="isRunning" @click="runAction(archiveLowQualityInfos)">归档低质量</button>
          <button type="button" class="button--ghost" :disabled="isRunning" @click="runAction(archiveDuplicateTitles)">归档重复标题</button>
        </div>
        <p class="action-message">{{ actionMessage || '操作顺序建议：先刷新质量，再重抓低完整详情，最后归档明显低质或重复内容。' }}</p>
        <ul v-if="retrySamples.length" class="retry-sample-list">
          <li v-for="sample in retrySamples" :key="sample.info_id">
            <div>
              <strong>{{ sample.title }}</strong>
              <span>{{ sample.channel_code }} · 优先级 {{ sample.attention_priority }} · {{ sample.quality_level }}</span>
            </div>
            <small>{{ sample.quality_summary }}</small>
            <small>动作：{{ sample.recommended_action }} · 原因：{{ riskReasonText(sample) }}</small>
          </li>
        </ul>
      </DataPanel>

      <DataPanel v-if="section === 'report'" title="渠道质量报告" :status="`${channelQuality?.channels.length ?? 0} 个渠道`">
        <div v-if="coreSourceRows.length" class="ruoyi-table">
          <div class="ruoyi-table-row ruoyi-table-head">
            <span>核心信源</span>
            <span>完整率</span>
            <span>可用率</span>
            <span>状态分布</span>
            <span>下一步动作</span>
          </div>
          <div v-for="item in coreSourceRows" :key="`core-${item.channel_code}`" class="ruoyi-table-row">
            <strong>{{ item.channel_name }} / {{ item.channel_code }}</strong>
            <div class="progress-cell">
              <span class="progress-track">
                <i :class="`progress-bar ${progressTone(item.complete_ratio)}`" :style="{ width: percentWidth(item.complete_ratio) }" />
              </span>
              <em>{{ item.complete_ratio }}%</em>
            </div>
            <div class="progress-cell">
              <span class="progress-track">
                <i :class="`progress-bar ${progressTone(item.usable_ratio)}`" :style="{ width: percentWidth(item.usable_ratio) }" />
              </span>
              <em>{{ item.usable_ratio }}%</em>
            </div>
            <span>{{ sourceStatusText(item) }}</span>
            <span>{{ item.primary_issue || topFailureText(item) }} · {{ item.next_action || '继续观察' }}</span>
          </div>
        </div>

        <div v-if="channelStatusRows.length" class="ruoyi-table">
          <div class="ruoyi-table-row ruoyi-table-head">
            <span>渠道</span>
            <span>完整率</span>
            <span>可用率</span>
            <span>待治理</span>
            <span>凭证</span>
          </div>
          <div v-for="item in channelStatusRows" :key="`status-${item.channel_code}`" class="ruoyi-table-row">
            <strong>{{ item.channel_name }} / {{ item.channel_code }}</strong>
            <div class="progress-cell">
              <span class="progress-track">
                <i :class="`progress-bar ${progressTone(item.complete_ratio)}`" :style="{ width: percentWidth(item.complete_ratio) }" />
              </span>
              <em>{{ item.complete_ratio }}%</em>
            </div>
            <div class="progress-cell">
              <span class="progress-track">
                <i :class="`progress-bar ${progressTone(item.usable_ratio)}`" :style="{ width: percentWidth(item.usable_ratio) }" />
              </span>
              <em>{{ item.usable_ratio }}%</em>
            </div>
            <span>{{ item.needs_attention_count }} 条 / {{ item.needs_attention_ratio }}%</span>
            <StatusBadge :label="credentialLabel(item)" :tone="credentialTone(item)" />
          </div>
        </div>

        <ul v-if="pagedChannels.length" class="data-list data-list--channel-quality">
          <li v-for="item in pagedChannels" :key="item.channel_code">
            <div class="channel-quality-main">
              <strong>{{ item.channel_name }} / {{ item.channel_code }}</strong>
              <span>
                可用 {{ item.usable_ratio }}% · 完整 {{ item.complete_ratio }}% · 待治理 {{ item.needs_attention_ratio }}%
              </span>
              <small>
                治理优先级 {{ item.quality_rank_score }} · 真实 {{ item.real_count }} · seed {{ item.seed_count }} · 平均质量 {{ item.avg_detail_score }} · 平均正文 {{ item.avg_detail_content_length }} 字
              </small>
            </div>
            <div class="channel-quality-badges">
              <StatusBadge :label="item.usable_ratio >= 70 ? '质量健康' : item.usable_ratio >= 45 ? '需要关注' : '重点治理'" :tone="qualityTone(item)" />
              <StatusBadge :label="credentialLabel(item)" :tone="credentialTone(item)" />
            </div>
            <div class="channel-quality-detail">
              <span>失败原因：{{ topFailureText(item) }}</span>
              <span>详情策略：{{ topStrategyText(item) }}</span>
              <span>下一步：{{ item.primary_issue || '质量状态' }} · {{ item.next_action || '继续观察' }}</span>
              <span>治理建议：{{ item.governance_advice.join(' / ') }}</span>
            </div>
            <ul v-if="item.weak_samples.length" class="weak-sample-list">
              <li v-for="sample in item.weak_samples" :key="sample.id">
                <strong>{{ sample.title }}</strong>
                <span>
                  {{ sample.detail_fetch_status }} · {{ sample.detail_strategy || '无策略' }} ·
                  质量 {{ sample.detail_score }} · {{ sample.detail_content_length }} 字 ·
                  优先级 {{ sample.attention_priority ?? '-' }}
                </span>
                <small>{{ sample.quality_summary || sample.detail_fetch_error || '暂无失败原因' }}</small>
                <small>建议：{{ sample.recommended_action || '继续观察' }} · {{ riskReasonText(sample) }}</small>
              </li>
            </ul>
          </li>
        </ul>
        <PaginationControl
          v-model:page="channelPage"
          :page-size="pageSize"
          :total="channelQuality?.channels.length ?? 0"
        />
        <EmptyState v-if="!pagedChannels.length" title="暂无渠道质量报告" description="采集服务启动并写入真实数据后会展示渠道完整率和失败原因。" />
      </DataPanel>

      <DataPanel v-if="section === 'snapshots'" title="数据质量快照" :status="`${snapshots.length} 条`">
        <ul v-if="pagedSnapshots.length" class="data-list">
          <li v-for="item in pagedSnapshots" :key="`${item.category_code}-${item.snapshot_at}`">
            <strong>{{ item.category_code }} · {{ item.total_count }} 条</strong>
            <span>
              真实完整率 {{ item.real_complete_detail_ratio }}% ·
              真实完整 {{ item.real_complete_detail_count }}/{{ item.real_detail_total }} ·
              seed {{ item.seed_detail_count }}
            </span>
            <small>重复 {{ item.duplicate_title_count }} / 缺正文 {{ item.empty_content_count }} / 缺实体 {{ item.missing_entity_count }}</small>
          </li>
        </ul>
        <PaginationControl v-model:page="snapshotPage" :page-size="pageSize" :total="snapshots.length" />
        <EmptyState v-if="!pagedSnapshots.length" title="暂无质量快照" description="质量任务写入后会展示质量变化。" />
      </DataPanel>

      <DataPanel
        v-if="section === 'event-analysis'"
        title="事件分析质量"
        :status="`${eventAnalysisQuality?.summary.risk_event_count ?? 0} 个风险事件`"
      >
        <div class="action-strip action-strip--compact">
          <button type="button" :disabled="isRunning" @click="runAction(() => enqueueEventAnalysisDetailJobs(20))">
            入队弱来源补偿
          </button>
          <button type="button" :disabled="isRunning" @click="runAction(() => prioritizeWeakSourceGovernance(20))">
            优先治理弱来源
          </button>
          <button type="button" class="button--ghost" :disabled="isRunning" @click="runAction(refreshQuality)">
            重建分析质量
          </button>
          <button type="button" class="button--ghost" :disabled="isRunning" @click="runAction(() => rebuildStaleEventAnalysis(200))">
            处理过期分析
          </button>
        </div>
        <div v-if="analysisRiskRows.length" class="analysis-board">
          <div class="analysis-board-item" v-for="item in analysisRiskRows" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
            <i :class="`analysis-board-mark ${item.tone}`" />
          </div>
        </div>
        <div class="quality-summary-strip">
          <span>活跃事件 {{ eventAnalysisQuality?.summary.active_event_count ?? 0 }}</span>
          <span>已分析 {{ eventAnalysisQuality?.summary.analyzed_count ?? 0 }}</span>
          <span>缺失分析 {{ eventAnalysisQuality?.summary.missing_analysis_count ?? 0 }}</span>
          <span>低置信度 {{ eventAnalysisQuality?.summary.low_confidence_count ?? 0 }}</span>
          <span>模型回退 {{ eventAnalysisQuality?.summary.fallback_count ?? 0 }}</span>
          <span>平均质量 {{ eventAnalysisQuality?.summary.avg_quality_score ?? 0 }}</span>
        </div>
        <div class="quality-summary-strip">
          <span>追踪事件 {{ displayQuality?.summary.tracked_event_count ?? 0 }}</span>
          <span>可展示 {{ displayQuality?.summary.display_ready_count ?? 0 }}</span>
          <span>已拦截 {{ displayQuality?.summary.blocked_count ?? 0 }}</span>
          <span>展示可用率 {{ displayQuality?.summary.display_ready_ratio ?? 0 }}%</span>
          <span>
            主要原因
            {{
              displayQuality?.summary.top_block_reasons.length
                ? displayQuality.summary.top_block_reasons.map((item) => `${item.reason} ${item.count}`).join(' / ')
                : '暂无'
            }}
          </span>
        </div>
        <ul v-if="riskEvents.length" class="data-list event-analysis-list">
          <li v-for="item in riskEvents" :key="item.event_id">
            <div class="event-analysis-main">
              <router-link :to="`/data-quality/event-analysis/${item.event_id}`" class="event-link">
                <strong>{{ item.title }}</strong>
              </router-link>
              <span>{{ item.one_line_summary || '暂无一句话摘要' }}</span>
              <small>
                来源 {{ item.source_count }} · 弱来源 {{ item.weak_source_count }} ·
                质量 {{ item.quality_score }} · 置信度 {{ item.confidence }} ·
                {{ item.provider || '未分析' }} {{ item.model_name }}
              </small>
            </div>
            <div class="channel-quality-badges">
              <StatusBadge :label="eventIssueText(item)" :tone="eventRiskTone(item)" />
              <StatusBadge :label="item.status" :tone="item.fallback_used ? 'warning' : 'success'" />
            </div>
            <div class="channel-quality-detail">
              <span>下一步：{{ item.primary_issue || eventIssueText(item) }} · {{ item.next_action || item.governance_advice[0] || '继续观察' }}</span>
              <span>治理建议：{{ item.governance_advice.join(' / ') }}</span>
              <span v-if="item.failure_reason">失败原因：{{ item.failure_reason }}</span>
              <span v-if="item.last_analyzed_at">分析时间：{{ item.last_analyzed_at }}</span>
            </div>
          </li>
        </ul>
        <EmptyState
          v-if="!riskEvents.length"
          title="事件分析质量稳定"
          description="当前没有命中低置信度、模型回退、弱来源或缺失分析的事件。"
        />
        <h3 class="subsection-title">展示质量拦截样本</h3>
        <ul v-if="blockedEventSamples.length" class="data-list event-analysis-list">
          <li v-for="item in blockedEventSamples" :key="item.event_id">
            <div class="event-analysis-main">
              <router-link :to="`/data-quality/event-analysis/${item.event_id}`" class="event-link">
                <strong>{{ item.title }}</strong>
              </router-link>
              <span>{{ item.one_line_summary || '暂无一句话摘要' }}</span>
              <small>
                来源 {{ item.source_count }} · 展示分 {{ item.display_quality_score }} ·
                等级 {{ item.display_quality_level || '未评级' }} · {{ item.last_updated_at || '暂无更新时间' }}
              </small>
            </div>
            <div class="channel-quality-badges">
              <StatusBadge :label="item.status" :tone="displayStatusTone(item.status)" />
              <StatusBadge :label="displayReasonText(item.display_quality_reasons)" tone="warning" />
            </div>
            <div class="channel-quality-detail">
              <span>下一步：{{ item.primary_issue || displayReasonText(item.display_quality_reasons) }} · {{ item.next_action || '补充证据后刷新展示质量' }}</span>
            </div>
          </li>
        </ul>
        <EmptyState
          v-if="!blockedEventSamples.length"
          title="暂无展示拦截样本"
          description="当前没有 monitoring 或 low_quality 事件。"
        />
      </DataPanel>

      <DataPanel v-if="section === 'low-quality'" title="低质量内容" :status="`${lowQualityInfos.length} 条`">
        <ul v-if="pagedLowQualityInfos.length" class="data-list">
          <li v-for="item in pagedLowQualityInfos" :key="item.id">
            <strong>{{ item.title }}</strong>
            <span>{{ item.issue_reason }} · 质量 {{ item.detail_score }} · 正文 {{ item.detail_content_length }} 字</span>
            <small>{{ item.category_name }} / {{ item.channel_name }} · {{ item.updated_at }}</small>
          </li>
        </ul>
        <PaginationControl v-model:page="lowQualityPage" :page-size="pageSize" :total="lowQualityInfos.length" />
        <EmptyState v-if="!pagedLowQualityInfos.length" title="暂无低质量内容" description="当前没有命中正文为空、详情评分偏低或关键实体缺失的内容。" />
      </DataPanel>
    </section>
  </section>
</template>
