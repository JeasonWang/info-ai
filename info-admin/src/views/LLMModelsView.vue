<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { chatLLM, createLLMModelConfig, getLLMModelConfigs, updateLLMModelConfig } from '@/services/adminApi'
import type { LLMChatResult, LLMModelConfig, LLMModelConfigPayload } from '@/types/admin'

const configs = ref<LLMModelConfig[]>([])
const editingId = ref<number | null>(null)
const configMessage = ref('')
const chatMessage = ref('')
const chattingId = ref<number | null>(null)
const chatResult = ref<LLMChatResult | null>(null)
const selectedChatConfigId = ref<number | ''>('')
const chatInput = ref('请用三句话介绍一下信息达人系统。')
const lastUserMessage = ref('')
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

const enabledConfigs = computed(() => configs.value.filter((item) => item.is_enabled === 1))
const totalRecentCalls = computed(() => configs.value.reduce((sum, item) => sum + (item.success_count || 0) + (item.failure_count || 0), 0))
const totalRecentSuccess = computed(() => configs.value.reduce((sum, item) => sum + (item.success_count || 0), 0))
const llmSuccessRate = computed(() => {
  if (!totalRecentCalls.value) return 0
  return Math.round((totalRecentSuccess.value * 1000) / totalRecentCalls.value) / 10
})
const circuitOpenCount = computed(() => configs.value.filter((item) => Boolean(item.circuit_open_until)).length)
const llmHealthRows = computed(() => [
  { label: '可用模型', count: enabledConfigs.value.length, tone: enabledConfigs.value.length ? 'success' : 'danger' },
  { label: '近百次成功率', count: `${llmSuccessRate.value}%`, tone: llmSuccessRate.value >= 80 ? 'success' : llmSuccessRate.value >= 50 ? 'warning' : 'danger' },
  { label: '熔断中', count: circuitOpenCount.value, tone: circuitOpenCount.value ? 'danger' : 'success' },
])
const selectedChatConfig = computed(() => {
  if (selectedChatConfigId.value === '') return null
  return configs.value.find((item) => item.id === selectedChatConfigId.value) || null
})
const canSendChat = computed(() => chatInput.value.trim().length > 0 && chattingId.value === null)
const chatAnswer = computed(() => chatResult.value?.answer || chatResult.value?.content || chatResult.value?.message || '')

function modelSuccessRate(item: LLMModelConfig) {
  const total = (item.success_count || 0) + (item.failure_count || 0)
  if (!total) return item.success_rate ?? 0
  return item.success_rate ?? Math.round(((item.success_count || 0) * 1000) / total) / 10
}

function modelHealthTone(item: LLMModelConfig) {
  if (item.circuit_open_until) return 'error'
  if (item.is_enabled !== 1) return 'muted'
  const rate = modelSuccessRate(item)
  if (rate >= 80 || ((item.success_count || 0) + (item.failure_count || 0)) === 0) return 'success'
  if (rate >= 50) return 'warning'
  return 'error'
}

function modelHealthLabel(item: LLMModelConfig) {
  if (item.circuit_open_until) return '熔断中'
  if (item.is_enabled !== 1) return '停用'
  return `成功率 ${modelSuccessRate(item)}%`
}

async function refreshData() {
  configs.value = await getLLMModelConfigs()
  if (
    selectedChatConfigId.value !== ''
    && !enabledConfigs.value.some((item) => item.id === selectedChatConfigId.value)
  ) {
    selectedChatConfigId.value = ''
  }
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
    configMessage.value = '大模型配置已更新'
  } else {
    await createLLMModelConfig({ ...form })
    configMessage.value = '大模型配置已新增'
  }
  resetForm()
  await refreshData()
}

