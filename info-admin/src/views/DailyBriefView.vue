<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import {
  generateDailyBrief,
  getDailyBriefByDate,
  getDailyBriefs,
  updateDailyBriefStatus,
  type DailyBrief,
} from '@/services/adminApi'

const briefs = ref<DailyBrief[]>([])
const total = ref(0)
const selectedBrief = ref<DailyBrief | null>(null)
const generating = ref(false)
const loading = ref(false)
const message = ref('')

function statusTone(status: string): 'success' | 'warning' | 'muted' | 'error' {
  switch (status) {
    case 'published': return 'success'
    case 'draft': return 'warning'
    case 'archived': return 'muted'
    default: return 'muted'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'published': return 'Published'
    case 'draft': return 'Draft'
    case 'archived': return 'Archived'
    default: return status
  }
}

async function refreshData() {
  loading.value = true
  try {
    const result = await getDailyBriefs(50)
    briefs.value = result.items
    total.value = result.total
  } finally {
    loading.value = false
  }
}

async function viewBrief(brief: DailyBrief) {
  selectedBrief.value = brief
}

function closeDetail() {
  selectedBrief.value = null
}

async function handleGenerate() {
  generating.value = true
  message.value = ''
  try {
    await generateDailyBrief()
    message.value = 'Generation started'
    setTimeout(() => refreshData(), 3000)
  } catch (e: any) {
    message.value = e.message || 'Generation failed'
  } finally {
    generating.value = false
  }
}

async function toggleStatus(brief: DailyBrief) {
  const nextStatus = brief.status === 'draft' ? 'published' : brief.status === 'published' ? 'archived' : 'draft'
  try {
    await updateDailyBriefStatus(brief.brief_date, nextStatus)
    await refreshData()
    if (selectedBrief.value && selectedBrief.value.brief_date === brief.brief_date) {
      selectedBrief.value = { ...selectedBrief.value, status: nextStatus }
    }
  } catch (e: any) {
    message.value = e.message || 'Status update failed'
  }
}

onMounted(refreshData)
</script>

<template>
  <section class="page-stack">
    <DataPanel title="Daily Brief" :status="total + ' items'">
      <div class="action-bar">
        <button :disabled="generating" @click="handleGenerate">
          {{ generating ? 'Generating...' : "Generate Today's Brief" }}
        </button>
        <span class="form-message">{{ message }}</span>
      </div>
      <ul v-if="briefs.length" class="data-list">
        <li v-for="item in briefs" :key="item.id" class="brief-item">
          <div class="brief-main">
            <strong>{{ item.brief_date }}</strong>
            <span>{{ item.headline }}</span>
            <small>{{ item.summary }}</small>
          </div>
          <div class="brief-actions">
            <StatusBadge :label="statusLabel(item.status)" :tone="statusTone(item.status)" />
            <button type="button" class="button--ghost" @click="viewBrief(item)">View</button>
            <button type="button" class="button--ghost" @click="toggleStatus(item)">
              {{ item.status === 'draft' ? 'Publish' : item.status === 'published' ? 'Archive' : 'To Draft' }}
            </button>
          </div>
        </li>
      </ul>
      <EmptyState v-else title="No daily briefs" description="Click the button above to generate today's brief." />
    </DataPanel>

    <DataPanel v-if="selectedBrief" :title="'Brief: ' + selectedBrief.brief_date" status="">
      <div class="detail-header">
        <h3>{{ selectedBrief.headline }}</h3>
        <StatusBadge :label="statusLabel(selectedBrief.status)" :tone="statusTone(selectedBrief.status)" />
        <button type="button" class="button--ghost" @click="closeDetail">Close</button>
      </div>
      <div class="detail-summary">{{ selectedBrief.summary }}</div>
      <div class="detail-content" v-html="selectedBrief.content"></div>
    </DataPanel>
  </section>
</template>

<style scoped>
.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.brief-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border, #eee);
}

.brief-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brief-main strong {
  font-size: 14px;
}

.brief-main span {
  font-size: 13px;
}

.brief-main small {
  color: var(--text-secondary, #909399);
}

.brief-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-header h3 {
  margin: 0;
}

.detail-summary {
  color: var(--text-secondary, #606266);
  margin-bottom: 16px;
  line-height: 1.6;
}

.detail-content {
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
