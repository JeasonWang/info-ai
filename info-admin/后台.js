const serviceStatus = document.querySelector('#serviceStatus')
const loginButton = document.querySelector('#loginButton')

async function refreshServiceStatus() {
  try {
    const response = await fetch('http://localhost:8080/health')
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
  alert('登录弹窗将在接入 info-serve 鉴权 API 后启用。')
})

refreshServiceStatus()
