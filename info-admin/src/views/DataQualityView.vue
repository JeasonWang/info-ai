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
  getChannelQualityReport,
  getLowQualityInfos,
  getQualitySnapshots,
  refreshQuality,
  retryLowQualityDetails,
} from '@/services/adminApi'
import type { ChannelQualityItem, ChannelQualityReport, LowQualityInfo, QualitySnapshot } from '@/types/admin'

const route = useRoute()
const snapshots = ref<QualitySnapshot[]>([])
const lowQualityInfos = ref<LowQualityInfo[]>([])
const channelQuality = ref<ChannelQualityReport | null>(null)
const actionMessage = ref('')
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
  { to: '/data-quality/low-quality', label: '低质量内容', description: '待重抓样本' },
  { to: '/data-quality/actions', label: '治理工具', description: '刷新、重抓、归档' },
]
const pagedChannels = computed(() => pageSlice(channelQuality.value?.channels || [], channelPage.value))
const pagedSnapshots = computed(() => pageSlice(snapshots.value, snapshotPage.value))
const pagedLowQualityInfos = computed(() => pageSlice(lowQualityInfos.value, lowQualityPage.value))

async function loadData() {
  loadError.value = ''
  const [snapshotItems, lowQualityItems, channelQualityReport] = await Promise.all([
    getQualitySnapshots(50),
    getLowQualityInfos(50),
    getChannelQualityReport(5),
  ])
  snapshots.value = snapshotItems
  lowQualityInfos.value = lowQualityItems
  channelQuality.value = channelQualityReport
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

function topStrategyText(item: ChannelQualityItem) {
  if (!item.top_detail_strategies.length) return '暂无详情策略'
  return item.top_detail_strategies.map((strategy) => `${strategy.strategy} ${strategy.count}`).join(' / ')
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
    </section>

    <section class="panel-grid">
      <DataPanel v-if="section === 'actions'" title="治理工具栏" status="人工治理">
        <div class="action-strip">
          <button type="button" :disabled="isRunning" @click="runAction(refreshQuality)">刷新质量</button>
          <button type="button" :disabled="isRunning" @click="runAction(() => retryLowQualityDetails(20))">重抓低完整详情</button>
          <button type="button" class="button--ghost" :disabled="isRunning" @click="runAction(archiveLowQualityInfos)">归档低质量</button>
          <button type="button" class="button--ghost" :disabled="isRunning" @click="runAction(archiveDuplicateTitles)">归档重复标题</button>
        </div>
        <p class="action-message">{{ actionMessage || '操作顺序建议：先刷新质量，再重抓低完整详情，最后归档明显低质或重复内容。' }}</p>
      </DataPanel>

      <DataPanel v-if="section === 'report'" title="渠道质量报告" :status="`${channelQuality?.channels.length ?? 0} 个渠道`">
        <ul v-if="pagedChannels.length" class="data-list data-list--channel-quality">
          <li v-for="item in pagedChannels" :key="item.channel_code">
            <div class="channel-quality-main">
              <strong>{{ item.channel_name }} / {{ item.channel_code }}</strong>
              <span>
                可用 {{ item.usable_ratio }}% · 完整 {{ item.complete_ratio }}% · 待治理 {{ item.needs_attention_ratio }}%
              </span>
              <small>
                真实 {{ item.real_count }} · seed {{ item.seed_count }} · 平均质量 {{ item.avg_detail_score }} · 平均正文 {{ item.avg_detail_content_length }} 字
              </small>
            </div>
            <div class="channel-quality-badges">
              <StatusBadge :label="item.usable_ratio >= 70 ? '质量健康' : item.usable_ratio >= 45 ? '需要关注' : '重点治理'" :tone="qualityTone(item)" />
              <StatusBadge :label="credentialLabel(item)" :tone="credentialTone(item)" />
            </div>
            <div class="channel-quality-detail">
              <span>失败原因：{{ topFailureText(item) }}</span>
              <span>详情策略：{{ topStrategyText(item) }}</span>
            </div>
            <ul v-if="item.weak_samples.length" class="weak-sample-list">
              <li v-for="sample in item.weak_samples" :key="sample.id">
                <strong>{{ sample.title }}</strong>
                <span>{{ sample.detail_fetch_status }} · {{ sample.detail_strategy || '无策略' }} · 质量 {{ sample.detail_score }} · {{ sample.detail_content_length }} 字</span>
                <small>{{ sample.detail_fetch_error || '暂无失败原因' }}</small>
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
