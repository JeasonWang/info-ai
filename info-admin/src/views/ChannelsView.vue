<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { createChannel, getCategories, getChannels } from '@/services/adminApi'
import type { AdminCategory, AdminChannel } from '@/types/admin'

const categories = ref<AdminCategory[]>([])
const channels = ref<AdminChannel[]>([])
const form = reactive({
  name: '',
  code: '',
  base_url: '',
  category_id: 0,
  crawl_interval: 60,
  is_active: 1,
})
const message = ref('')

async function refreshData() {
  const [categoryItems, channelItems] = await Promise.all([getCategories(), getChannels()])
  categories.value = categoryItems
  channels.value = channelItems
  if (!form.category_id && categoryItems[0]) {
    form.category_id = categoryItems[0].id
  }
}

async function submitChannel() {
  await createChannel({ ...form })
  form.name = ''
  form.code = ''
  form.base_url = ''
  form.crawl_interval = 60
  message.value = '渠道已保存'
  await refreshData()
}

onMounted(refreshData)
</script>

<template>
  <DataPanel title="渠道管理" :status="`${channels.length} 个渠道`">
    <form class="inline-form channel-form" @submit.prevent="submitChannel">
      <input v-model="form.name" required placeholder="渠道名称，例如 新浪体育" />
      <input v-model="form.code" required placeholder="渠道编码，例如 sina_sports" />
      <input v-model="form.base_url" placeholder="渠道首页 URL" />
      <select v-model.number="form.category_id" required>
        <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select>
      <input v-model.number="form.crawl_interval" required type="number" min="1" placeholder="采集间隔" />
      <button type="submit">新增渠道</button>
    </form>
    <p class="form-message">{{ message }}</p>

    <ul v-if="channels.length" class="data-list">
      <li v-for="item in channels" :key="item.id">
        <strong>{{ item.name }} · {{ item.code }}</strong>
        <span>{{ item.category_name }} · {{ item.crawl_interval }} 分钟</span>
        <StatusBadge :label="item.is_active === 1 ? '启用' : '停用'" :tone="item.is_active === 1 ? 'success' : 'muted'" />
      </li>
    </ul>
    <EmptyState v-else title="暂无渠道" description="新增渠道后，采集任务可以绑定这些数据源。" />
  </DataPanel>
</template>
