const serviceStatus = document.querySelector('#serviceStatus')
const loginButton = document.querySelector('#loginButton')
const loginPanel = document.querySelector('#loginPanel')
const submitLoginButton = document.querySelector('#submitLoginButton')
const emailInput = document.querySelector('#emailInput')
const passwordInput = document.querySelector('#passwordInput')
const loginMessage = document.querySelector('#loginMessage')
const channelCount = document.querySelector('#channelCount')
const eventCount = document.querySelector('#eventCount')
const infoCount = document.querySelector('#infoCount')
const recentRunStatus = document.querySelector('#recentRunStatus')
const recentRunText = document.querySelector('#recentRunText')
const qualityStatus = document.querySelector('#qualityStatus')
const qualityText = document.querySelector('#qualityText')
const taskStatus = document.querySelector('#taskStatus')
const categoryStatus = document.querySelector('#categoryStatus')
const channelStatus = document.querySelector('#channelStatus')
const crawlRunList = document.querySelector('#crawlRunList')
const qualitySnapshotList = document.querySelector('#qualitySnapshotList')
const crawlTaskList = document.querySelector('#crawlTaskList')
const categoryList = document.querySelector('#categoryList')
const channelList = document.querySelector('#channelList')
const categoryForm = document.querySelector('#categoryForm')
const categoryNameInput = document.querySelector('#categoryNameInput')
const categoryCodeInput = document.querySelector('#categoryCodeInput')
const categoryDescriptionInput = document.querySelector('#categoryDescriptionInput')
const channelForm = document.querySelector('#channelForm')
const channelNameInput = document.querySelector('#channelNameInput')
const channelCodeInput = document.querySelector('#channelCodeInput')
const channelBaseURLInput = document.querySelector('#channelBaseURLInput')
const channelCategorySelect = document.querySelector('#channelCategorySelect')
const channelIntervalInput = document.querySelector('#channelIntervalInput')

const API_BASE_URL = 'http://localhost:8080'
const TOKEN_KEY = 'info-admin-token'
let cachedCategories = []

async function refreshServiceStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    serviceStatus.textContent = 'info-serve 已连接'
    serviceStatus.classList.add('online')
  } catch {
    serviceStatus.textContent = '等待连接 info-serve'
    serviceStatus.classList.remove('online')
  }
}

loginButton.addEventListener('click', () => {
  loginPanel.hidden = !loginPanel.hidden
})

submitLoginButton.addEventListener('click', async () => {
  loginMessage.textContent = '正在登录...'
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: emailInput.value,
        password: passwordInput.value,
      }),
    })
    const result = await response.json()
    if (!response.ok) {
      throw new Error(result.message || '登录失败')
    }
    localStorage.setItem(TOKEN_KEY, result.data.token)
    loginMessage.textContent = '登录成功，正在加载管理数据。'
    loginButton.textContent = result.data.user.email
    loginPanel.hidden = true
    await refreshOverview()
    await refreshMonitoringLists()
    await refreshConfiguration()
  } catch (error) {
    loginMessage.textContent = error.message
  }
})

categoryForm.addEventListener('submit', async (event) => {
  event.preventDefault()
  try {
    await submitAdminConfig('/api/admin/categories', {
      name: categoryNameInput.value,
      code: categoryCodeInput.value,
      description: categoryDescriptionInput.value,
    })
    categoryForm.reset()
    await refreshConfiguration()
  } catch (error) {
    loginMessage.textContent = error.message
  }
})

channelForm.addEventListener('submit', async (event) => {
  event.preventDefault()
  try {
    await submitAdminConfig('/api/admin/channels', {
      name: channelNameInput.value,
      code: channelCodeInput.value,
      base_url: channelBaseURLInput.value,
      category_id: Number(channelCategorySelect.value),
      crawl_interval: Number(channelIntervalInput.value),
      is_active: 1,
    })
    channelForm.reset()
    channelIntervalInput.value = '60'
    await refreshConfiguration()
  } catch (error) {
    loginMessage.textContent = error.message
  }
})

async function refreshOverview() {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) {
    return
  }
  const response = await fetch(`${API_BASE_URL}/api/admin/overview`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (response.status === 401 || response.status === 403) {
    localStorage.removeItem(TOKEN_KEY)
    loginButton.textContent = '管理员登录'
    return
  }
  if (!response.ok) {
    throw new Error(`管理总览加载失败：${response.status}`)
  }
  const result = await response.json()
  renderOverview(result.data)
}

async function refreshMonitoringLists() {
  const [runs, snapshots, tasks] = await Promise.all([
    fetchAdminList('/api/admin/crawl-runs?limit=6'),
    fetchAdminList('/api/admin/quality-snapshots?limit=6'),
    fetchAdminList('/api/admin/crawl-tasks'),
  ])
  renderCrawlRuns(runs)
  renderQualitySnapshots(snapshots)
  renderCrawlTasks(tasks)
}

