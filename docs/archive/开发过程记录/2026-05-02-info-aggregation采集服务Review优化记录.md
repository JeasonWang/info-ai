# info-aggregation 采集服务 Review 优化记录

日期：2026-05-02

## 背景

本次优化针对采集服务代码 review 中发现的五个问题，目标是提升真实数据采集的新鲜度、详情完整度、并发稳定性和可诊断性。

## 优化内容

1. 渠道级采集间隔真正生效
   - 调度器不再只按分类固定间隔采集全部渠道。
   - 每次分类任务触发时，先同步 `CrawlTask`，再只执行 `next_run_at <= now` 的到期渠道。
   - 采集完成后根据 `schedule_value` 推进下一次 `next_run_at`。

2. 嵌入详情纳入完整详情闭环
   - `_search_content` 通过质量管线判定为完整详情后，保存阶段同步写入语义字段。
   - 同步记录 `InfoAcquisitionLog`，避免详情完整但没有采集日志。
   - 对历史已完整但缺少语义或日志的记录，在跳过重复详情抓取时补齐。

3. 同渠道采集并发隔离
   - 注册中心为每个渠道维护 `RLock`。
   - 手动采集、定时采集和详情补偿执行同渠道爬虫时会进入同一把锁，避免全局单例爬虫的 `requests.Session` 被并发复用。

4. 今日头条详情策略短路
   - `hot_board_detail`、`search_content`、`web_fallback` 每一步拿到候选后立即进入详情质量管线。
   - 达到 `complete` 时直接返回，不再继续启动 Playwright。
   - Playwright 渲染保留为最后兜底策略。

5. 知乎热搜 source_id 升级
   - 热搜二次搜索成功时，优先使用规范化 `source_url` 生成 `source_id`。
   - 只有无法解析问题或文章 URL 时，才退回热搜词生成 ID。
   - 嵌入搜索详情达到完整标准时，直接短路返回，减少不必要的回答 API 调用。

## 回归测试

新增和调整的关键测试覆盖：

- 到期渠道才会被调度执行，未到期渠道不会被提前采集。
- 嵌入详情完整入库后会生成采集日志，并补齐语义字段。
- 今日头条轻量详情已经完整时不会触发浏览器渲染。
- 知乎热搜 enriched URL 会参与 `source_id` 生成。

验证命令：

```bash
cd info_aggregation
./.venv/bin/python -m pytest -q
```

验证结果：

```text
134 passed in 23.84s
```
