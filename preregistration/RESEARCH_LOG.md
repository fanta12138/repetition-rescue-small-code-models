# 研究日志（唯一记录文件）

课题 A：让 3B~7B 小模型通过 Agent 架构与反思纠错机制完成代码修复任务。
模型：Qwen2.5-Coder-7B-Instruct-AWQ（vLLM, RTX 3090, temp=0.2）。
铁律：预注册（跑数前冻结判定规则）；seed 有效性核验；控制组归因。

本文件是全工作唯一的 md 记录。E0-E4 为已定版的历史归档，
E5 起的新内容直接追加在本文件末尾。

## 项目骨架

```
configs/  实验 yaml        agent/    repair loop、prompt、反馈压缩
tools/    sandbox、提取    data/     自建任务集 v1-v4
eval/     指标、统计检验   scripts/  入口（verify_tasks / run_e0 / task_matrix）
setup_env/ 全部运行脚本（WSL 内执行）   runs/  实验产物
```

环境：WSL2 Ubuntu-24.04，venv 在 `~/agentenv`，模型在 `~/models`。
vLLM 服务：`vllm serve ~/models/Qwen2.5-Coder-7B-Instruct-AWQ --quantization awq
--max-model-len 16384 --gpu-memory-utilization 0.9 --port 8000`（终端常驻）。
一切逻辑写 .sh 经 `wsl -d Ubuntu-24.04 bash` 执行（PowerShell 会剥 `$`/引号）。

---

# 历史归档（E0-E4，已定版）

## E0（v2 难度集，5 seeds × 4 臂，n=100/臂）——反馈诊断性首次证伪
结果：direct 84% / no_feedback 92% / random_reflection 92% / repair 93%。
McNemar：repair vs direct +9pp 11/2 p=0.023（循环效应真实）；
repair vs no_feedback +1pp 2/1 p=1.0（反馈诊断性不可检出）。
核心发现 F-03：v2_11 策略锁定（0/20 全组，5 轮逐字重复同一错误修法）——
failure taxonomy 种子。裁决：反馈压缩线关闭。
复现：`python -m scripts.run_e0 --dataset v2 --seeds ... --out runs/E0v2s5`

## E1（可操作反馈格式，n=100/臂）——格式线关闭
新臂 repair_structured（逐用例断言差异）、repair_contrast（+通过用例对比），
以 repair 为基底、触发前逐位一致。结果均 95%，vs no_feedback +3pp 3/0
p=0.25，未过阈（p<0.025 且 Δ≥3pp）。裁决：反馈形式无效。
辅助：structured 比 repair 省 20% token 且准确率更高 → 成为默认格式。
复现：`bash setup_env/run_e1.sh; bash setup_env/analyze_e1.sh`

## E2（v3 多文件集 10 题，5 seeds × 4 臂，n=50/臂）——诊断性彻底证伪
结果：direct 84% / 三个循环臂均 94%；repair vs no_feedback 0/0 p=1.0；
repair vs direct +10pp 5/0 p=0.0625。定位率全臂 100%（定位不是瓶颈）。
唯一失败 v3_07（CSV 引号解析，正则 lookbehind 族）：全臂逐字重复锁死。
裁决：即使需要跨文件定位，真反馈相对"重试无反馈"增益仍精确为 0。
复现：`bash setup_env/run_e2.sh; bash setup_env/analyze_e2.sh;
bash setup_env/check_seed_dup_e2.sh; bash setup_env/inspect_v3_07.sh`

## E3（打破 repetition lock-in，n=150/臂 pooled）——首个阳性信号（边缘）
新臂均以 repair_structured 为基底、触发式干预（冒烟验证触发前逐位一致）：
repair_diverse（逐字重复检测 → 注入"换思路"指令 DIVERSITY_NUDGE）、
repair_tempbump（同检测 → 温度 0.2→0.9）。预注册阈：Δ≥4pp 且 p<0.025。
结果：diverse v2=100%（5/5 救回 v2_11）/ v3=94%；pooled +3.3pp 5/0
p=0.0625 未过阈；tempbump 与 structured 逐字节一致（固定 seed 下升温无效）。
机制证据：nudge 后 v2_11 从锁死的 str.replace 循环切到栈解法一次通过
——正确修法一直在分布内，锁定是策略粘滞而非能力缺口。v3_07 未救回
（深层方案族锁定）。裁决：边缘阴性 + 强机制证据。diverse 省 10% token。
复现：`bash setup_env/e3_smoke.sh; bash setup_env/run_e3.sh;
bash setup_env/analyze_e3.sh; bash setup_env/inspect_e3.sh`

## E4（锁定干预扩样 + 归因分离，210 实例）——效应确认但统计单位纠错
设置：v4 粘滞诱导集 12 题（tasks_v4.py，两轮筛选预先识别锁定题）+
v2_11/v3_07，3 臂（structured / diverse / nudge_weak）× 5 seeds。
nudge_weak = 同一重复观察 + 通用"再试一次"（无换思路要求），
用于排除"多一轮重试"替代解释。筛选证据：v4_01、v4_08 双 seed 锁定；
v4_04/v4_05 不稳定；其余 8 题一次解掉。
预注册口径（n=22 锁定实例）：P1 diverse vs structured 54.5% vs 0%，
12/0 p=0.00049 过阈；P2 weak 无效（1/0 p=1.0）；S1 diverse vs weak
11/0 p=0.00098 过阈。逐任务：v2_11 与 v4_08（浅层）各 5/5 救回，
v4_01 与 v3_07（深层）0 救回——浅层/深层分层假说 4/4 成立。
零回归、零公平性失配、diverse 省 15% token。
**关键修正**：seed 核验暴露锁定题在 temp=0.2 下完全确定（v2_11 全臂
10/10 seed hash 重复），22 实例按轨迹 hash 坍缩为 8 个独立行为单元，
去重后 P1 p=0.25、S1 p=0.50 均不显著。**诚实裁决：统计显著性不成立，
但效应确定性复现（5/5 且逐位一致）、归因分离成立（diverse 5/5 vs
weak 0/5，唯一差异是措辞）、边界清晰（深层锁定不可救）**。
方法论教训：低温确定性推理下 seed 不是独立实验单位，行为单元
（轨迹 hash）才是；功效只能靠增加不同任务，不能靠加 seed。
复现：`bash setup_env/screen_e4.sh; bash setup_env/run_e4.sh;
bash setup_env/analyze_e4.sh; bash setup_env/analyze_e4_dedup.sh`

## 五轮实验 claim 链（截至 E4）
1. E0/E1/E2：测试反馈的诊断内容无价值（增益 = 重试）。
2. E3/E4：重复检测 + 换思路指令对浅层策略粘滞确定性有效、零回归、
   省 token；弱版 nudge 无效（归因分离）；深层方案族锁定不可救。