async function refreshConfiguration() {
  const [categories, channels] = await Promise.all([
    fetchAdminList('/api/admin/categories'),
    fetchAdminList('/api/admin/channels'),
  ])
  cachedCategories = categories
  renderCategories(categories)
  renderChannelCategoryOptions(categories)
  renderChannels(channels)
}

async function fetchAdminList(path) {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) {
    return []
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    return []
  }
  const result = await response.json()
  return result.data || []
}

async function submitAdminConfig(path, payload) {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) {
    loginMessage.textContent = '请先登录管理员账号。'
    return
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  const result = await response.json()
  if (!response.ok) {
    throw new Error(result.message || '配置保存失败')
  }
  loginMessage.textContent = '配置已保存。'
  return result.data
}

function renderOverview(data) {
  channelCount.textContent = data.channel_count
  eventCount.textContent = data.event_count
  infoCount.textContent = data.info_count

  const recentRun = data.recent_runs?.[0]
  if (recentRun) {
    recentRunStatus.textContent = recentRun.status
    recentRunText.textContent = `${recentRun.channel_code} 最近采集入库 ${recentRun.saved_count} 条，详情成功 ${recentRun.detail_success_count} 条。`
  } else {
    recentRunStatus.textContent = '暂无运行日志'
    recentRunText.textContent = '采集运行日志表已就绪，后续调度器写入后将在这里展示。'
  }

  qualityStatus.textContent = '已接入'
  qualityText.textContent = `重复标题 ${data.quality.duplicate_title_count} 条，正文缺失 ${data.quality.empty_content_count} 条，实体缺失 ${data.quality.missing_entity_count} 条，低详情评分 ${data.quality.low_detail_score_count} 条。`
}

function renderCrawlRuns(items) {
  crawlRunList.innerHTML = ''
  if (!items.length) {
    crawlRunList.appendChild(listItem('暂无采集运行日志', '等待调度器写入'))
    return
  }
  items.forEach((item) => {
    crawlRunList.appendChild(
      listItem(`${item.channel_code} · ${item.status}`, `入库 ${item.saved_count} / 详情失败 ${item.detail_failed_count}`)
    )
  })
}

function renderQualitySnapshots(items) {
  qualitySnapshotList.innerHTML = ''
  if (!items.length) {
    qualitySnapshotList.appendChild(listItem('暂无质量快照', '等待质量任务写入'))
    return
  }
  items.forEach((item) => {
    qualitySnapshotList.appendChild(
      listItem(`${item.category_code} · ${item.total_count} 条`, `重复 ${item.duplicate_title_count} / 缺正文 ${item.empty_content_count}`)
    )
  })
}

function renderCrawlTasks(items) {
  crawlTaskList.innerHTML = ''
  taskStatus.textContent = items.length ? `${items.length} 个任务` : '暂无任务'
  if (!items.length) {
    crawlTaskList.appendChild(listItem('暂无采集任务', '后续由调度器注册'))
    return
  }
  items.forEach((item) => {
    crawlTaskList.appendChild(listItem(`${item.task_name}`, `${item.channel_name} · ${item.status}`))
  })
}

function renderCategories(items) {
  categoryList.innerHTML = ''
  categoryStatus.textContent = items.length ? `${items.length} 个分类` : '暂无分类'
  if (!items.length) {
    categoryList.appendChild(listItem('暂无分类', '请先创建分类，再添加渠道'))
    return
  }
  items.forEach((item) => {
    categoryList.appendChild(listItem(`${item.name} · ${item.code}`, item.description || '暂无说明'))
  })
}

function renderChannelCategoryOptions(items) {
  channelCategorySelect.innerHTML = ''
  if (!items.length) {
    const option = document.createElement('option')
    option.value = ''
    option.textContent = '请先创建分类'
    channelCategorySelect.appendChild(option)
    return
  }
  items.forEach((item) => {
    const option = document.createElement('option')
    option.value = item.id
    option.textContent = item.name
    channelCategorySelect.appendChild(option)
  })
}

function renderChannels(items) {
  channelList.innerHTML = ''
  channelStatus.textContent = items.length ? `${items.length} 个渠道` : '暂无渠道'
  if (!items.length) {
    channelList.appendChild(listItem('暂无渠道', '新增渠道后，采集任务可绑定这些数据源'))
    return
  }
  items.forEach((item) => {
    const category = item.category_name || cachedCategories.find((categoryItem) => categoryItem.id === item.category_id)?.name || '未分类'
    const state = item.is_active === 1 ? '启用' : '停用'
    channelList.appendChild(listItem(`${item.name} · ${item.code}`, `${category} · ${state} · ${item.crawl_interval} 分钟`))
  })
}

function listItem(title, meta) {
  const item = document.createElement('li')
  const strong = document.createElement('strong')
  const span = document.createElement('span')
  strong.textContent = title
  span.textContent = meta
  item.append(strong, span)
  return item
}

refreshServiceStatus()
refreshOverview()
refreshMonitoringLists()
refreshConfiguration()
