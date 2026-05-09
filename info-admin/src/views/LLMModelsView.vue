<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { createLLMModelConfig, getLLMModelConfigs, updateLLMModelConfig } from '@/services/adminApi'
import type { LLMModelConfig, LLMModelConfigPayload } from '@/types/admin'

const configs = ref<LLMModelConfig[]>([])
const editingId = ref<number | null>(null)
const message = ref('')
const form = reactive<LLMModelConfigPayload>({
  provider_name: '千问',
  provider_code: 'qwen',
  base_url: 'http://127.0.0.1:8001/v1',
  api_key: '',
  model_name: 'qwen2.5-14b-instruct',
  is_enabled: 0,
  daily_call_limit: 1000,
  daily_call_count: 0,
  priority: 10,
})

async function refreshData() {
  configs.value = await getLLMModelConfigs()
}

function resetForm() {
  editingId.value = null
  form.provider_name = '千问'
  form.provider_code = 'qwen'
  form.base_url = 'http://127.0.0.1:8001/v1'
  form.api_key = ''
  form.model_name = 'qwen2.5-14b-instruct'
  form.is_enabled = 0
  form.daily_call_limit = 1000
  form.daily_call_count = 0
  form.priority = 10
}

function editConfig(item: LLMModelConfig) {
  editingId.value = item.id
  form.provider_name = item.provider_name
  form.provider_code = item.provider_code
  form.base_url = item.base_url
  form.api_key = ''
  form.model_name = item.model_name
  form.is_enabled = item.is_enabled
  form.daily_call_limit = item.daily_call_limit
  form.daily_call_count = item.daily_call_count
  form.priority = item.priority
}

async function submitConfig() {
  if (editingId.value) {
    await updateLLMModelConfig(editingId.value, { ...form })
    message.value = '大模型配置已更新'
  } else {
    await createLLMModelConfig({ ...form })
    message.value = '大模型配置已新增'
  }
  resetForm()
  await refreshData()
}

onMounted(refreshData)
</script>

<template>
  <section class="page-stack">
    <DataPanel title="大模型配置" status="事件分析增强">
      <form class="inline-form channel-form" @submit.prevent="submitConfig">
        <input v-model="form.provider_name" required placeholder="供应商，例如 千问 / DeepSeek" />
        <input v-model="form.provider_code" required placeholder="编码，例如 qwen / deepseek" />
        <input v-model="form.base_url" required placeholder="接口地址，例如 http://127.0.0.1:8001/v1" />
        <input v-model="form.model_name" required placeholder="模型，例如 qwen2.5-14b-instruct" />
        <input v-model="form.api_key" type="password" placeholder="API Key，留空表示保留原密钥" />
        <input v-model.number="form.daily_call_limit" required type="number" min="0" placeholder="每日上限，0不限" />
        <input v-model.number="form.priority" required type="number" min="1" placeholder="优先级" />
        <select v-model.number="form.is_enabled">
          <option :value="1">启用</option>
          <option :value="0">停用</option>
        </select>
        <button type="submit">{{ editingId ? '更新配置' : '新增配置' }}</button>
        <button v-if="editingId" type="button" class="button--ghost" @click="resetForm">取消编辑</button>
      </form>
      <p class="form-message">{{ message || '所有模型停用或达到每日上限时，事件分析会自动使用本地规则分析。' }}</p>
    </DataPanel>

    <DataPanel title="模型列表" :status="`${configs.length} 个模型`">
      <ul v-if="configs.length" class="data-list">
        <li v-for="item in configs" :key="item.id">
          <div class="channel-quality-main">
            <strong>{{ item.provider_name }} · {{ item.model_name }}</strong>
            <span>{{ item.base_url }}</span>
            <small>
              今日 {{ item.daily_call_count }}/{{ item.daily_call_limit || '不限' }} ·
              优先级 {{ item.priority }} · 最近调用 {{ item.last_call_date || '暂无' }} · 密钥 {{ item.api_key || '未配置' }}
            </small>
            <small>
              近100次 成功 {{ item.success_count || 0 }} / 失败 {{ item.failure_count || 0 }} ·
              平均耗时 {{ item.avg_latency_ms || 0 }}ms · 连续失败 {{ item.consecutive_failure_count || 0 }}
            </small>
            <small v-if="item.circuit_open_until || item.last_failure_reason">
              {{ item.circuit_open_until ? `熔断至 ${item.circuit_open_until}` : '未熔断' }}
              {{ item.last_failure_reason ? ` · 最近失败：${item.last_failure_reason}` : '' }}
            </small>
          </div>
          <div class="channel-quality-badges">
            <StatusBadge :label="item.is_enabled === 1 ? '启用' : '停用'" :tone="item.is_enabled === 1 ? 'success' : 'muted'" />
            <button type="button" class="button--ghost" @click="editConfig(item)">编辑</button>
          </div>
        </li>
      </ul>
      <EmptyState v-else title="暂无大模型配置" description="新增千问、DeepSeek 或兼容 OpenAI 协议的模型后，可以增强事件分析。" />
    </DataPanel>
  </section>
</template>
