# info-max 工程 Review 总结

## 1. 工程定位

**info-max** 是整个 info-ai 体系的**主站 Web 前端**，面向 C 端用户提供"热点事件聚合"的浏览体验。用户可在此查看多源聚合的事件列表、阅读事件详情（时间线、多方视角、相关报道）、管理收藏与阅读历史。

核心页面：
- 首页：事件列表 + 分类/渠道/排序筛选 + 搜索
- 事件详情：时间线、多方视角摘要、相关报道、科技标签
- 内容详情：单条原始信息的详情页
- 登录/注册：JWT 认证
- 收藏夹与阅读历史：用户个人数据

---

## 2. 系统架构

### 2.1 技术栈
- **Framework**: Vue 3.5 + Composition API + `<script setup>`
- **Router**: Vue Router 4（history 模式）
- **Build Tool**: Vite 6
- **Language**: TypeScript
- **Testing**: Vitest + happy-dom + @vue/test-utils
- **State Management**: 无 Pinia/Vuex，使用 `localStorage` + 自定义事件通信
- **HTTP Client**: 原生 `fetch` 封装
- **UI Library**: 无（纯手写 CSS）

### 2.2 模块结构
```
info-max/src/
├── views/              # 页面级组件
│   ├── HomeView.vue    # 首页（事件列表+筛选）
│   ├── EventDetailView.vue  # 事件详情
│   ├── InfoDetailView.vue   # 内容详情
│   ├── LoginView.vue   # 登录
│   ├── FavoriteEventsView.vue
│   └── ReadHistoryView.vue
├── components/         # 可复用组件
│   ├── EventList.vue
│   ├── EventCategoryTabs.vue
│   ├── EventTimeline.vue
│   ├── FilterBar.vue   # 筛选面板（分类+渠道+搜索）
│   ├── SkeletonBlock.vue
│   └── FavoriteButton.vue
├── services/           # API 与数据持久化
│   ├── api.ts          # fetch 封装 + 业务 API
│   ├── userSession.ts  # 用户状态管理
│   └── homeFilterMemory.ts  # 首页筛选本地缓存
├── composables/        # 组合式函数
│   └── useEventFavorites.ts
├── router.ts           # 路由配置
├── types.ts            # 全局类型定义
└── styles.css          # 全局样式
```

### 2.3 架构评价
**优点**：
- Vue 3 Composition API 使用规范，`<script setup>` 语法现代
- 组件拆分粒度适中，EventList/EventTimeline 等组件职责单一
- 路由懒加载 + 滚动恢复行为设计合理
- 测试覆盖较好（HomeView/EventDetailView/LoginView 均有测试）
- `fetch` 封装简洁，无过度抽象

**问题**：
- **无全局状态管理**：用户信息、收藏状态通过 `localStorage` + 自定义事件传递，跨组件通信脆弱
- **无 UI 组件库**：所有样式手写，开发效率低，且视觉一致性难以长期保持
- **缺少错误边界**：页面级错误（如 API 500）直接抛出，未做全局降级处理
- **无请求防抖/节流**：搜索输入直接触发请求，高频输入时产生大量无效请求

---

## 3. 代码逻辑

### 3.1 首页 (`HomeView.vue`)
- 数据加载逻辑清晰：`loadCategories → loadChannels → restorePreference → loadEvents`
- 分页采用 IntersectionObserver 实现无限滚动，体验流畅
- 筛选条件（分类、渠道、排序）本地持久化 + 服务端同步（登录后）
- **问题**：`loadChannels` 失败后未降级，会导致页面白屏（虽已修复 try-catch）

### 3.2 事件详情 (`EventDetailView.vue`)
- 时间线去重逻辑较细致（`isRedundantText`）
- "多方视角"直接展示后端返回的 `summaries` map，未做标签映射（`what_happened` → "发生了什么" 等映射缺失）
- 阅读历史记录异步发送（`recordReadHistory`），但无重试机制

### 3.3 收藏功能 (`useEventFavorites.ts`)
- 使用 composable 封装收藏逻辑，复用性好
- 但收藏状态仅在前端内存维护，页面刷新后需重新同步

### 3.4 样式架构 (`styles.css`)
- CSS 变量设计完整（色彩、间距、圆角、阴影、字体）
- BEM 命名规范（`.home-filter-panel__item--active`）
- 但缺少 Dark Mode 支持、响应式断点不统一

---

## 4. 页面布局与视觉

