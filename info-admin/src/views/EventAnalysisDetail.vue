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
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 20px;
}

.subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.runs-panel,
.sources-panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 12px;
}

.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.runs-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.run-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.run-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.run-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.run-time {
  font-size: 13px;
  color: #606266;
}

.run-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.mode-tag {
  background: #409eff;
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
}

.provider,
.model {
  color: #909399;
}

.run-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #606266;
}

.fallback-notice {
  margin-top: 8px;
  padding: 4px 8px;
  background: #fdf6ec;
  color: #e6a23c;
  font-size: 12px;
  border-radius: 4px;
}

.failure-notice {
  margin-top: 8px;
  padding: 4px 8px;
  background: #fef0f0;
  color: #f56c6c;
  font-size: 12px;
  border-radius: 4px;
}

.sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.source-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 12px;
}

.source-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.weight,
.quality {
  font-size: 12px;
  color: #909399;
}

.source-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
  line-height: 1.4;
}

.source-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

.source-url {
  font-size: 12px;
  color: #409eff;
  text-decoration: none;
}

.source-url:hover {
  text-decoration: underline;
}
</style>