核心 claim 候选："小模型反思循环的有效成分是行为层的循环检测与
换思路指令，而非测试反馈的诊断内容；其效力存在清晰的深度边界。"

---

# E5：浅层锁定任务扩充（进行中）

## 动机与统计设计
E4 瓶颈：独立行为单元仅 8 个（可救的浅层只有 v2_11、v4_08 两个任务）。
E5 定向造"浅层可救"族任务（跳读循环级联、顺序/下标混淆），目标
8-10 个互不相同的锁定任务。确定性已证（E4）：每任务跑 2 seeds 做
确定性核验，统计单位 = 任务（轨迹 hash 去重后）。

## 任务集（data/selfbuilt/tasks_v5.py，14 候选，verify 全过）
- A 族跳读级联 6 题（v2_11 同族异规则）：v5_01 数字对和=10、
  v5_02 参数化和=k、v5_03 ASCII 差 1、v5_04 字符串列表相等、
  v5_05 嵌套括号配对、v5_06 数字串相等（v2_11 同构异表面）。正解均为栈。
- B 族顺序/边界混淆 8 题（v4_08 同族）：v5_07 three_sum 排序双指针
  （并列 k 规则）、v5_08 max_profit 无视 i<j、v5_09 closest_pair 并列 j
  规则、v5_10 search_range last off-by-one、v5_11 max_subarray 并列键
  缺失、v5_12 pivot_index 右切片含自身、v5_13 min_rotated lo=mid
  死循环、v5_14 longest_mountain 长度 off-by-one。
- 设计原则：只造"正解在分布内且与 buggy 族不同构"的题（栈/哈希 vs
  跳读循环/排序指针）；深层族（replace 顺序、正则）刻意排除。

## 预注册判定规则（跑数前冻结，2026-08-17）
流程：
1. 筛选：仅用 repair_structured 臂，14 题 × seeds 0,1 → 锁定任务 =
   双 seed 均失败且 repetition_events≥2（只用基线臂可观测行为，
   不碰干预臂数据）。冻结锁定子集后才跑干预臂。
2. 全量：冻结子集 × 3 臂（structured/diverse/nudge_weak）× seeds 0,1。
   structured 的 seed 0 直接复用筛选结果（同配置同 seed 确定性等价）。
3. 确定性核验：锁定任务在 structured 臂下 seed0/seed1 轨迹 hash 相同
   为预期；若不同则该任务按两个单元计。

检验（单位 = 去重后的独立任务）：
- P1：diverse vs structured，锁定任务集，McNemar/符号检验精确。
  阈值：b≥7 且 c=0（b=diverse 独胜任务数）。功效：K≥8 且 diverse
  恢复 ≥7 → 双侧 p=2·0.5^K≤0.016 < 0.05。若 K<8 则只报描述性统计。
- P2：weak vs structured，同口径（预期不过；归因对照）。
- S1：diverse vs weak（预期过，配合 P2 排除"重试"解释）。
- 回归守卫：非锁定任务（筛选中一次解掉的）上 diverse 不净亏损。

解释树：
- P1 过 + P2 不过 + S1 过 → STRONG：效应跨任务族泛化且归因干净，
  五轮 claim 链获得真统计支持，进入论文写作。
- P1 过但 P2 也过 → 降级：换思路指令与弱重试不可分离。
- P1 不过 → 效应不泛化，五轮结论维持 E4 裁决（确定性机制证据）。

## 筛选结果（structured 臂，14 题 × 2 seeds）
- 双 seed 锁定（失败 + rep≥2）仅 2 题：**v5_07**（rep=4，确定性 Y）、
  **v5_09**（rep=3，确定性 Y）。
- v5_04 双 seed 失败但 seed0 仅 rep=1（轨迹逐步演化后定型，属"漂移
  后锁定"而非逐字重复）→ 按预注册"若不同则按两个单元计"处理，
  仅 seed1 的逐字锁定（rep=4，5 步输出 hash 全同）入锁定集。
- 其余 11 题中 10 题 iters=1 一次解掉（off-by-one 族 v5_10/13/14 全军
  覆没，模型太强）；v5_03 seed0 二轮解掉。
- 冻结锁定子集：{v5_07, v5_09, v5_04@seed1}，K=3 < 8 → 预注册规定
  只报描述性统计。

## 干预结果（3 臂 × seeds 0,1，冻结子集）
| 单元 | structured | diverse | weak |
| --- | --- | --- | --- |
| v5_04@seed1 | FAIL r4 | **PASS i1 iters=3** | FAIL r2 |
| v5_07 | FAIL r4 | FAIL r2 i2 | FAIL r4 i4 |
| v5_09 | FAIL r3 | FAIL r2 i2 | FAIL r3 i3 |

- P1：b=1, c=0，K=3 → **不过**（阈 b≥7）。
- P2：b=0, c=0 → 不过。S1：1/0 → 功效不足不作判定。
- 确定性核验：structured 臂 E5 与筛选的 token 逐位一致（6/6 SAME），
  v5_07/v5_09 双 seed 轨迹 hash 相同——行为完全确定，非抽样波动。
- 公平性：v5_04@seed0（未锁定单元）三臂 token 全同 2267，干预前行为
  逐位一致。

## 裁决（按预注册解释树）
**P1 不过 → 效应未在新任务族上泛化，五轮结论维持 E4 裁决**
（确定性机制证据 + 归因分离 + 边界，不宣称统计显著性）。

## E5 真正的收获：锁定类型学细化（新机制发现）
diverse 的 nudge 在 v5_07/v5_09 上**确实改变了行为**（rep 从 4→2、
3→2，代码不再逐字重复），但模型**留在同一算法族内微调**
（v5_09 触发后仍在排序双指针上加并列条件、v5_07 仍重写排序指针），
未跳到分布内的正解族（哈希/枚举）。对比被救回的锁定：v2_11→栈、
v4_08→哈希、v5_04@seed1→跳读变体，触发后均发生**算法族切换**。

据此把 repetition lock-in 细化为三类：
1. **可救型（family-switch）**：逐字重复 + 正解族与 buggy 族不同构且
   可达 → nudge 触发族切换，确定性救回（v2_11、v4_08、v5_04@seed1）。
2. **族内打转型（within-family tinkering）**：表面规范（并列 tie-break）
   诱使模型相信"微调就能对"，nudge 能打破逐字重复但无法迫使跳出
   算法族 → 不可救（v5_07、v5_09）。
3. **深层方案族型**：正确修法可能不在模型分布内 → 不可救
   （v3_07、v4_01）。
