<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import DataPanel from '@/components/DataPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import { createCategory, getCategories } from '@/services/adminApi'
import type { AdminCategory } from '@/types/admin'

const categories = ref<AdminCategory[]>([])
const form = reactive({ name: '', code: '', description: '' })
const message = ref('')

async function refreshCategories() {
  categories.value = await getCategories()
}

async function submitCategory() {
  await createCategory({ ...form })
  form.name = ''
  form.code = ''
  form.description = ''
  message.value = '分类已保存'
  await refreshCategories()
}

onMounted(refreshCategories)
</script>

<template>
  <DataPanel title="分类管理" :status="`${categories.length} 个分类`">
    <form class="inline-form" @submit.prevent="submitCategory">
      <input v-model="form.name" required placeholder="分类名称，例如 体育" />
      <input v-model="form.code" required placeholder="分类编码，例如 sports" />
      <input v-model="form.description" placeholder="分类说明" />
      <button type="submit">新增分类</button>
    </form>
    <p class="form-message">{{ message }}</p>

    <ul v-if="categories.length" class="data-list">
      <li v-for="item in categories" :key="item.id">
        <strong>{{ item.name }} · {{ item.code }}</strong>
        <span>{{ item.description || '暂无说明' }}</span>
      </li>
    </ul>
    <EmptyState v-else title="暂无分类" description="请先创建分类，再添加渠道。" />
  </DataPanel>
</template>
