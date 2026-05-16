<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getEventAnalysisRuns, getEventAnalysisSources } from '@/services/adminApi'
import StatusBadge from '@/components/StatusBadge.vue'

interface AnalysisRun {
  run_id: number
  analysis_version: string
  mode: string
  provider: string
  model_name: string
  status: string
  input_item_count: number
  quality_score: number
  confidence: number
  fallback_used: boolean
  failure_reason: string
  started_at: string
  finished_at: string
  created_at: string
}

interface AnalysisSource {
  source_id: number
  info_id: number
  title: string
  role: string
  weight: number
  quality_score: number
  channel_name: string
  source_url: string
  event_time: string
}

const route = useRoute()
const eventId = ref<number>(0)
const runs = ref<AnalysisRun[]>([])
const selectedRunId = ref<number | null>(null)
const selectedSources = ref<AnalysisSource[]>([])
const loadingRuns = ref(false)
const loadingSources = ref(false)

onMounted(() => {
  const id = parseInt(route.params.id as string)
  if (id) {
    eventId.value = id
    loadRuns()
  }
})

async function loadRuns() {
  loadingRuns.value = true
  try {
    const result = await getEventAnalysisRuns(eventId.value)
    runs.value = result.runs
    if (runs.value.length > 0 && !selectedRunId.value) {
      selectedRunId.value = runs.value[0].run_id
    }
  } catch (e) {
    console.error('加载分析运行失败', e)
    runs.value = []
  } finally {
    loadingRuns.value = false
  }
}

watch(selectedRunId, async (newRunId) => {
  if (newRunId) {
    await loadSources(newRunId)
  }
})

async function loadSources(runId: number) {
  loadingSources.value = true
  try {
    const result = await getEventAnalysisSources(eventId.value, runId)
    selectedSources.value = result.sources
  } catch (e) {
    console.error('加载分析来源失败', e)
    selectedSources.value = []
  } finally {
    loadingSources.value = false
  }
}

function getModeLabel(mode: string): string {
  const map: Record<string, string> = {
    rule: '规则',
    llm: '大模型',
    hybrid: '混合',
  }
  return map[mode] || mode
}

function getRoleLabel(role: string): string {
  const map: Record<string, string> = {
    primary: '主要来源',
    media: '媒体来源',
    background: '背景资料',
  }
  return map[role] || role
}

function getStatusTone(status: string): 'success' | 'warning' | 'error' {
  const map: Record<string, 'success' | 'warning' | 'error'> = {
    succeeded: 'success',
    fallback: 'warning',
    failed: 'error',
  }
  return map[status] || 'warning'
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    succeeded: '成功',
    fallback: '规则回退',
    failed: '失败',
  }
  return map[status] || status
}
</script>

<template>
  <div class="analysis-detail">
    <div class="page-header">
      <h2>事件分析溯源</h2>
      <p class="subtitle">事件 ID: {{ eventId }}</p>
    </div>

    <div class="content-grid">
      <!-- 左侧：分析运行列表 -->
      <div class="runs-panel">
        <h3>分析运行历史</h3>
        <div v-if="loadingRuns" class="loading">加载中...</div>
        <div v-else-if="runs.length === 0" class="empty">
          暂无分析记录
        </div>
        <ul v-else class="runs-list">
          <li
            v-for="run in runs"
            :key="run.run_id"
            class="run-item"
            :class="{ active: selectedRunId === run.run_id }"
            @click="selectedRunId = run.run_id"
          >
            <div class="run-header">
              <span class="run-time">{{ run.created_at }}</span>
              <StatusBadge
                :label="getStatusLabel(run.status)"
                :tone="getStatusTone(run.status)"
              />
            </div>
            <div class="run-meta">
              <span class="mode-tag">{{ getModeLabel(run.mode) }}</span>
              <span v-if="run.provider" class="provider">{{ run.provider }}</span>
              <span v-if="run.model_name" class="model">{{ run.model_name }}</span>
            </div>
            <div class="run-stats">
              <span>来源数: {{ run.input_item_count }}</span>
              <span>质量分: {{ run.quality_score.toFixed(1) }}</span>
              <span>置信度: {{ (run.confidence * 100).toFixed(0) }}%</span>
            </div>
            <div v-if="run.fallback_used" class="fallback-notice">
              触发了规则回退
            </div>
            <div v-if="run.failure_reason" class="failure-notice">
              {{ run.failure_reason }}
            </div>
          </li>
        </ul>
      </div>

      <!-- 右侧：来源明细 -->
      <div class="sources-panel">
        <h3>来源明细</h3>
        <div v-if="!selectedRunId" class="empty">
          请选择左侧的分析运行
        </div>
        <div v-else-if="loadingSources" class="loading">
          加载中...
        </div>
        <div v-else-if="selectedSources.length === 0" class="empty">
          暂无来源记录
        </div>
        <ul v-else class="sources-list">
          <li v-for="source in selectedSources" :key="source.source_id" class="source-item">
            <div class="source-header">
              <StatusBadge
                :label="getRoleLabel(source.role)"
                :tone="source.role === 'primary' ? 'success' : 'muted'"
              />
              <span class="weight">权重: {{ source.weight }}</span>
              <span class="quality">质量: {{ source.quality_score }}</span>
            </div>
            <div class="source-title">{{ source.title }}</div>
            <div class="source-meta">
              <span v-if="source.channel_name" class="channel">{{ source.channel_name }}</span>
              <span v-if="source.event_time" class="time">{{ source.event_time }}</span>
            </div>
            <a
              v-if="source.source_url"
              :href="source.source_url"
              target="_blank"
              class="source-url"
            >
              查看原文
            </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-detail {
  padding: 0;
}

.page-header {
  margin-bottom: 12px;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 15px;
}

.subtitle {
  margin: 0;
  color: var(--subtle);
  font-size: 13px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.runs-panel,
.sources-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 12px;
}

h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--ink);
  border-bottom: 1px solid var(--line);
  padding-bottom: 8px;
}

.loading,
.empty {
  text-align: center;
  padding: 20px;
  color: var(--subtle);
  font-size: 13px;
}

.runs-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.run-item {
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.run-item:hover {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.run-item.active {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.run-time {
  font-size: 12px;
  color: var(--muted);
}

.run-meta {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
}

.mode-tag {
  background: var(--primary);
  color: #fff;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.provider,
.model {
  color: var(--subtle);
  font-size: 11px;
}

.run-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--muted);
}

.fallback-notice {
  margin-top: 6px;
  padding: 3px 8px;
  background: var(--warning-soft);
  color: var(--warning);
  font-size: 12px;
  border-radius: 4px;
}

.failure-notice {
  margin-top: 6px;
  padding: 3px 8px;
  background: #fef0f0;
  color: var(--danger);
  font-size: 12px;
  border-radius: 4px;
}

.sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.source-item {
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  margin-bottom: 8px;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.weight,
.quality {
  font-size: 12px;
  color: var(--subtle);
}

.source-title {
  font-size: 13px;
  color: var(--ink);
  margin-bottom: 6px;
  line-height: 1.4;
}

.source-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}

.source-url {
  font-size: 12px;
  color: var(--primary);
  text-decoration: none;
}

.source-url:hover {
  text-decoration: underline;
}
</style>
