<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  createCategory,
  createChannel,
  getAdminCategories,
  getAdminChannels,
  updateCategory,
  updateChannel,
} from '@/services/api'
import type { Category, CategoryPayload, Channel, ChannelPayload } from '@/types'

const categories = ref<Category[]>([])
const channels = ref<Channel[]>([])
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')
const editingCategoryId = ref<number | null>(null)
const editingChannelId = ref<number | null>(null)

const categoryForm = reactive<CategoryPayload>({
  name: '',
  code: '',
  description: '',
})

const channelForm = reactive<ChannelPayload>({
  name: '',
  code: '',
  base_url: '',
  category_id: 0,
  crawl_interval: 60,
  is_active: 1,
})

const editCategoryForm = reactive<CategoryPayload>({
  name: '',
  code: '',
  description: '',
})

const editChannelForm = reactive<ChannelPayload>({
  name: '',
  code: '',
  base_url: '',
  category_id: 0,
  crawl_interval: 60,
  is_active: 1,
})

const hasCategoryOptions = computed(() => categories.value.length > 0)

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [categoryData, channelData] = await Promise.all([getAdminCategories(), getAdminChannels()])
    categories.value = categoryData
    channels.value = channelData
    if (!channelForm.category_id && categoryData.length > 0) {
      channelForm.category_id = categoryData[0].id
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载配置失败'
  } finally {
    loading.value = false
  }
}

function resetCategoryForm() {
  categoryForm.name = ''
  categoryForm.code = ''
  categoryForm.description = ''
}

function resetChannelForm() {
  channelForm.name = ''
  channelForm.code = ''
  channelForm.base_url = ''
  channelForm.crawl_interval = 60
  channelForm.is_active = 1
  if (categories.value.length > 0) {
    channelForm.category_id = categories.value[0].id
  }
}

async function handleCreateCategory() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await createCategory({ ...categoryForm })
    message.value = '分类已创建'
    resetCategoryForm()
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建分类失败'
  } finally {
    saving.value = false
  }
}

async function handleCreateChannel() {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await createChannel({ ...channelForm })
    message.value = '渠道已创建'
    resetChannelForm()
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建渠道失败'
  } finally {
    saving.value = false
  }
}

function startEditCategory(category: Category) {
  editingCategoryId.value = category.id
  editCategoryForm.name = category.name
  editCategoryForm.code = category.code
  editCategoryForm.description = category.description
}

function startEditChannel(channel: Channel) {
  editingChannelId.value = channel.id
  editChannelForm.name = channel.name
  editChannelForm.code = channel.code
  editChannelForm.base_url = channel.base_url
  editChannelForm.category_id = channel.category_id
  editChannelForm.crawl_interval = channel.crawl_interval
  editChannelForm.is_active = channel.is_active
}

async function handleUpdateCategory(id: number) {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await updateCategory(id, { ...editCategoryForm })
    message.value = '分类已更新'
    editingCategoryId.value = null
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '更新分类失败'
  } finally {
    saving.value = false
  }
}