async function sendChat(config?: LLMModelConfig | null) {
  const message = chatInput.value.trim()
  if (!message) {
    chatMessage.value = '请输入聊天内容'
    return
  }

  const targetConfig = config ?? selectedChatConfig.value
  if (targetConfig) {
    selectedChatConfigId.value = targetConfig.id
  }
  chattingId.value = targetConfig?.id ?? 0
  chatResult.value = null
  lastUserMessage.value = message
  chatMessage.value = '大模型正在回复，响应可能需要几十秒到数分钟。'
  try {
    chatResult.value = await chatLLM({
      ...(targetConfig ? { config_id: targetConfig.id } : {}),
      message,
      timeout_seconds: 240,
    })
    chatMessage.value = chatResult.value.ok ? '大模型已回复' : '大模型回复失败'
    await refreshData()
  } catch (error) {
    chatMessage.value = error instanceof Error ? error.message : '大模型回复失败'
  } finally {
    chattingId.value = null
  }
}

function useConfigForChat(item: LLMModelConfig) {
  selectedChatConfigId.value = item.id
  chatResult.value = null
  chatMessage.value = `已选择 ${item.provider_name} · ${item.model_name}`
}

onMounted(refreshData)
</script>

<template>
  <section class="page-stack">
    <DataPanel title="大模型配置" status="事件分析增强">
      <div v-if="configs.length" class="analysis-board">
        <div class="analysis-board-item" v-for="item in llmHealthRows" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.count }}</strong>
          <i :class="`analysis-board-mark ${item.tone}`" />
        </div>
      </div>
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
      <p class="form-message">{{ configMessage || '所有模型停用或达到每日上限时，事件分析会自动使用本地规则分析。' }}</p>
    </DataPanel>

    <DataPanel title="大模型聊天" status="admin → serve → aggregation → 模型">
      <form class="llm-test-form" @submit.prevent="sendChat()">
        <label>
          聊天模型
          <select v-model="selectedChatConfigId">
            <option value="">自动选择可用模型</option>
            <option v-for="item in enabledConfigs" :key="item.id" :value="item.id">
              {{ item.provider_name }} · {{ item.model_name }}
            </option>
          </select>
        </label>
        <label>
          聊天内容
          <textarea v-model="chatInput" rows="5" placeholder="输入普通问题，大模型会直接返回答案"></textarea>
        </label>
        <div class="llm-test-actions">
          <button type="submit" :disabled="!canSendChat">
            {{ chattingId !== null ? '回复中' : '发送' }}
          </button>
          <span>{{ chatMessage || '输入问题后可直接和大模型对话，发送和返回内容会记录在调用日志中。' }}</span>
        </div>
      </form>
      <div v-if="chatResult" class="test-result">
        <strong>{{ chatResult.ok ? '模型回答' : '调用失败' }}</strong>
        <span>
          {{ chatResult.provider_code || 'unknown' }} · {{ chatResult.model_name || 'unknown' }}
          {{ chatResult.latency_ms !== undefined ? ` · ${chatResult.latency_ms}ms` : '' }}
        </span>
        <span>你发送的内容</span>
        <pre>{{ lastUserMessage }}</pre>
        <span>大模型返回结果</span>
        <pre>{{ chatAnswer || JSON.stringify(chatResult, null, 2) }}</pre>
      </div>
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
              成功率 {{ modelSuccessRate(item) }}% · 平均耗时 {{ item.avg_latency_ms || 0 }}ms · 连续失败 {{ item.consecutive_failure_count || 0 }}
            </small>
            <small v-if="item.circuit_open_until || item.last_failure_reason">
              {{ item.circuit_open_until ? `熔断至 ${item.circuit_open_until}` : '未熔断' }}
              {{ item.last_failure_reason ? ` · 最近失败：${item.last_failure_reason}` : '' }}
            </small>
          </div>
          <div class="channel-quality-badges">
            <StatusBadge :label="item.is_enabled === 1 ? '启用' : '停用'" :tone="item.is_enabled === 1 ? 'success' : 'muted'" />
            <StatusBadge :label="modelHealthLabel(item)" :tone="modelHealthTone(item)" />
            <button type="button" class="button--ghost" :disabled="item.is_enabled !== 1" @click="useConfigForChat(item)">
              选为聊天模型
            </button>
            <button type="button" class="button--ghost" @click="editConfig(item)">编辑</button>
          </div>
        </li>
      </ul>
      <EmptyState v-else title="暂无大模型配置" description="新增千问、DeepSeek 或兼容 OpenAI 协议的模型后，可以增强事件分析。" />
    </DataPanel>
  </section>
</template>
