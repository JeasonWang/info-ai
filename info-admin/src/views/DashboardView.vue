<script setup lang="ts">
import { onMounted, ref } from 'vue'
import MetricCard from '@/components/MetricCard.vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import { getAdminOverview } from '@/services/adminApi'
import type { AdminOverview } from '@/types/admin'

const overview = ref<AdminOverview | null>(null)
const errorMessage = ref('')

onMounted(async () => {
  try {
    overview.value = await getAdminOverview()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '管理总览加载失败'
  }
})
</script>

<template>
  <section class="page-stack">
    <section class="hero-card">
      <div>
        <p class="eyebrow">MONITORING</p>
        <h3>先看清数据，再干预采集</h3>
        <p class="hero-copy">Pro 后台聚焦采集健康、质量治理和配置安全，用户端只保留清爽阅读体验。</p>
      </div>
      <span class="status-pill">info-serve</span>
    </section>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <section class="metric-grid">
      <MetricCard label="采集渠道" :value="overview?.channel_count ?? '--'" hint="来自 Pro MySQL 数据库" />
      <MetricCard label="热点事件" :value="overview?.event_count ?? '--'" hint="当前可展示事件" />
      <MetricCard label="原始内容" :value="overview?.info_count ?? '--'" hint="进入 Pro 数据底座" />
    </section>

    <section class="panel-grid">
      <DataPanel title="数据质量" status="已接入">
        <ul v-if="overview" class="data-list">
          <li><strong>重复标题</strong><span>{{ overview.quality.duplicate_title_count }} 条</span></li>
          <li><strong>正文缺失</strong><span>{{ overview.quality.empty_content_count }} 条</span></li>
          <li><strong>实体缺失</strong><span>{{ overview.quality.missing_entity_count }} 条</span></li>
          <li><strong>低详情评分</strong><span>{{ overview.quality.low_detail_score_count }} 条</span></li>
        </ul>
        <EmptyState v-else title="等待总览数据" description="登录后会从 info-serve 加载质量指标。" />
      </DataPanel>

      <DataPanel title="最近采集" :status="overview?.recent_runs?.length ? `${overview.recent_runs.length} 条` : '暂无'">
        <ul v-if="overview?.recent_runs?.length" class="data-list">
          <li v-for="item in overview.recent_runs" :key="`${item.channel_code}-${item.started_at}`">
            <strong>{{ item.channel_code }} · {{ item.status }}</strong>
            <span>入库 {{ item.saved_count }} / 详情失败 {{ item.detail_failed_count }}</span>
          </li>
        </ul>
        <EmptyState v-else title="暂无运行日志" description="采集任务写入后会展示最近运行状态。" />
      </DataPanel>
    </section>
  </section>
</template>
