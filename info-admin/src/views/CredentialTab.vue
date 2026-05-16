<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { getChannels, getChannelCredentials, updateChannelCredentials, testChannelCredentials, deleteChannelCredentials } from '@/services/adminApi'
import type { ChannelCredentialInfo, ChannelCredentialPayload, CredentialTestResult } from '@/services/adminApi'
import StatusBadge from '@/components/StatusBadge.vue'
import type { AdminChannel } from '@/types/admin'

const channels = ref<AdminChannel[]>([])
const selectedChannel = ref<string>('')
const credentialInfo = ref<ChannelCredentialInfo | null>(null)
const loading = ref(false)
const testing = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const cookiesInput = ref('')
const extraCredentialsInput = ref('')

const credentialChannels = ['weibo', 'zhihu', 'xiaohongshu']

onMounted(async () => {
  await loadChannels()
})

async function loadChannels() {
  channels.value = await getChannels()
  const hasCredentialChannel = channels.value.find(c => credentialChannels.includes(c.code))
  if (hasCredentialChannel && !selectedChannel.value) {
    selectedChannel.value = hasCredentialChannel.code
  }
}

watch(selectedChannel, async (newChannel) => {
  if (newChannel) {
    await loadCredentialInfo(newChannel)
  }
})

async function loadCredentialInfo(channelCode: string) {
  loading.value = true
  message.value = ''
  try {
    credentialInfo.value = await getChannelCredentials(channelCode)
    // 显示脱敏的 cookie
    cookiesInput.value = ''
    // 如果有配置，显示脱敏预览
    if (credentialInfo.value?.cookie_configured) {
      extraCredentialsInput.value = JSON.stringify(credentialInfo.value.extra_credentials || {}, null, 2)
    } else {
      extraCredentialsInput.value = '{}'
    }
  } catch (e) {
    credentialInfo.value = null
    console.error('加载凭证信息失败', e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!selectedChannel.value) return
  loading.value = true
  message.value = ''
  try {
    const payload: ChannelCredentialPayload = {
      cookies: cookiesInput.value,
      updated_by: 'admin',
    }
    if (extraCredentialsInput.value.trim()) {
      try {
        payload.extra_credentials = JSON.parse(extraCredentialsInput.value)
      } catch {
        message.value = '额外凭证格式错误，请输入有效的 JSON'
        messageType.value = 'error'
        loading.value = false
        return
      }
    }
    await updateChannelCredentials(selectedChannel.value, payload)
    message.value = '凭证保存成功'
    messageType.value = 'success'
    await loadCredentialInfo(selectedChannel.value)
  } catch (e: any) {
    message.value = e?.message || '保存失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function handleTest() {
  if (!selectedChannel.value) return
  testing.value = true
  message.value = ''
  try {
    const result: CredentialTestResult = await testChannelCredentials(selectedChannel.value)
    if (result.success) {
      message.value = `测试成功：${result.response_code}`
      messageType.value = 'success'
    } else {
      message.value = `测试失败：响应码 ${result.response_code}`
      messageType.value = 'error'
    }
    await loadCredentialInfo(selectedChannel.value)
  } catch (e: any) {
    message.value = e?.message || '测试请求失败'
    messageType.value = 'error'
  } finally {
    testing.value = false
  }
}

async function handleDelete() {
  if (!selectedChannel.value) return
  if (!confirm('确定要清除该渠道的所有凭证吗？')) return
  loading.value = true
  message.value = ''
  try {
    await deleteChannelCredentials(selectedChannel.value)
    message.value = '凭证已清除'
    messageType.value = 'success'
    await loadCredentialInfo(selectedChannel.value)
  } catch (e: any) {
    message.value = e?.message || '清除失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    active: '有效',
    expired: '已过期',
    invalid: '无效',
    sample: '格式样例',
    not_configured: '未配置',
    unknown: '未知',
  }
  return map[status] || status
}

function getStatusTone(status: string): 'success' | 'warning' | 'error' | 'muted' {
  const map: Record<string, 'success' | 'warning' | 'error' | 'muted'> = {
    active: 'success',
    expired: 'warning',
    invalid: 'error',
    sample: 'muted',
    not_configured: 'muted',
    unknown: 'muted',
  }
  return map[status] || 'muted'
}
</script>

<template>
  <div class="credential-tab">
    <div class="credential-header">
      <h3>凭证管理</h3>
      <div class="channel-selector">
        <label>选择渠道：</label>
        <select v-model="selectedChannel">
          <option value="">-- 选择渠道 --</option>
          <option v-for="ch in channels" :key="ch.id" :value="ch.code">
            {{ ch.name }} ({{ ch.code }})
          </option>
        </select>
      </div>
    </div>

    <div v-if="selectedChannel" class="credential-content">
      <div v-if="loading" class="loading">加载中...</div>

      <template v-else-if="credentialInfo">
        <div class="credential-status">
          <div class="status-item">
            <span class="label">Cookie 状态：</span>
            <StatusBadge
              :label="getStatusText(credentialInfo.cookie_status)"
              :tone="getStatusTone(credentialInfo.cookie_status)"
            />
            <span v-if="credentialInfo.cookie_preview" class="preview">{{ credentialInfo.cookie_preview }}</span>
          </div>
          <div class="status-item">
            <span class="label">最后更新：</span>
            <span>{{ credentialInfo.updated_at || '从未更新' }}</span>
            <span v-if="credentialInfo.updated_by" class="by">by {{ credentialInfo.updated_by }}</span>
          </div>
        </div>

        <div class="form-section">
          <div class="form-group">
            <label>Cookie 凭证</label>
            <textarea
              v-model="cookiesInput"
              placeholder="粘贴 Cookie 字符串，或输入 JSON 格式 {&quot;cookie&quot;: &quot;...&quot;, &quot;status&quot;: &quot;active&quot;}"
              rows="4"
            ></textarea>
            <p class="hint">输入完整的 Cookie 字符串，系统会自动保存</p>
          </div>

          <div class="form-group">
            <label>额外凭证 (JSON)</label>
            <textarea
              v-model="extraCredentialsInput"
              placeholder='例如：{"zhihu": {"zse_93": "101_3_3.0", "zse_96": "2.0_..."}}'
              rows="3"
            ></textarea>
            <p class="hint">仅知乎需要 zse_93 和 zse_96</p>
          </div>
        </div>

        <div class="message" :class="messageType" v-if="message">
          {{ message }}
        </div>

        <div class="action-buttons">
          <button class="btn-primary" @click="handleSave" :disabled="loading">
            保存凭证
          </button>
          <button class="btn-secondary" @click="handleTest" :disabled="testing || !credentialInfo.cookie_configured">
            {{ testing ? '测试中...' : '测试连接' }}
          </button>
          <button class="btn-danger" @click="handleDelete" :disabled="loading || !credentialInfo.cookie_configured">
            清除凭证
          </button>
        </div>
      </template>

      <div v-else class="empty-state">
        <p>请选择一个渠道查看凭证信息</p>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>请选择需要管理凭证的渠道</p>
      <p class="hint">目前支持微博、知乎、小红书的 Cookie 凭证管理</p>
    </div>
  </div>
</template>

<style scoped>
.credential-tab {
  padding: 0;
}

.credential-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.credential-header h3 {
  margin: 0;
  font-size: 15px;
}

.channel-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.channel-selector select {
  padding: 5px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  font-size: 13px;
}

.credential-content {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
}

.credential-status {
  background: #fff;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.status-item:last-child {
  margin-bottom: 0;
}

.status-item .label {
  font-weight: 500;
  color: var(--muted);
}

.status-item .preview {
  font-family: monospace;
  color: var(--subtle);
  font-size: 12px;
}

.status-item .by {
  color: var(--subtle);
  font-size: 12px;
}

.form-section {
  background: #fff;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
  color: var(--ink);
  font-size: 13px;
}

.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  resize: vertical;
  box-sizing: border-box;
}

.form-group textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.hint {
  margin: 4px 0 0;
  color: var(--subtle);
  font-size: 12px;
}

.message {
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}

.message.success {
  background: var(--success-soft);
  color: var(--success);
  border: 1px solid #e1f3d8;
}

.message.error {
  background: #fef0f0;
  color: var(--danger);
  border: 1px solid #fde2e2;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

button {
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #66b1ff;
}

.btn-secondary {
  background: #fff;
  color: var(--muted);
  border: 1px solid var(--line-strong);
}

.btn-secondary:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.btn-danger {
  background: var(--danger);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #f78989;
}

.loading {
  text-align: center;
  padding: 20px;
  color: var(--subtle);
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: var(--subtle);
  font-size: 13px;
}

.empty-state .hint {
  margin-top: 6px;
}
</style>
