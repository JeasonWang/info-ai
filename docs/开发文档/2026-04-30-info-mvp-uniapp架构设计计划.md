# info-mvp 架构设计计划

> 目标：将 info-max（Vue 3 SPA）重构为 uni-app（Vue 3 + Vite）项目，一套代码同时输出 H5 和微信小程序。后端 info-serve 零改动。

---

## 一、项目背景与目标

### 1.1 现状
- info-max：Vue 3 + Vite + 手写 CSS，仅 H5，约 5,000 行代码，5 个页面
- info-serve：Go 后端，REST API，JWT 认证，MySQL

### 1.2 目标
- 新建工程 `info-mvp/`，与 `info-max/` 并行存在
- 复用后端 API（info-serve 不做任何改动）
- 编译产物同时支持：
  - H5（替换现有 info-max 的移动端访问）
  - 微信小程序（原生体验，支持分享、订阅消息等扩展）

---

## 二、技术选型

| 层级 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 框架 | uni-app | 3.0+ (Vue3/Vite) | 一套代码编译多端，Vue 3 Composition API 直接复用 |
| 语言 | TypeScript | 5.x | 与 info-max 保持一致，类型复用 |
| UI 组件 | uni-ui | 最新 | 官方组件库，小程序+H5 双端已验证兼容 |
| 状态管理 | Pinia | 2.x | Vue 3 官方推荐，devtools 支持好，类型友好 |
| HTTP | uni.request 封装 | - | uni-app 统一 API，H5 底层自动映射 fetch/XHR |
| 构建工具 | Vite | 5.x+ | uni-app Vue3 模式默认使用，与 info-max 一致 |
| CSS 预处理器 | 无（原生 CSS） | - | 减少构建体积，保持简单；若后期需要再引入 SCSS |

### 不引入的库（控制包体积）
- ~~Vue Router~~ → uni-app 用 `pages.json`
- ~~Axios~~ → `uni.request` 足够
- ~~第三方 UI 库（Vant、uView）~~ → 用 uni-ui
- ~~Day.js / Moment~~ → 简单日期用原生 `Intl.DateTimeFormat`

---

## 三、工程目录结构

