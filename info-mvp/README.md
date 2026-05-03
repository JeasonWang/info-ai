# info-mvp

InfoMVP 是 info-max 的 uni-app 重构版本，一套代码同时编译到 **H5** 和 **微信小程序**。

## 技术栈

- uni-app Vue3 + Vite
- TypeScript 5.x
- Pinia 状态管理
- uni-ui 组件库

## 本地开发

### 前置条件

- Node.js 22+
- 已启动的后端服务（info-serve on :8080）

### 安装依赖

```bash
cd info-mvp
npm install
```

### 启动 H5 开发服务器

```bash
npm run dev:h5
# 或复用后端地址
VITE_API_BASE_URL=http://localhost:8080/api npm run dev:h5
```

### 启动微信小程序开发

```bash
npm run dev:mp-weixin
```

编译完成后，用**微信开发者工具**打开 `dist/build/mp-weixin` 目录。

### 一键启动（整合脚本）

```bash
# 从项目根目录
./scripts/start-mvp-local.sh
```

## 构建

### H5 生产构建

```bash
npm run build:h5
# 产物在 dist/build/h5/
```

### 微信小程序生产构建

```bash
npm run build:mp-weixin
# 产物在 dist/build/mp-weixin/
# 用微信开发者工具上传
```

## Docker 部署

### 构建镜像

```bash
cd info-mvp
docker build -t info-ai-info-mvp:pro .
```

### 独立部署（复用现有后端）

```bash
# 从项目根目录
docker compose -f docker-compose.mvp.yml up -d --build info-mvp
```

### 替换 info-max 部署

修改根目录 `docker-compose.yml`，将 `info-max` 服务替换为 `info-mvp`：

```yaml
  info-mvp:
    image: info-ai-info-mvp:pro
    build:
      context: ./info-mvp
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: ${VITE_INFO_SERVE_BASE_URL:-http://127.0.0.1:8080}/api
    container_name: info-mvp
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - info-serve
```

## 项目结构

```
src/
  pages/           # 页面
    home/          # 首页（事件列表）
    event-detail/  # 事件详情
    info-detail/   # 资讯详情
    login/         # 登录/注册
    favorites/     # 我的收藏
    history/       # 阅读历史
  components/      # 业务组件
  composables/     # 组合式逻辑
  stores/          # Pinia Store
  services/        # API 层
  types/           # TypeScript 类型
  utils/           # 工具函数
```

## 环境变量

| 变量 | 开发默认值 | 说明 |
|------|-----------|------|
| `VITE_API_BASE_URL` | `/api` | 后端 API 基地址 |

## 多端兼容

- **H5**：标准 Vue 3 行为，`v-html` 渲染富文本，浏览器原生分享
- **微信小程序**：`rich-text` 渲染内容，`uni.setClipboardData` 复制链接，`onShareAppMessage` 分享卡片

## 与 info-max 的差异

| 特性 | info-max (Vue SPA) | info-mvp (uni-app) |
|------|-------------------|-------------------|
| 路由 | Vue Router | pages.json |
| HTTP | fetch | uni.request |
| 存储 | localStorage | uni Storage |
| 构建产物 | 纯静态文件 | H5 静态文件 + 小程序代码 |
| 登录态 | 手动管理 | Pinia + 拦截器自动注入 |
| 滚动加载 | IntersectionObserver | onReachBottom |