### 4.1 布局特点
- 采用"紧凑卡片式"布局，信息密度高
- 顶部固定用户导航栏（品牌 + 账号操作）
- 筛选面板可展开/收起，节省首屏空间

### 4.2 色彩系统
- 主色：蓝色（`#2563eb`）用于品牌、按钮、高亮
- 背景：浅灰（`#f7f8fa`）+ 纯白卡片
- 文字：四级灰度（`#1d2129` → `#86909c`）
- 分类色带：蓝、紫、青、橙、玫红（左侧 4px 色条区分分类）

### 4.3 UI 问题
- **品牌名不一致**：代码中混用 "Info Daren"、"InfoMVP"、"热点事件"，品牌认知混乱
- **移动端适配不足**：纯 PC Web 设计，小屏体验差（但当前定位就是 PC 主站，可接受）
- **Loading 状态单一**：仅骨架屏，无局部刷新 loading
- **空状态设计粗糙**："当前还没有可展示的热点事件" 文案生硬

---

## 5. 产品定位分析

info-max 的定位是**"信息聚合主站"**，面向重度信息消费者（科技从业者、投资人、媒体人）。

**当前匹配度**：
- 事件聚合 + 多源视角：匹配目标用户需求
- 时间线展示：对热点追踪有价值
- 科技标签（实体/关键词）：差异化亮点

**缺失的产品能力**：
- 无推荐算法（仅靠综合分排序）
- 无用户画像/个性化 feed
- 无分享功能（微信/微博分享卡片）
- 无推送/订阅机制
- 无评论/讨论区（社区氛围缺失）

---

## 6. 问题汇总与优化方向

### 6.1 高优先级（近期）

| 问题 | 影响 | 优化方向 |
|------|------|----------|
| 无全局状态管理 | 跨组件通信脆弱、代码重复 | 引入 Pinia，统一用户/收藏/历史状态 |
| 品牌名混乱 | 用户认知混乱、产品不专业 | 统一品牌名称为 "热点事件" 或 "Info Daren"，全量替换 |
| 搜索无防抖 | 高频无效请求、性能浪费 | 输入框增加 300ms debounce |
| 多方视角标签未映射 | 用户看到 `what_happened` 等英文 key | 增加 summary type 中文映射表 |
| 无错误边界 | 单个组件错误导致整页崩溃 | 增加 `onErrorCaptured` 或全局错误降级页 |

### 6.2 中优先级（中期）

| 问题 | 影响 | 优化方向 |
|------|------|----------|
| 纯手写 CSS 效率低 | 新页面开发慢、样式易冲突 | 引入轻量 UI 库（如 Tailwind CSS 或 UnoCSS） |
| 无响应式设计 | 移动端体验差 | 增加移动端断点适配（或专注 PC，明确产品边界） |
| 缺少分享功能 | 传播裂变能力为零 | 增加 Web Share API + 复制链接 + 二维码 |
| 无个性化推荐 | 用户留存低 | 基于阅读历史的协同过滤（或简单规则推荐） |
| 空状态/错误状态粗糙 | 用户体验断层 | 设计情感化空状态插图和友好错误文案 |

### 6.3 低优先级（长期）

| 问题 | 影响 | 优化方向 |
|------|------|----------|
| 无 SSR/SSG | SEO 差、首屏慢 | Nuxt 3 迁移或接入 SSG |
| 无 PWA 能力 | 无法离线浏览、无法添加到桌面 | 接入 Vite PWA 插件 |
| 无埋点分析 | 无法量化用户行为 | 接入 Google Analytics 或自建埋点 |
| 无暗黑模式 | 夜间阅读体验差 | CSS 变量支持 `prefers-color-scheme` |

---

## 7. 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | 6.5/10 | Vue3 使用规范，但缺少状态管理和错误边界 |
| 代码质量 | 7/10 | 测试覆盖好，逻辑清晰，但搜索无防抖 |
| UI/UX 设计 | 6/10 | 色彩系统完整，但品牌混乱、空状态粗糙 |
| 性能优化 | 5.5/10 | 无限滚动好，但无缓存、无防抖、无懒加载优化 |
| 产品匹配 | 6.5/10 | 核心功能具备，但缺少推荐、分享、社区 |

**一句话总结**：info-max 是一个"技术实现扎实、但产品化不足"的 Vue3 主站，当务之急是**统一品牌**、**引入 Pinia**、**补齐搜索防抖和错误边界**，中长期需考虑**个性化推荐**和**社交裂变**能力。
