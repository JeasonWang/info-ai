# 信息达人事件关键词搜索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为首页事件流补齐“当前频道内关键词搜索”能力，并通过前后端测试完成收尾。

**Architecture:** 后端继续复用现有 `/api/events` 的 `keyword` 参数过滤标题与一句话摘要；前端在首页英雄区新增搜索输入与触发按钮，把关键词透传到事件流请求，并在切换频道与分页时保留搜索条件。实现保持在现有首页与 API 结构内，不新增独立搜索页。

**Tech Stack:** FastAPI、SQLAlchemy、Vue 3、TypeScript、Vitest、pytest

---

## 文件与职责映射

- 修改：`info-max/src/views/__tests__/HomeView.spec.ts`
  - 先补首页关键词搜索行为测试，覆盖初始化、关键词触发与频道切换时保留关键词。
- 修改：`info-max/src/types.ts`
  - 为事件列表查询参数增加 `keyword` 字段。
- 修改：`info-max/src/services/api.ts`
  - 将 `keyword` 透传到 `/api/events` 查询参数。
- 修改：`info-max/src/views/HomeView.vue`
  - 新增搜索输入、搜索触发与请求参数状态管理。
- 验证：`info_aggregation/tests/test_event_api.py`
  - 复用已有后端关键词过滤测试，确认接口回归通过。

### Task 1: 用前端测试锁定关键词搜索行为

**Files:**
- Modify: `info-max/src/views/__tests__/HomeView.spec.ts`

- [ ] **Step 1: 写出失败的首页搜索测试**

```ts
expect(fetchMock).toHaveBeenCalledWith(
  expect.stringContaining('/api/events?category_code=all&keyword=OpenAI&page=1&page_size=10'),
  expect.any(Object),
)
```

- [ ] **Step 2: 运行单测确认先失败**

Run: `npm test -- src/views/__tests__/HomeView.spec.ts`
Expected: FAIL because HomeView does not render a search input or send `keyword`.

- [ ] **Step 3: 实现最小前端代码让测试通过**

```ts
const keyword = ref('')
const appliedKeyword = ref('')

async function submitSearch() {
  appliedKeyword.value = keyword.value.trim()
  await loadEvents(1)
}
```

- [ ] **Step 4: 重新运行单测确认通过**

Run: `npm test -- src/views/__tests__/HomeView.spec.ts`
Expected: PASS

### Task 2: 透传事件搜索参数并保持频道上下文

**Files:**
- Modify: `info-max/src/types.ts`
- Modify: `info-max/src/services/api.ts`
- Modify: `info-max/src/views/HomeView.vue`

- [ ] **Step 1: 为事件列表请求参数补充 keyword 字段**

```ts
export interface ListEventParams {
  category_code?: string
  keyword?: string
  page?: number
  page_size?: number
}
```

- [ ] **Step 2: 在 API 请求中透传 keyword**

```ts
const query = buildQuery({
  category_code: params.category_code ?? 'all',
  keyword: params.keyword,
  page: params.page,
  page_size: params.page_size,
})
```

- [ ] **Step 3: 在首页保留频道与关键词联动**

```ts
eventPage.value = await getEvents({
  category_code: activeCategoryCode.value,
  keyword: appliedKeyword.value,
  page,
  page_size: pageSize,
})
```

- [ ] **Step 4: 运行首页测试确认联动行为**

Run: `npm test -- src/views/__tests__/HomeView.spec.ts`
Expected: PASS

### Task 3: 做完整回归验证

**Files:**
- Verify: `info-max/src/views/__tests__/HomeView.spec.ts`
- Verify: `info_aggregation/tests/test_event_api.py`

- [ ] **Step 1: 跑前端首页相关测试**

Run: `npm test -- src/views/__tests__/HomeView.spec.ts`
Expected: PASS

- [ ] **Step 2: 跑后端事件 API 测试**

Run: `pytest tests/test_event_api.py -q`
Expected: PASS

- [ ] **Step 3: 跑前端构建验证**

Run: `npm run build`
Expected: build succeeds