锁定能否被指令救回，取决于"诱人的下一步微调是否仍在错误族内"，
而非 buggy 代码的表面家族（v4_08 是 B 族但可救，v5_07/v5_09 同为
B 族但不可救——区别正在于此）。

## 累计锁定记录（五轮全部）
| 单元 | 族 | 锁定类型 | diverse |
| --- | --- | --- | --- |
| v2_11 | 跳读级联 | 可救 | 5/5 救回 |
| v3_07 | 正则 | 深层 | 0 |
| v4_01 | replace 顺序 | 深层 | 0 |
| v4_04/05 | 跳读/缺排序 | seed 依赖 | 部分 |
| v4_08 | 排序指针+下标 | 可救 | 5/5 救回 |
| v5_04@seed1 | 跳读级联 | 可救 | 救回 |
| v5_07/v5_09 | 排序指针+tie-break | 族内打转 | 0 |

## 导师裁决与下一步建议
功效目标（K≥8 独立可救锁定任务）未达成，且两轮筛选（v4 12 题→2 锁定、
v5 14 题→2 锁定）表明：该模型下稳定锁定本身就是稀有事件，继续造题
的边际收益递减。**建议停止追 p 值，进入论文写作**：我们手里有一个
诚实且完整的故事——反馈诊断性三连证伪（E0-E2）→ 循环检测干预的
确定性机制证据与干净归因（E3-E4）→ 边界与锁定类型学（E4-E5），
外加零回归/省 token 的工程证据。若仍想追真显著，唯一诚实路径是
E6（需重新预注册，预算大、收益不确定）。

## 复现
```bash
bash setup_env/screen_e5.sh    # 筛选（runs/E5_screen）
bash setup_env/run_e5.sh       # 干预臂全量（runs/E5）
bash setup_env/analyze_e5.sh   # 预注册分析 + 触发后代码检查
```

---

# 论文大纲（paper-plan，2026-08-18）

**工作标题**：Repetition Detection, Not Diagnostic Feedback, Drives
Self-Repair in Small Code Models
**一句话贡献**：对 3B-7B 小模型的测试驱动修复循环做受控解剖：反馈的
诊断内容贡献为零（增益=重试），循环的活性成分是行为层逐字重复检测
+换思路指令，它对可救型策略锁定确定性有效、零回归、省 token，并存在
由锁定类型学刻画的清晰边界。
**目标会场**：ICLR（正文 9 页，不含参考文献/附录）；natbib 引用。
**类型**：empirical / mechanism-analysis。

## Claims-Evidence 矩阵
| Claim | 证据 | 状态 | 章节 |
| --- | --- | --- | --- |
| C1 反馈诊断性零贡献，增益=重试（限定 7B-AWQ） | E0 +1pp 2/1 p=1.0；E1 +3pp 3/0 p=0.25 未过阈；E2 0/0 p=1.0；E6：3B 上 +6pp p=0.031 未复现 → 限定范围 | Supported（三轮证伪，范围限定） | §4 |
| C2 触发式干预确定性救回可救型锁定 | v2_11 5/5、v4_08 5/5、v5_04@seed1；跨 seed/跨 run 逐位复现；E6：3B 上 v4_08 diverse 3/5 救援轨迹逐位一致 | Supported（7B 确定性证据 + 3B 描述性复现） | §5.3 |
| C3 活性成分是"换思路"指令本身（归因分离） | weak 臂同观察仅改指令 0/5 vs diverse 5/5；触发前逐位一致；E6：3B 上 v4_08 weak 0/5 vs diverse 3/5 同向 | Supported | §5.4 |
| C4 锁定三类型学与可救性判据 | 全部锁定单元记录；v5_07/v5_09 rep↓但不切族；v4_01/v3_07 零效果；E6：两模型各现可救型+深层族型，锁定集零重叠 | Supported（跨模型强化 + 新增量化指标，见下） | §5.5 |
| C5 工程价值：零回归、公平、省 token | 回归守卫 0 亏损；rep=0 实例 token 全同；省 10-15% | Supported | §5.3/§6 |

已知弱点（如实写入 §6）：无统计显著性（独立锁定单元仅 8 个）；
单语言自建小任务集；确定性 regime（且 E6 发现该 regime 规模依赖：
3B 锁定轨迹漂移）；C1 零结论不跨规模（3B 上诊断内容 +6pp）。

## 外部评审（GLM 独立评审）与采纳决定
评分：逻辑流 8 / claim-evidence 7 / 缺失分析 6 / 定位 8 / 预算 8 /
前置强度 7。四条最小修复的采纳决定：
1. 样本量功效不足 → 采纳：§5.6 增加贝叶斯因子报告（预注册口径与
   行为单元口径双报告），不再追造题（两轮筛选已证命中率 ~2/14，
   边际收益递减，导师裁决不变）。
2. 单模型泛化 → 采纳为**写作前前置实验 E6**：用第二个模型复跑
   核心臂（direct/repair/no_feedback/diverse/weak × v2 集 + 已知
   锁定题），验证"诊断零贡献+干预可救"跨模型一致性。候选：
   Qwen2.5-Coder-3B-Instruct（同家族不同规模，AWQ 后 3090 可跑）
   或 StarCoder2-3B（跨架构，需先验 ModelScope 可达性）。
3. 类型学缺量化判据 → 采纳：新增离线指标——对触发前后候选代码做
   **AST 结构编辑距离**（去标识符后），"切族"=结构距离跨阈，
   "族内打转"=结构距离小但语义不变；用已有轨迹数据即可计算，
   无需新跑模型，写入 §5.5 与 Fig 3。
4. 内部表征探针（隐藏状态/注意力）→ 婉拒入正文：vLLM 提取 hidden
   states 工程量大且超出行为层论文定位；写入 §6 future work。

## 分节大纲（页预算合计 9.0）
### §0 Abstract（150-250 词）
- 问题：小模型 self-repair 被默认有效，但活性成分从未被分离。
- 方法：预注册受控解剖（控制组分离重试/反馈内容/反馈格式/干预）。
- 发现：反馈诊断性三轮证伪；重复检测干预确定性救回可救型锁定；
  弱版对照排除重试解释；三类型学边界。
- 最强结果：v2_11/v4_08 上 diverse 5/5 确定性救回 vs weak 0/5。

### §1 Introduction（1.5 页）
- hook：Reflexion 类 self-repair 在大模型上有效，社区默认迁移到
  小模型，但没有人用控制组分离过"反馈内容 vs 重试 vs 干预"。
- 研究问题：小模型修复循环的增益从哪来？锁定何时可救？
- 贡献（4 条，对应 C1/C2+C3/C4/C5）。
- hero figure 见 Fig 1；结果前置（浏览式读者在 §1 就能看到主 claim）。
- 关键引用：Reflexion、Self-Refine、Self-Debug、SWE-agent、SWE-bench。