```
info-mvp/
├── src/
│   ├── pages/
│   │   ├── home/
│   │   │   └── home.vue           # 首页（事件/信息聚合）
│   │   ├── info-detail/
│   │   │   └── info-detail.vue    # 信息详情
│   │   ├── event-detail/
│   │   │   └── event-detail.vue   # 事件详情
│   │   ├── login/
│   │   │   └── login.vue          # 登录页
│   │   ├── favorites/
│   │   │   └── favorites.vue      # 收藏列表
│   │   └── history/
│   │       └── history.vue        # 阅读历史
│   ├── components/
│   │   ├── EventList.vue
│   │   ├── EventCategoryTabs.vue
│   │   ├── FilterBar.vue
│   │   ├── InfoList.vue
│   │   ├── DetailContent.vue
│   │   ├── SkeletonBlock.vue
│   │   ├── PaginationBar.vue       # H5 用分页，小程序也用分页（无限滚动备选）
│   │   ├── FavoriteButton.vue
│   │   └── StatCards.vue
│   ├── composables/
│   │   ├── useAuth.ts              # 登录状态 + Token 管理
│   │   ├── useListLoad.ts          # 列表分页/加载更多逻辑（通用）
│   │   ├── useFilterMemory.ts      # 筛选状态持久化
│   │   └── usePlatform.ts          # 平台判断（H5 / MP-WEIXIN）
│   ├── stores/
│   │   ├── user.ts                 # 用户 Store（Pinia）
│   │   └── home.ts                 # 首页筛选/状态 Store
│   ├── services/
│   │   ├── api.ts                  # 业务 API 函数（复用 info-max 逻辑）
│   │   └── request.ts              # uni.request 封装（拦截器、错误处理）
│   ├── types/
│   │   └── index.ts                # 从 info-max 复制并微调
│   ├── utils/
│   │   ├── platform.ts             # isH5 / isWeixinMP
│   │   ├── storage.ts              # 封装 uni Storage，H5 也走 uni API
│   │   └── format.ts               # 日期、数字格式化
│   ├── static/
│   │   └── images/
│   ├── App.vue
│   ├── main.ts
│   ├── manifest.json               # 各端配置（小程序 AppID、H5 路由模式等）
│   └── pages.json                  # 页面路由 + 导航栏 + TabBar 配置
├── .env                            # H5 默认环境变量
├── .env.production
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

---

## 四、与原 info-max 的复用对照表

| info-max 文件 | info-mvp 复用策略 | 备注 |
|---------------|-------------------|------|
| `src/types.ts` | **100% 复用** → `src/types/index.ts` | 类型定义多端通用 |
| `src/services/api.ts` | **逻辑复用，API 替换** | 函数签名不变，内部 `fetch` → `request.ts` 封装 |
| `src/services/homeFilterMemory.ts` | **逻辑复用** → `composables/useFilterMemory.ts` | storage 走 `utils/storage.ts` |
| `src/services/userSession.ts` | **逻辑复用** → `composables/useAuth.ts` + `stores/user.ts` | 引入 Pinia 管理登录态 |
| `src/views/HomeView.vue` | **逻辑复用，模板重写** | `ref/computed/onMounted` 逻辑保留，`<template>` 改为 uni 组件 |
| `src/views/InfoDetailView.vue` | **逻辑复用，模板重写** | 富文本渲染改用 `rich-text`（小程序）/ `v-html`（H5 条件编译） |
| `src/components/*.vue` | **全部重写** | 小程序组件标签与 H5 不同，必须用 uni-ui 或原生标签 |
| `src/router.ts` | **废弃** | 改为 `pages.json` |
| `src/styles.css` | **重写** | uni-app 有全局样式配置，单位改为 rpx |

---

## 五、关键模块设计

### 5.1 网络请求层（src/services/request.ts）

设计目标：
- 统一用 `uni.request`
- H5 和小程序 Token 存储方式不同，但读取逻辑统一
- 401 自动跳转登录

```typescript
// 伪代码示意
function request<T>(config: UniApp.RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      ...config,
      header: {
        ...config.header,
        Authorization: `Bearer ${getToken()}`,
      },
      success: (res) => {
        if (res.statusCode === 401) {
          clearToken()
          redirectToLogin()
          reject(new Error('Unauthorized'))
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else {
          reject(new Error(res.data?.message || 'Request failed'))
        }
      },
      fail: reject,
    })
  })
}
```

### 5.2 登录策略（多端差异点）

| 平台 | 触发方式 | Token 存储 | 后端接口 |
|------|----------|------------|----------|
| H5 | 邮箱 + 密码 表单 | `uni.setStorageSync('token', xxx)` | `POST /api/v1/auth/login` |
| 微信小程序 | 点击 "微信登录" 按钮 → `uni.login` 获取 code | 同上 | `POST /api/v1/auth/wx-login`（预留，本期不实现） |

**本期范围**：H5 和小程序都先走邮箱密码登录（小程序端也展示表单）。微信一键登录作为预留扩展。

### 5.3 列表加载策略

统一采用**分页加载**（而非无限滚动）：
- 原因：uni-app `onReachBottom` 在 scroll-view 内不生效，且分页对两端更稳定
- 交互：底部 "加载更多" 按钮或自动触发，配合 `PaginationBar.vue`

`useListLoad.ts` 封装通用逻辑：
```typescript
function useListLoad<T>(fetcher: (page: number) => Promise<T[]>) {
  const list = ref<T[]>([])
  const page = ref(1)
  const loading = ref(false)
  const hasMore = ref(true)
  async function loadMore() { ... }
  return { list, loading, hasMore, loadMore, refresh }
}
```

### 5.4 富文本渲染策略

info-detail 和 event-detail 需要展示 HTML 内容。

- **H5 端**：条件编译使用 `v-html`
- **小程序端**：条件编译使用 `<rich-text>` 组件
- 若 `rich-text` 无法满足（如图片点击预览），考虑引入 `mp-html` 插件（轻量，50KB 左右）

```vue
<!-- #ifdef H5 -->
<div v-html="sanitizedHtml"></div>
<!-- #endif -->

<!-- #ifdef MP-WEIXIN -->
<rich-text :nodes="sanitizedHtml"></rich-text>
<!-- #endif -->
```

### 5.5 分享策略

- **H5**：浏览器原生分享（不干预）
- **小程序**：重写 `onShareAppMessage`，分享卡片带当前页面路径

---

## 六、开发阶段与里程碑

### Phase 0：工程基建（1 天）✅
- [x] 使用 `npx degit dcloudio/uni-preset-vue#vite` 创建 Vue3/Vite 模板
- [x] 配置 `manifest.json`（H5 + 微信小程序）
- [x] 配置 `pages.json` 路由
- [x] 安装依赖：pinia、uni-ui
- [x] 配置 `request.ts` 基座
- [x] 配置 `vite.config.ts` 代理（开发时转发到本地 info-serve:8080）
- [x] 验证：H5 编译通过 + 微信小程序编译通过

### Phase 1：首页 + 列表（2 天）✅
- [x] 复制 `types.ts`，微调
- [x] 迁移 `api.ts` 接口（首页相关：categories、events、infos、stats）
- [x] 实现 `home.vue`（事件分类 Tabs + 列表 + 筛选 + 用户入口栏 + 回到顶部）
- [x] 实现 `EventList.vue`、`EventCategoryTabs.vue`、`FilterBar.vue`
- [x] 实现 `useListLoad.ts` 通用加载逻辑
- [x] 实现 `SkeletonBlock.vue`
- [x] H5 + 小程序双端编译通过

### Phase 2：详情页（2 天）✅
- [x] `info-detail.vue`（信息详情 + 富文本条件编译 + 原文链接）
- [x] `event-detail.vue`（事件详情 + 时间线 + 多方视角 + 相关报道）
- [x] 收藏按钮 `FavoriteButton.vue` + `useFavorite.ts`
- [x] 阅读历史记录（调用 `recordReadHistory`）

### Phase 3：用户中心（1.5 天）✅
- [x] `login.vue` 登录页（邮箱 + 密码 + 表单校验）
- [x] `useAuth.ts` + `stores/user.ts`（Pinia 管理登录态）
- [x] `favorites.vue` 收藏列表（骨架屏 + 空状态 + 确认取消）
- [x] `history.vue` 阅读历史（骨架屏 + 空状态）
- [x] Token 过期自动跳转登录（401 防重跳锁）
- [x] 收藏/历史页面登录守卫

### Phase 4：多端适配与优化（1.5 天）✅
- [x] 微信小程序：`onShareAppMessage`（首页、详情页、事件页）
- [x] 微信小程序：`onShareTimeline`（首页）
- [x] 微信小程序：`lazyCodeLoading: requiredComponents` 性能优化
- [x] H5：`pages.json` hash 模式验证
- [x] App.vue 全局 CSS 变量规范

### Phase 5：测试与部署（1 天）✅
- [x] H5 构建产物（300KB，Nginx Docker 镜像 50MB）
- [x] 微信小程序构建产物（308KB，60 个文件）
- [x] 包体积远低于 2MB 限制
- [x] `Dockerfile` + `nginx.conf` + `docker-compose.mvp.yml`
- [x] 本地开发脚本 `scripts/start-mvp-local.sh`
- [x] `README.md` 部署文档

**总计工期：约 9 个工作日（2 周）**

---

## 七、环境变量配置

```bash
# .env（开发）
VITE_API_BASE_URL=http://localhost:8080

# .env.production（生产）
VITE_API_BASE_URL=https://api.yourdomain.com
```

---

## 八、后端兼容性说明

本期 info-serve **零改动**。但需注意：

1. **H5 跨域**：开发时 Vite 代理解决；生产时 Nginx 或后端已配置 CORS
2. **小程序合法域名**：上线前需在小程序后台配置 `request` 合法域名（必须是 HTTPS）
3. **微信登录扩展**：后续若接入微信登录，后端需新增 `/api/v1/auth/wx-login`，接受 `code` 返回 `openid` + JWT

---

## 九、风险与回退方案

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| `rich-text` 无法渲染复杂 HTML | 详情页展示异常 | 引入 `mp-html` 插件作为兜底 |
| 小程序包体积超限 | 无法上传 | 启用分包加载；图片挪到 CDN；按需引入 uni-ui |
| uni-ui 某组件 H5 表现不一致 | UI 走查不过 | 条件编译，H5 端用原生 HTML 标签替换 |
| 后端 API 响应慢导致小程序体验差 | 用户流失 | 增加前端缓存（Storage 缓存列表 60s） |

---

## 十、验收标准

- [ ] H5 端：功能与现有 info-max 完全一致，视觉不降级
- [ ] 小程序端：首页、详情、登录、收藏、历史 5 大功能可用
- [ ] 小程序包体积 < 2MB（主包 < 1.5MB）
- [ ] 列表页滚动流畅，无白屏、无内存泄漏
- [ ] 登录态持久化，Token 过期自动跳转

---

**文档版本**: v1.0
**日期**: 2026-04-30
**作者**: Claude Code
