# Failure Taxonomy（初版草稿，E0 后按轨迹标注迭代）

用途：对失败 trajectory 逐条标注主因类别（单选主类别 + 可加次类别），
统计分布后写入论文 Error Analysis 一节。

## 类别定义

| 代码 | 类别 | 定义与判别线索 |
|---|---|---|
| F1 | 问题理解错误 | 模型修复方向与任务描述不符；改动内容与描述要求的 bug 无关 |
| F2 | 上下文不足 | 需要的信息不在 prompt 中（repo 级任务常见；自建集应罕见） |
| F3 | patch 格式错误 | 无法提取代码块 / 提取到错误代码块（trajectory 中 error_type=extract_failed） |
| F4 | 测试理解错误 | 模型正确定位 bug 但误解测试期望（如断言语义理解错） |
| F5 | 修复方向错误 | 定位到错误位置，改了不该改的地方 |
| F6 | 重复犯同一错误 | 连续两轮输出等价错误代码（对比相邻两次输出） |
| F7 | 过度修改 | 修复引入新 bug / 破坏原本通过的测试 / 重写整个实现 |
| F8 | 幻觉 API | 使用不存在的函数、方法或参数 |
| F9 | 循环震荡 | 在两种错误方案间来回切换，无法收敛 |
| F10 | 预算耗尽 | error_type=budget_exceeded，5 轮/50K token 内未解决 |
| F11 | 基础设施失败 | 测试执行超时、环境错误（此类不计入模型失败，需单独报告） |

## 标注流程

1. 从 `runs/E0/<mode>/metrics.jsonl` 筛出 `success=false` 的实例；
2. 对照 `trajectories.jsonl` 回放该实例全部 step（重点看每轮 feedback 与响应差异）；
3. 在 `analysis/annotations/<mode>.tsv` 记录：instance_id, 主类别, 次类别, 备注；
4. E0 阶段要求至少精读每组 10 条失败轨迹；
5. 标注完成后统计分布，检验假设：
   - 若 F3 占比高 → 优先上 guided decoding / 格式约束；
   - 若 F6/F9 占比高 → 反思记忆机制（去重、震荡检测）是下一步重点；
   - 若 F5 占比高 → 检索增强 / 错误定位是下一步重点。

## 分析产物的论文价值

- 失败分布表（按 mode 分列）直接进论文 Error Analysis；
- `repair` 组中 F6/F9 的比例变化可量化"反思是否真的减少了重复错误"；
- 与 bug_type（off_by_one、state_update 等）交叉分析：哪类 bug 反思最有效。