### §2 Related Work（1 页，按方法论族组织，非逐篇列表）
- (a) self-refine/reflection 循环：默认反馈有价值假设——本文证伪其
  小模型情形；(b) 测试驱动代码修复/生成与反馈形式研究——本文证明
  形式无关；(c) agent 失败模式与重复/退化生成文献——lock-in 类型学
  与之衔接；(d) 小模型 agent 与成本等效研究。

### §3 Framework & Benchmark（1.5 页）
- 修复循环状态机形式化：候选生成/沙箱执行/反馈压缩/干预注入点。
- 9 个实验臂设计意图表（每臂回答哪个归因问题）。
- 任务集 v2-v5 设计原则与双不变量校验（buggy 必失败/fixed 必通过）；
  粘滞诱导设计与筛选流程（纸面设计不可靠，必须实证筛选）。
- 预注册方法论与统计单位处理（低温确定性下按轨迹 hash 坍缩行为
  单元）——方法论本身作为贡献呈现。

### §4 Feedback Content Contributes Nothing（1.5 页）
- E0/E1/E2 合并呈现，Table 1；逐层排除叙事：重试有效（p=0.023）→
  诊断内容零贡献 → 格式无关 → 跨文件定位不改变结论。
- 失败伏笔：v2_11/v3_07 全臂锁死，引出 §5。

### §5 Repetition Lock-in and Triggered Intervention（2.5 页，核心）
- 5.1 现象定义与度量：repetition_events、轨迹 hash 确定性核验。
- 5.2 干预设计与公平性：触发条件、DIVERSITY/WEAK 措辞、触发前三臂
  逐位一致验证。
- 5.3 主结果：Fig 2 锁定单元×臂恢复矩阵（8 个独立行为单元逐个
  呈现）；回归守卫与 token 成本。
- 5.4 归因分离：weak 臂设计逻辑与结果（E4/E5）。
- 5.5 边界与类型学：Fig 3 三类型学 + AST 结构距离量化判据 +
  轨迹定性案例（v5_09：rep 4→2 但留在排序指针族；v2_11：切栈）。
- 5.6 诚实的统计地位：预注册口径 vs 行为单元口径双报告 + 贝叶斯
  因子；效应主张基于确定性复现而非 p 值，明示功效不足。

### §6 Discussion & Limitations（0.5 页）
- 启示：检测器比反馈器便宜且有效；何时该投资反馈（定位/长程任务
  待验证）。
- 局限：单模型（E6 补充第二模型）、单语言、K 小、确定性 regime；
  future work：内部表征探针、深层锁定的更强干预（示例注入/方案族
  显式枚举）。

### §7 Conclusion（0.5 页）
重述贡献（非复粘 intro），收尾于方法论启示：小模型 agent 研究需要
成分分离式受控解剖，而非端到端榜单比较。

## Figure / Table 计划

**产出约束（用户要求，2026-08-18）**：全部图片用 Python + matplotlib
绘制，字体 Times New Roman；每张图同时导出配套 CSV 数据文件
（正式稿用户用 Visio 重绘）。图表统一放 figures/ 目录，命名
figN_xxx.pdf/png + figN_xxx.csv。

| ID | 类型 | 内容 | 数据来源 | 优先级 |
| --- | --- | --- | --- | --- |
| Fig 1 | hero 双栏 | 左：direct 84% vs 循环臂 92-93% 条形图（标 p 值，信息=增益是重试）；右：structured 5 轮同一代码（灰）vs diverse 注入 nudge 后切族通过（彩色） | E0v2s5 + 轨迹 | HIGH |
| Fig 2 | 热力矩阵 | 8 独立锁定单元 × 3 臂恢复矩阵 | E3/E4/E5 metrics | HIGH |
| Fig 3 | 类型学示意 | 三类各一条真实轨迹的策略演化序列 + AST 结构距离曲线 | 轨迹 + 离线 AST 分析 | HIGH |
| Table 1 | 主结果 | E0/E1/E2 合并：臂 × success/iters/tokens/McNemar | runs/E0v2s5,E1,E2 | HIGH |
| Table 2 | 检验 | E4 预注册三检验 + 去重敏感性双报告 | analyze_e4*.sh | HIGH |
| 附录 | 全集 | 逐任务矩阵、任务设计细则、prompt 模板、E6 跨模型结果 | 全部 runs | — |

## 引用计划（全部写作阶段逐条核验，不凭记忆生成 BibTeX）
- §1：Reflexion、Self-Refine、Self-Debug、SWE-agent、SWE-bench
- §2：Test-driven code generation、EvalPlus/HumanEval、重复退化
  文献、小模型 agent（CodeLlama/StarCoder 技术报告）
- §3：pytest/沙箱无关引用；McNemar/精确检验标准引用

## 下一步
1. ~~E6 前置实验~~ → 已完成，见文末 E6 节（R1 未复现、R3 未过、
   v4_08 可救型跨模型描述性复现）。
2. AST 结构距离离线分析（用已有轨迹，无新计算）。
3. 贝叶斯因子计算（§5.6）。
4. paper-figure → paper-write → paper-compile。

---

# E6：跨模型验证（完成，2026-08-18）

## 设置
第二模型：Qwen2.5-Coder-3B-Instruct-AWQ（ModelScope 下载，同家族
不同规模；注意 3B 为 Research Only 许可，论文需注明）。其余配置与
7B 完全一致（temp=0.2、max_iters=5、同 prompt/沙箱/预算）。
- 运行 1：v2 全集 20 题 × 6 臂（direct/repair/no_feedback/
  structured/diverse/weak）× 5 seeds = 600 实例。
- 运行 2：v4_08（7B 上的可救型锁定标杆）× structured/diverse/weak
  × 5 seeds = 15 实例。

## 预注册判定规则（跑数前冻结）
- **R1（反馈诊断性复现）**：repair vs no_feedback（n=100 配对），
  复现成功 = Δ≤3pp（无论 p 值）且 repair vs direct Δ>0。
  （与 E0 同口径；若 Δ>3pp 且 p<0.025 → 结论不跨模型，论文限定
  声明范围为 7B-AWQ。）
- **锁定识别**：同 E4/E5 口径（structured 失败且 rep≥2，双 seed），
  轨迹 hash 确定性核验，单元 = 去重后任务。
- **R3（干预主检验，3B 上真显著的机会）**：3B 更弱预期产生更多
  锁定单元。主比较 diverse vs structured 于锁定任务集（单位=任务）：
  阈值 b≥7 且 c=0（同 E5 预注册）→ 双侧精确 p≤0.016，效应跨模型
  真显著。K<7 则只报描述性。