async function handleUpdateChannel(id: number) {
  saving.value = true
  message.value = ''
  error.value = ''
  try {
    await updateChannel(id, { ...editChannelForm })
    message.value = '渠道已更新'
    editingChannelId.value = null
    await loadData()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '更新渠道失败'
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="settings-page">
    <div class="settings-page__top">
      <div>
        <p class="panel__eyebrow">Admin</p>
        <h1>配置管理</h1>
        <p class="panel__meta">管理分类和渠道配置，修改结果会直接影响前端筛选与定时爬取行为。</p>
      </div>
      <RouterLink class="button button--ghost" to="/">返回首页</RouterLink>
    </div>

    <p v-if="message" class="feedback">{{ message }}</p>
    <p v-if="error" class="error-banner">{{ error }}</p>

    <div v-if="loading" class="panel empty-state">正在加载配置...</div>
    <template v-else>
      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Category</p>
            <h2>新增分类</h2>
          </div>
        </div>

        <div class="settings-grid">
          <label class="field">
            <span>分类名称</span>
            <input v-model="categoryForm.name" type="text" placeholder="如：市场洞察" />
          </label>
          <label class="field">
            <span>分类编码</span>
            <input v-model="categoryForm.code" type="text" placeholder="如：market" />
          </label>
          <label class="field settings-grid__full">
            <span>分类描述</span>
            <input v-model="categoryForm.description" type="text" placeholder="用于前端展示说明" />
          </label>
        </div>

        <div class="info-card__actions">
          <button class="button button--primary" :disabled="saving" @click="handleCreateCategory">
            创建分类
          </button>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Category</p>
            <h2>分类列表</h2>
          </div>
        </div>
        <div class="card-stack">
          <article v-for="category in categories" :key="category.id" class="info-card">
            <template v-if="editingCategoryId === category.id">
              <div class="settings-grid">
                <label class="field">
                  <span>分类名称</span>
                  <input v-model="editCategoryForm.name" type="text" />
                </label>
                <label class="field">
                  <span>分类编码</span>
                  <input v-model="editCategoryForm.code" type="text" />
                </label>
                <label class="field settings-grid__full">
                  <span>分类描述</span>
                  <input v-model="editCategoryForm.description" type="text" />
                </label>
              </div>
              <div class="info-card__actions">
                <button class="button button--primary" :disabled="saving" @click="handleUpdateCategory(category.id)">
                  保存
                </button>
                <button class="button button--ghost" @click="editingCategoryId = null">取消</button>
              </div>
            </template>
            <template v-else>
              <h3>{{ category.name }}</h3>
              <p class="info-card__summary">编码：{{ category.code }}</p>
              <p class="info-card__summary">{{ category.description || '暂无描述' }}</p>
              <div class="info-card__actions">
                <button class="button button--ghost" @click="startEditCategory(category)">编辑</button>
              </div>
            </template>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Channel</p>
            <h2>新增渠道</h2>
          </div>
        </div>

        <div v-if="!hasCategoryOptions" class="empty-state">请先创建至少一个分类后再新增渠道。</div>
        <template v-else>
          <div class="settings-grid">
            <label class="field">
              <span>渠道名称</span>
              <input v-model="channelForm.name" type="text" placeholder="如：B站" />
            </label>
            <label class="field">
              <span>渠道编码</span>
              <input v-model="channelForm.code" type="text" placeholder="如：bilibili" />
            </label>
            <label class="field">
              <span>归属分类</span>
              <select v-model="channelForm.category_id">
                <option v-for="category in categories" :key="category.id" :value="category.id">
                  {{ category.name }}
                </option>
              </select>
            </label>
            <label class="field">
              <span>爬取间隔（分钟）</span>
              <input v-model.number="channelForm.crawl_interval" type="number" min="1" />
            </label>
            <label class="field settings-grid__full">
              <span>基础地址</span>
              <input v-model="channelForm.base_url" type="text" placeholder="https://example.com" />
            </label>
            <label class="field">
              <span>启用状态</span>
              <select v-model.number="channelForm.is_active">
                <option :value="1">启用</option>
                <option :value="0">停用</option>
              </select>
            </label>
          </div>

          <div class="info-card__actions">
            <button class="button button--primary" :disabled="saving" @click="handleCreateChannel">
              创建渠道
            </button>
          </div>
        </template>
      </section>

      <section class="panel">
        <div class="panel__header">
          <div>
            <p class="panel__eyebrow">Channel</p>
            <h2>渠道列表</h2>
          </div>
        </div>
        <div class="card-stack">
          <article v-for="channel in channels" :key="channel.id" class="info-card">
            <template v-if="editingChannelId === channel.id">
              <div class="settings-grid">
                <label class="field">
                  <span>渠道名称</span>
                  <input v-model="editChannelForm.name" type="text" />
                </label>
                <label class="field">
                  <span>渠道编码</span>
                  <input v-model="editChannelForm.code" type="text" />
                </label>
                <label class="field">
                  <span>归属分类</span>
                  <select v-model.number="editChannelForm.category_id">
                    <option v-for="category in categories" :key="category.id" :value="category.id">
                      {{ category.name }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span>爬取间隔</span>
                  <input v-model.number="editChannelForm.crawl_interval" type="number" min="1" />
                </label>
                <label class="field settings-grid__full">
                  <span>基础地址</span>
                  <input v-model="editChannelForm.base_url" type="text" />
                </label>
                <label class="field">
                  <span>启用状态</span>
                  <select v-model.number="editChannelForm.is_active">
                    <option :value="1">启用</option>
                    <option :value="0">停用</option>
                  </select>
                </label>
              </div>
              <div class="info-card__actions">
                <button class="button button--primary" :disabled="saving" @click="handleUpdateChannel(channel.id)">
                  保存
                </button>
                <button class="button button--ghost" @click="editingChannelId = null">取消</button>
              </div>
            </template>
            <template v-else>
              <h3>{{ channel.name }}</h3>
              <p class="info-card__summary">编码：{{ channel.code }} · 分类：{{ channel.category_name || channel.category_id }}</p>
              <p class="info-card__summary">{{ channel.base_url }}</p>
              <div class="info-card__meta">
                <span>间隔：{{ channel.crawl_interval }} 分钟</span>
                <span>{{ channel.is_active === 1 ? '已启用' : '已停用' }}</span>
              </div>
              <div class="info-card__actions">
                <button class="button button--ghost" @click="startEditChannel(channel)">编辑</button>
              </div>
            </template>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>
