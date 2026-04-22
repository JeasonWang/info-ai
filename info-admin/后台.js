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

const API_BASE_URL = 'http://localhost:8080'
const TOKEN_KEY = 'info-admin-token'

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

refreshServiceStatus()
refreshOverview()