- **R2（归因复现）**：锁定任务上 weak vs diverse 描述性报告，
  预期 diverse 优于 weak（同 E4 方向）。
- **公平性/回归守卫**：rep=0 实例 diverse/weak vs structured token
  全同；非锁定实例干预臂不净亏损。

## 结果

### R1：反馈诊断性复现（v2 × 6 臂 × 5 seeds，n=100/臂）

| 臂 | 成功率 | avg_tokens |
|---|---|---|
| direct | 70/100 | 408 |
| repair | 82/100 | 1267 |
| no_feedback | 76/100 | 960 |
| repair_structured | 80/100 | 1102 |
| repair_diverse | 80/100 | 1116 |
| repair_nudge_weak | 80/100 | 1112 |

- repair vs no_feedback：Δ=+6pp，b/c=6/0，精确 p=0.0312 → **R1 未复现**
  （阈值 Δ≤3pp）。Δ>3pp 但 p=0.031 未触发预注册的 p<0.025 分支
  （预注册未覆盖的灰区）→ 按预注册精神处理：C1 零贡献结论限定
  7B-AWQ，论文如实报告 3B 上诊断内容有 +6pp 增益。
- repair vs direct：+12pp，p=0.0005（循环臂显著强于一次生成，与 7B 同向）。
- structured vs no_feedback：+4pp，p=0.125；repair vs structured ≈ +2pp
  → 3B 上反馈增益主要来自结构化/重试，诊断内容仅贡献边缘小量，
  但已足够打破 7B 的严格零结论。

### 锁定识别（structured 臂）

锁定任务：**v2_13、v2_14、v2_15**（7B 上均未锁定；7B 锁定的 v2_11
在 3B 上多数 seed 一次解掉）。轨迹 hash：v2_13/v2_15 五个 seed 五条
不同轨迹（非确定性），v2_14 两条。K=15 单元（任务×seed）。
**新发现：3B 的锁定是非确定性的，与 7B temp=0.2 下逐位确定性
regime 不同 → 确定性 regime 本身是模型/规模依赖的边界条件。**

### R3：干预主检验（diverse vs structured 于锁定集）

b/c=0/0，p=1.0 → **阈值不过**。3B 原生锁定任务（深层方案族：
三臂全败、轨迹漂移）干预全部救不回。R2：weak vs diverse b/c=0/0，
无差异。公平性：rep=0 实例 token 全同，0 mismatch；回归守卫：
非锁定实例干预臂 0 增益 0 损失。

### E6lock：v4_08（7B 可救型标杆）跨模型复现

| 臂 | 成功率 | rep |
|---|---|---|
| structured | 0/5 | 3,3,4,4,4 |
| **diverse** | **3/5（iters=3）** | 3,2,1,1,1 |
| weak | 0/5 | 3,3,4,3,4 |

三次救援 tokens 全同=1507 → 救援轨迹确定性复现。**可救型锁定 +
diverse 干预 + 归因分离（weak 无效）三要素跨模型成立（描述性，
n 小不单独显著）。**

**轨迹取证（2026-08-18，排除数据污染）**：3B 救援候选代码与 7B
逐字节相同曾引起污染怀疑。取证结论：非污染，是真实收敛——
① v4_08 为 Two Sum 任务，两模型锁定族同为暴力解（excerpt hash
f8bfd594），救援后同收敛到典范哈希解（hash ef01fa7d）；②逐步
prompt/completion tokens 指纹一致但 wall_time 系统性不同（3B 0.74s
vs 7B 1.05s），确认为两个模型独立推理；③ E6lock run_meta 确认
模型为 3B-AWQ。**诚实含义**：v4_08 的跨模型救援复现部分依赖
该题是经典算法题（典范解吸引子），论文需如实表述，不能外推到
新颖结构任务；这也解释了"3B 救援 tokens 逐位一致"的现象。

## 导师裁决（2026-08-18）

1. **R1 未跨模型复现（诚实的阴性）**：诊断零贡献是 7B-AWQ regime
   的结论；3B 上诊断内容值 +6pp。论文 claims 矩阵更新：C1 限定
   模型范围，并在 §5.6/附录如实报告 3B 差异（这反而加强论文的
   诚实叙事：效应存在规模边界）。
2. **R3 未过但类型学跨模型强化（C4）**：两个模型上同时观察到
   可救型（v2_11@7B、v4_08@两模型）与深层方案族型（v3_07/v4_01@7B、
   v2_13/14/15@3B），且 3B 锁定集与 7B 零重叠 → 锁定涌现依赖
   模型能力分布，支持类型学而非单一致应。
3. **C2/C3 跨模型描述性成立**：v4_08 上 diverse 确定性救援 3/5、
   weak 0/5。严格显著性仍以 7B 池化证据为主，3B 作为 replication
   evidence 报告。
4. 新增论文素材：确定性 regime 的规模依赖性（7B 逐位确定 vs 3B
   轨迹漂移）入 §5 讨论。

## 复现

```bash
bash setup_env/e6_pipeline.sh   # 启动 3B vLLM（需 VLLM_WSL2_ENABLE_PIN_MEMORY=1）
                                # + run_e6.sh（运行 1+2）+ analyze_e6.sh
```
原始输出：runs/E6v2、runs/E6lock；分析脚本 setup_env/analyze_e6.sh。

## 写作前置分析（完成，2026-08-18，全部离线）

### 1. AST 结构编辑距离（冻结判据 τ=0.25）

方法：对锁定案例每个 coder 步提取候选代码 → 匿名化用户标识符 →
AST dump 分词 → 归一化 Levenshtein。脚本 setup_env/ast_structure_distance.py，
输出 analysis/figures_data/ast_structure_distance.csv（逐步）+
ast_case_matrix.csv（逐案例）。关键结果：

| 案例 | 轨迹形态 | 结局 |
|---|---|---|
| v4_08@7B diverse、v4_08@3B diverse s2-4 | 第 3 候选跳至 0.6525（切族） | 救援成功 |
| v4_01@7B（structured/diverse/weak） | 全程 0.0（逐字锁定） | 全败 |
| v5_09@7B diverse | 缓慢漂移到 0.279（第 4 候选才跨 τ） | 未救回 |
| v2_13@3B diverse | 第 3 候选跳到 0.38 后停滞 | 未救回 |

**结论（入 §5.5/Fig 3）：结构切换（跨 τ）是救援的必要非充分条件**——
救援案例都在第 3 候选早切族（0.65），而迟切/切后停滞者均失败。
类型学三型获得量化判据支撑（C4 强化）。

### 2. 贝叶斯因子（§5.6 诚实统计地位）

