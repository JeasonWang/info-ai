# Info Max

`Info Max` 是基于 `Vue 3 + TypeScript + Vite` 实现的前端应用，用于展示 `Info_aggregation` 后端提供的多渠道热点信息。

## 已实现能力

- 对接后端接口：`/api/categories`、`/api/channels`、`/api/infos`、`/api/infos/{id}`、`/api/stats`、`/api/crawl/trigger`
- 首页看板：统计卡片、筛选器、列表、时间线、渠道触发面板
- 详情页：正文展示、元数据展示、来源跳转
- 分页能力：支持服务端分页切换
- 内容格式化：支持普通文本、Markdown 风格文本、HTML 文本转可读内容、媒体链接识别
- 本地收藏：基于浏览器 `localStorage` 持久化收藏
- 分享能力：优先调用 Web Share API，降级为复制详情链接
- 骨架屏与异常态：列表、详情加载骨架，空态、失败态、重试入口
- 响应式布局：兼容桌面端与 H5 窄屏浏览
- 可扩展接口层与类型层：为后续迁移 `uni-app` 保留清晰边界

## 目录结构

```text
Info_max/
├── src/
│   ├── components/   # 统计、筛选、列表、时间线、详情渲染
│   ├── services/     # 后端 API 请求封装
│   ├── views/        # 页面级视图
│   ├── router.ts     # 路由
│   ├── styles.css    # 设计系统与响应式样式
│   ├── types.ts      # 类型定义
│   └── utils.ts      # 时间、内容、状态等工具方法
├── .env.example
└── package.json
```

## 启动方式

1. 启动后端 `Info_aggregation`，默认地址为 `http://localhost:8000`
2. 在 `Info_max/` 下安装依赖并启动前端

```bash
npm install
npm run dev
```

如需自定义后端地址，复制 `.env.example` 为 `.env` 后修改：

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Docker 与自动部署

- Dockerfile: `Dockerfile`
- Nginx 配置: `nginx.conf`
- 生产编排: `docker-compose.prod.yml`
- GitHub Actions: `.github/workflows/deploy.yml`
- Secrets 配置说明: `GITHUB_SECRETS_SETUP.md`

当前自动部署方式：

- GitHub Actions 构建镜像
- 导出为镜像 tar.gz 包
- 通过 SCP 上传到服务器
- 服务器执行 `docker load`
- 最后执行 `docker compose up -d`

基础命令：

```bash
docker build --build-arg VITE_API_BASE_URL=http://your-server-ip:8000 -t info-max:latest .
docker run -d --name info-max -p 80:80 info-max:latest
```

## 架构说明

- 页面层只负责状态组合和交互编排
- `services/api.ts` 统一处理接口请求
- `types.ts` 与后端返回结构一一对应，减少字段漂移风险
- 当前样式为 Web/H5 优先，后续如果要支持 `uni-app` 小程序，可以复用：
  - 数据类型
  - API 封装逻辑
  - 页面信息结构
  - 内容渲染策略