方法：配对二元结果 McNemar 不一致对 (b,c)，H0: p=0.5，H1: Beta(1,1)
先验，BF10 = b!c!2^(b+c)/(b+c+1)!。脚本 setup_env/bayes_factors.py，
输出 analysis/figures_data/bayes_factors.csv。关键行：

| 比较 | b/c | BF10 | 解读 |
|---|---|---|---|
| 7B repair vs no_feedback | 2/1 | 0.67 | inconclusive（偏 H0）|
| 3B repair vs no_feedback（E6 R1） | 6/0 | 9.14 | moderate for H1 |
| 7B repair vs direct（重试效应） | 11/2 | 7.50 | moderate for H1 |
| 3B repair vs direct | 12/0 | 315.1 | decisive for H1 |
| 池化 diverse vs structured（锁定，7B） | 3/0 | 2.0 | inconclusive |
| 池化 diverse vs weak（锁定，7B） | 3/0 | 2.0 | inconclusive |

**写作立场（已定）**：干预效应主张不建立在 p 值/BF 显著性上
（n 小，BF 仅 inconclusive），而是建立在**确定性复现证据**上
（v2_11 5/5、v4_08@7B 5/5 救援 tokens 逐位一致、weak 同单元 0 救援
的归因分离）；BF 用于如实量化频率学证据强度。

### 3. 图表产出（matplotlib + Times New Roman，每图配 CSV）

脚本 setup_env/make_figures.py（bash setup_env/make_figures.sh），
pdf.fonttype=42 保证文字可在 Visio/Illustrator 中编辑。

| 图 | 内容 | 文件（figures/） |
|---|---|---|
| Fig 1 | 6 臂成功率 7B vs 3B + McNemar/BF 标注；7B weak 臂仅锁定子集（n=27，1/27，斜纹标注） | fig1_feedback_dissection.pdf/.png/.csv |
| Fig 2 | 47 锁定单元 × 3 干预臂救援矩阵（diverse：v2_11 5/5、v4_08@7B 5/5、v5_04 s1、v4_04 s1/s4、v4_08@3B 3/5；weak 仅 v4_04 s1） | fig2_rescue_matrix.pdf/.png/.csv |
| Fig 3 | 五案例 AST 距离轨迹 + τ=0.25 线（"切换必要非充分"） | fig3_ast_typology.pdf/.png/.csv |

数字全部从 runs/*/metrics.jsonl 重新计算（非手录），已与日志定版
核对一致（Fig 1：7B 84/93/92/95/100，3B 70/82/76/80/80/80）。

## 下一步

1. ~~AST 结构编辑距离离线分析~~ ✔
2. ~~贝叶斯因子计算~~ ✔
3. ~~paper-figure（Fig 1-3 + CSV）~~ ✔
4. paper-write → paper-compile。

## 论文写作进度（2026-08-18）

paper/ 目录已按 ICLR 结构完成起草（自写等效 iclr2026_conference.sty，
官方样式不可达，正式投稿前需替换）：

- 正文 §0-§7 + 附录 A 全部成稿（sections/0_abstract … A_appendix）。
  附录含正文引用的三个标签：app:prompts（中文 prompt 原文，CJKutf8）、
  app:e6（E6 跨模型结果 + v4_08 取证）、app:ast（AST 方法与案例矩阵）。
- references.bib 18 条，逐条经 web 检索核验元数据（网络受限，DBLP
  直连超时）。其中 3 条 arXiv 号未能独立确认（jimenez2024swebench、
  huang2024selfcorrect、gou2024critic）、alagarsamy2024testgen 作者
  列表不全——均已标注 [VERIFY]，投稿前需复查。
- 静态审计完成：\ref 全部闭合、18 引用键↔bib 全匹配、正文数字与
  本日志定版逐一核对一致。终审抽查补完：§5.3 E4 名义 n=22/
  54.5%/b=c=12/0/p=0.00049、hash 去重后 8 单元 p=0.25（E4 节 ✓）；
  §5.4 weak 池化 n=27、1/27（图表节 ✓）；§5.6 BF 表六行与
  bayes_factors 定版逐行一致含 BF01 倒数 ✓；Related Work 四段
  ≥1 页 ✓。
- 编译验证完成（2026-08-18，Windows 本机 TeX Live 2026，latexmk）：
  main.pdf 15 页 = 正文 8 页（References 自第 8 页起，满足 ≤9 页限制）
  + 参考文献 2 页 + 附录 5 页。编译期修复三处：①\pp/\BF 宏加
  \ensuremath（文本模式调用报 \mathrm 错）；②references.bib 内
  联 % 注释改 @comment 并移到条目外（BibTeX 不认 %）；③fig2
  救援矩阵超高（260×887pt）改用 height=0.86\textheight 约束。
  附录中文经 CJKutf8+arphic gbsn 正确嵌入。剩余警告均为无害项
  （caption 未知文档类、hyperref 空链接、两处 <1.2pt overfull）。
  论文写作阶段（paper-write）完成。

## 2026-08-18：auto-paper-improvement-loop 两轮审稿润色完成

- 流程：MAX_ROUNDS=2，每轮零上下文新审稿人（llm-reviewer MCP 不可用，
  降级 GeneralPurpose 子代理；不告知上轮修改）。备份 main_round0_original.pdf。
- Round 1：4/10（W1-W12，两条 CRITICAL：section 命令缺失致交叉引用全断、
  "5/5 seeds" 与自身单元口径矛盾）。修复：全部补 \section；单元口径统一
  （2/2 units + partial + 3/5@3B）；power 陈述；app:recon 对账表；token
  分母；判据改 escape-from-failing-family；预注册载体声明；补 Self-Edit/
  xia2023apr（arXiv API 核验，纠正错误 id 2210.07553→2210.14179）。
- Round 2：分数未持久化（上下文压缩，不虚构）。修复：任务级敏感性分析
  （analysis/task_level_sensitivity.py → 附录 D.2，不改预注册主分析）；
  related work 补 test-time compute 段（brown2024monkeys/snell2024testtime）；
  alagarsamy2024testgen 经 dblp 核验补全；BF 表与干预指令英文全文移附录；
  正文从 10 页压回 9 页。
- 终态：main_round2.pdf，17 页 = 正文 9 页（Conclusion 完整收于第 9 页）
  + 参考文献 2 页 + 附录 6 页；0 undefined refs/citations；2 处 ≤1.2pt
  overfull（无害）。详见 paper/PAPER_IMPROVEMENT_LOG.md。
- 遗留：图 2/3 被 LaTeX 延迟排至附录区（p16/17），投稿前人工终审浮动位置。

## 2026-08-18：第二轮审稿循环（Round 3/4）与证据级弱点诊断

- Round 3：5/10（C1/C2 CRITICAL + M1-M5）；Round 4：6/10 Weak Accept
  （W1 CRITICAL 证据为 case-report 级 K=2；W2 无外部基准；W3 非
  compute-matched；W4 确定性解码需显式 scope；W5 种子索引歧义已用
  原始数据裁决）。全部写作可修复项已关闭；剩余 W1-W3 为实验缺口。
- 裁决：停止润色，进入补证据阶段。启动 E7/E8，预注册如下
  （**规则冻结于任何 E7/E8 数据观察之前**）。

---

# E7 预注册：compute-matched best-of-N 基线（关闭 W3）

**问题**：等 token 预算下，采样式 test-time compute（best-of-N + 测试
验证器筛选）能否替代/胜过修复循环，尤其是在锁定单元上？

## 设置（与 E0-E6 对齐）

- 模型 7B-AWQ；锁定臂 temp 0.2；T_max=5；50K tokens/实例；反馈 6K 字符。
- 数据集：v2（20 题，主分析）+ v4 粘滞套（锁定单元定向分析；
  锁定集沿用 E4v4 冻结筛查结果，不重新筛查）。
- 循环臂（新跑，5 seeds，协议同 E4v4）：structured / diverse / weak。

## best-of-N 臂（两个预先注册的多样性机制）

1. `bestofn_seed`：逐个 one-shot 候选，seed 递增（0..9），temp 0.2
   ——与论文其余部分的多样性来源一致（seed 变化）。
2. `bestofn_temp`：seed=None，temp 0.8 ——标准 best-of-N 机制。

**逐实例预算匹配（主规则）**：对每个实例 i，以同 E7 运行中配对的
diverse 臂实际耗 token T_i 为预算；从第一个 one-shot 候选起累计，
达到或超过 T_i 即停（硬上限 N_max=10）。成功 = 任一已采样候选通过。
**多样性审计（预设，无条件报告）**：每实例唯一候选数（按文本 hash
去重）与采样数之比，两个机制分别报告。

## 终点与阈值

- **P1（主，锁定单元）**：diverse vs bestofn_seed / bestofn_temp 的
  救援结果。样本小（8 单元），裁决口径同 §5.6：逐单元结果 + 确定性
  描述，不宣称频率显著性。
- **P2（次，v2 全集）**：structured vs 两 best-of-N 臂成功率，
  精确 McNemar，冻结阈 p<0.025 且 Δ≥3pp。
- **S1（公平性核查）**：逐实例实际耗 token 比值（best-of-N/循环），
  报告均值与分位数。

## 解释树（冻结）

1. bestofn_temp 产生多样候选但救不回 diverse 能救的锁定单元 →
   支持"预算内指令引导的族切换 > 盲采样"，强化 C2/C3；同时报告
   seed 机制在确定性解码下的退化（预期唯一候选率≈1）。
2. bestofn_temp 救回同等或更多锁定单元 → 干预效应可被温度随机性
   替代；诚实降级 C2/C3 表述，重写为"任何多样性来源均有效，
   指令的价值在于免升温/免额外采样"。
3. temp 0.8 采样在本 harness 下零多样性（同 tempbump 实现层 null）→
   如实报告为实现边界，compute-matched 比较限定于本 harness，
   并在论文声明该限定。

---

# E8 预注册：外部基准 lock-in 患病率与干预迁移（关闭 W2）

**问题**：repetition lock-in 在标准外部基准（HumanEval）上是否存在？
触发式干预能否迁移？

## 设置

- 数据：data/humaneval.jsonl（164 题，已从 ModelScope vendored）。
- 协议适配（generate-test-revise）：attempt 1 = one-shot 函数补全
  （提示词与 smoke_humaneval 一致）；执行 = prompt+补全+test+check
  入沙箱（timeout 15s）；失败后给结构化反馈（断言/traceback 解析，
  实现于跑数前冻结）进入修正轮，T_max=5。
- 冻结格式护栏：抽取代码若不含 `def {entry_point}` 则前置
  entry["prompt"]（同 smoke 脚本），避免格式伪迹被计为行为锁定。
- 臂：direct / repair_structured / repair_diverse / repair_nudge_weak；
  5 seeds；temp 0.2；预算同 E0。
- 锁定判据（沿用冻结定义）：structured 臂下失败且 rep≥2。

## 终点与阈值

- **P1（主）**：lock-in 患病率 = structured 锁定 seed-实例 / 全部
  seed-实例，Clopper-Pearson 95% CI；同时按轨迹 hash 去重报告
  单元级患病率（E4 教训预应用）。
- **P2**：锁定实例上 diverse vs structured，精确 McNemar，阈
  p<0.025 且 Δ≥3pp；若锁定实例 <10，裁决改为描述性 + 确定性单元
  报告（同 §5.6 惯例）。
- **P3**：锁定实例上 diverse vs weak，同 P2 规则。
- **S1**：loop gain：structured vs direct，同阈值。
- **S2（确定性审计，无条件报告）**：锁定实例跨 seed 轨迹 hash 一致率。

## 中期规则（预设的算力保护，非事后选择）

seeds 0-1 全臂跑完后：若 ≥90% 失败 structured 轨迹在两 seed 间
byte-identical（确定性体制），seeds 2-4 仅跑锁定实例及其配对对照；
否则 5 seeds 全量。

## 解释树（冻结）

1. 患病率 ≥5% 且干预同向 → lock-in 外部效度成立 + C2/C3 部分迁移，
   新增 claim C6。
2. 患病率 <2% → HumanEval 对该模型过易（预期 pass@1 高），锁定在
   简单外部任务上稀有；如实报告，MBPP/更难题集列为 future work。
3. 患病率 ≥5% 但干预无效 → 救援边界：外部基准失败多为深层锁/能力
   缺口而非策略粘滞；如实报告并精化 typology 边界。

**执行顺序**：E7 先行（1-2 天）；E8 随后（含中期规则后约 1 天）。
均通过 setup_env/ 脚本在 WSL2 vLLM（localhost:8000）上执行。

---

# E7 裁决记录（2026-08-18，按冻结解释树执行）

数据：runs/E7/{v2,v4}/seed{0..4}/{loop 三臂, bestofn_seed, bestofn_temp}。
裁决脚本 scripts/analyze_e7.py（McNemar 精确检验、冻结锁定集 E4V4_LOCKED
硬编码，不从新数据重新推导）。

## 结果

**v2 全集（100 seed-实例）**：structured 95.0%、diverse 100.0%、
weak 95.0%、bestofn_seed 85.0%、bestofn_temp 90.0%。
- P2：structured vs bon_seed Δ=−10.0pp，b=0/c=10，exact p=0.0020 →
  **SIGNAL（过冻结阈）**；vs bon_temp Δ=−5.0pp，b=5/c=10，p=0.3018 →
  **null（未过冻结阈）**。

**v4（60 seed-实例，全集对比非冻结终点，仅描述）**：structured 75.0%、
diverse 86.7%、weak 76.7%、bon_seed 58.3%、bon_temp 78.3%。

**P1 冻结锁定单元（14 个，E4v4 筛查）**：
- v4_01×5：四臂全 FAIL（深锁，typology 不可救型，与 E4v4 一致）。
- v4_04@s1/s4：diverse PASS、bon_seed FAIL、bon_temp PASS。
- v4_05@s0/s4：diverse FAIL、bon_seed FAIL、bon_temp PASS（2 单元
  为 bon_temp 独有救援）。
- v4_08×5：diverse PASS 5/5（完整复现 E4v4）、bon_seed FAIL、
  bon_temp FAIL（盲采样救不回）。
- diverse 救回而 bon_seed 失败：7 单元；diverse 救回而 bon_temp
  失败：5 单元；bon_temp 救回而 diverse 失败：2 单元（v4_05）。

**S1 公平性**：bon 实际耗 token/匹配预算 mean=1.54--1.74（冻结停止
规则的首超即停导致系统性超支，如实报告；即 bon 臂算力略多于循环臂，
仍不胜出，比较方向保守）。

**多样性审计（无条件）**：unique_ratio bon_seed=0.509(v2)/0.551(v4)，
bon_temp=0.711(v2)/0.730(v4)。seed 机制在 temp 0.2 下显著退化；
v4_01/v4_08 等深锁实例 bon_seed 常出现 n 个候选全同（unique=1）。

**harness 复现性**：E7 loop 阶段 diverse v2 20/20、v4_08 救援 5/5，
与 E4v4 论文数字一致。

## 解释树裁决

**分支 1 成立（主裁决）**：bon_temp 产生了真实多样的候选
（unique_ratio≈0.71-0.73），但救不回 diverse 能救的 v4_08×5 深锁单元；
bon_seed 在确定性解码下退化（unique_ratio≈0.51-0.55，锁定单元救援 0/14）。
支持「预算内指令引导的族切换 > 盲采样」，强化 C2/C3。

**诚实细化（必须入论文）**：bon_temp 救回了 diverse 救不回的
v4_05@s0/s4（2 单元）——温度随机性对部分浅层锁有独立救援能力；
干预的价值因此精确表述为「在深锁/粘滞单元上的定向救援 + 免升温、
免额外采样的效率」，而非「任何盲采样都无效」。分支 2 不成立
（bon_temp 4/14 < diverse 7/14），C2/C3 不降级。分支 3 不成立
（temp 0.8 有真实多样性）。

**P2 结论**：v2 上循环（structured）显著优于同预算 seed 盲采样
（p=0.002）；与 temp 盲采样差异未过冻结阈。W3（compute-matched）关闭。

---

# E8 中期规则执行记录（2026-08-18，非最终裁决）

**中期规则判定：NO TRIGGER**。seeds 0-1 全臂跑完后，在两个 seed
均失败的 structured 任务共 22 个，跨 seed 轨迹 byte-identical 者
13 个（59%），低于冻结的 90% 阈值 → 非确定性体制，按预注册原文
执行 **seeds 2-4 全量**（不得缩减为只跑锁定实例）。

**seeds 0-1 快照（仅供监控，不构成裁决）**：
- 四臂 pass：direct 86.0%、structured 86.0%、diverse 87.2%、
  weak 86.3%（各 328 seed-实例）。
- P1 患病率（冻结判据）：45/328 = 13.72%，Clopper-Pearson 95%
  CI [10.19%, 17.92%]，涉及 24 个不同任务 —— 解释树分支 2
  （「HumanEval 过易」）已被数据排除（患病率 ≫ 5%）。
- S2：锁定 ≥2 seeds 的任务 21 个，跨 seed hash 一致 13 个
  （62%）—— 确定性锁定与非确定性失败混合存在。
- P2/P3 当前为 null（diverse 救回 4/45，方向正向但未过阈）；
  最终裁决待 5 seeds 齐后按冻结阈值执行。
- 轨迹 hash 去重：45 锁定单元含 32 个不同轨迹（E4 教训的
  去重核算已预应用）。

**执行**：seeds 2-4 全量已启动（run_e8.sh --seeds 2,3,4），
完成后执行完整裁决并归档。

---

# E8 完整裁决记录（2026-08-18，5 seeds，按冻结阈值执行）

**数据完整性**：20 个 metrics.jsonl（5 seeds × 4 臂），各 164 行，
每臂 820 个 seed-实例。完整裁决如下（analyze_e8.py，冻结阈值）。

**四臂 pass（820 seed-实例/臂）**：direct 86.2%、structured 86.6%、
diverse 87.3%、weak 86.7%。

**P1 患病率（冻结判据 struct fail & rep≥2）**：107/820 = 13.05%，
Clopper-Pearson 95% CI [10.82%, 15.55%]，涉及 25 个不同任务。
远超冻结的 5% 下限 → **解释树分支 2（「HumanEval 过易」）被排除**，
lock-in 现象在外部基准上**外部效度成立**。去重核算：107 锁定单元
含 42 个不同轨迹 hash（E4 教训的去重已预应用）。

**S1 loop gain（structured vs direct，全集）**：86.6% vs 86.2%
（Δ=+0.4pp，b=14/c=11，exact p=0.690）→ **null**。HumanEval 对
loop 修复而言足够易解，修复在聚合层面不产生净增益——loop 的作用
被限定在锁定实例上。

**P2 diverse vs structured（锁定单元，exact McNemar）**：
0.0% vs 5.6%（Δ=+5.6pp，b=6/c=0，p=0.0312）。**按冻结阈值
p<0.025 判 null**。方向为正、Δ 过阈（≥3pp），但 p 距阈值仅一步。

**P3 diverse vs weak（锁定单元）**：0.9% vs 5.6%（Δ=+4.7pp，
b=5/c=0，p=0.0625）→ **null**。

**S2 确定性审计（无条件报告）**：锁定 ≥2 seeds 的任务 24 个，
跨 seed 轨迹 byte-identical 者 11 个（46%）。lock-in 为
确定性陷阱与 seed 敏感失败的混合体。

**解释树裁定**：P1 成立（现象真实且外部可迁移）；P2/P3 干预
方向为正但按冻结规则**未过阈** → 落入**分支 3（救援边界）**。
如实报告方向性证据（p=0.0312 距阈值极近、方向一致），
**不做任何事后阈值放宽**——预注册纪律要求 null 即 null。

**一句话结论**：lock-in 现象本身获得外部基准验证（患病率 13%），
但多样干预在 HumanEval 上仅有弱方向性支持、未达冻结显著性，
属诚实的边界性结果。
