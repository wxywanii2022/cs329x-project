# RQ1 assessment pipeline / 组员模型交接

## 1. 范围与当前状态

本模块按照项目的 RQ1 流程实现：**decision point × behavior → 截断可见证据 → 独立模型调用 → 标签与证据校验 → 保存原始记录 → 与 A、B、裁决标签分别比较**。

- 不推断整个人的能力，不把缺失机会或缺失证据打成 0。
- 每次只评一个行为；B1/B2 即使共用同一个 user turn，也分别调用。
- 输入不含背景档案、其他标注、答案、最终产物或预设 opportunity 状态。
- 模型自行判断 opportunity；判断错了仍是一个应被评估的预测，不会被环境真值强制纠正。
- 一次调用使用一个独立 session ID；adapter 必须无共享历史、无工具、无外部检索。
- 真人参考文件仅在离线 evaluate/compare 阶段读取，不进入模型请求。
- **组员模型尚未配置，也未进行真实模型验证。** `configs/assessment.team.example.json` 的 `model` 为 null；run 会明确报错，绝不自动选择其他模型。
- 离线 mock 仅是词汇规则 fixture，不能用于判断规则准确性、模型可靠性或学习效果。

这是 assessment 接入，不是把整个 simulation 宣布为正式研究就绪。现有 outcome evaluator 仍一次读取完整任务记录，只约束引用不能越过 decision point；其输入隔离仍需另行改造。其 oracle opportunity 仅适合受控 outcome calibration，不等于 RQ1 机会识别。

## 2. 规则版本

### 真实日志：v0.2

`src/adaptive_tutor/rq1/rubrics/specification_verification_v02.md` 是之前已冻结文件的逐字节副本，SHA-256：

`046ceb7bc8fb5035ebd347c56e3a16b4b8240deb4d3279904bf4a77bfb845e1d`

运行时检查这个哈希。用户粘贴的 proposal/Protocol 包含较早或简写措辞，没有静默替换已冻结规则。输出 schema 的说明附在完整规则后面，不改变评分标准。新的 assessment 调用不再使用旧的 `prompts/assessment_v1.txt`；修改提示词时应查看 `rq1/core.py` 和对应 rubric，而不是修改未使用的旧文件。

### 模拟任务：sim-opportunities-v1

保留仓库的 candidate adaptation（learner 向 task assistant 传达要求和证据标准）。它与 v0.2 的 B1/B2 N/A 例外有差别，**仍需团队批准和独立校准**。不能把在 v0.2 上的表现直接视为该模拟版本已经验证。

`assessment.py` 在 simulation 内调用同一个核心函数，但明确选择模拟 rubric。每个 pre-task 的 assessment 从一次合并调用改为 B1–B4 四次独立调用，模型调用预算应据此重算。

## 3. 最短本地运行

```bash
cd cs329x-project  # 你的本地 clone 目录
source .venv/bin/activate
# 初次安装或新增 CLI 后重新安装；也可使用 uv pip install -e .
python -m pip install -e .
```

如果该 venv 不带 pip，使用 `uv pip install --python .venv/bin/python -e .`。

```bash
# 全部是合成样例，无私人日志、真实标注或付费调用。
tutor-assess validate --items examples/assessment_items.synthetic.jsonl

tutor-assess run \
  --items examples/assessment_items.synthetic.jsonl \
  --config configs/assessment.mock.json \
  --output outputs/assessment-final

tutor-assess audit --run outputs/assessment-final

tutor-assess evaluate \
  --run outputs/assessment-final \
  --reference examples/assessment_reference.synthetic.csv \
  --reference-provenance synthetic-fixture \
  --save outputs/assessment-final/agreement.synthetic.json

python -m unittest discover -s tests -v
```

代码、输入、规则或模型参数变化后，必须使用新 output 目录。不要覆盖先前的 pilot、A/B 草稿或裁决。

**真实标注数据（Main 1，60 条）** 已转换到 `data/rq1/main60/`：输入、A/B 原始标签、最终裁决标签（`reference_adjudicated.csv`）、一致性和使用限制见 [该目录 README](../data/rq1/main60/README.md)。这些标签只用于评估，不能用于训练或调 prompt。

## 4. 输入格式和证据边界

一个 JSONL 行对应一个 decision point × behavior：

```json
{
  "item_id": "example-001",
  "session_id": "pseudonymous-session-01",
  "participant_id": "pseudonymous-participant-01",
  "agent": "source-agent",
  "behavior": "B3",
  "target_turn_id": "u2",
  "visible_instructions": "",
  "messages": [
    {"turn_id":"a1","role":"assistant","content":"The increase was 35%."},
    {"turn_id":"u2","role":"user","content":"Where does the 35% come from? Recalculate it."},
    {"turn_id":"a3","role":"assistant","content":"This future reply is removed before inference."}
  ]
}
```

- messages 按原始发生顺序，不按 ID 的数字或字典序重排。输入可以包含后续消息，构造请求时在目标 user turn 停止。
- 每条消息仅含 `turn_id, role, content`；角色允许 user/assistant/tool/system/evidence。这里的 system 是日志中的可见文本，不会被提升成模型的 system prompt。
- 空消息和以 `/` 开头的 user command 被排除；不能选择它们作为目标。
- `visible_instructions` 只能是目标回合前已可见的实际任务文本，不能放答案、评分 rubric、隐藏任务信息或后来补充的要求。程序无法判定上游文本是否真实可见，数据整理人员必须核对来源。没有独立任务字段时可以留空，保留用户请求本身即可。
- item/session/participant/agent 等用于本地索引和分组，不进入模型 payload。真实数据应预先完成稳定脱敏；不要随意改写证据语义。
- 输入文件不允许夹带 label/reason/background 等顶层字段。不要把工作簿标注直接混进推理 JSONL。
- 找不到 target 是输入错误，不自动记成 N/A。仅当整段记录明确缺失时，允许 `target_turn_id: null, messages: [], visible_instructions: ""`，并要求模型给出 insufficient_evidence。
- 原有自由文本 `items.blind.jsonl` 不是直接兼容格式。接入前须从已核验、已脱敏的源事件重建结构化消息并核对 cutoff；不要盲目通过正则拆分转录文本。本次没有迁移或发布原 60 条数据。
- 本模块不重新抽样。≥2 个合格 user turns、按 agent 分层、每 session/behavior 最多两个点等抽样条件，仍应在源数据选择清单中验证；目标前缀本身无法证明整个 session 的资格。

## 5. 模型输出

内部统一使用 JSON null 表示 N/A；CSV 导出为文字 `N/A`。

```json
{
  "behavior": "B3",
  "label": 2,
  "opportunity_status": "available",
  "na_reason": null,
  "reason": "The user selects the 35% claim and requests recalculation.",
  "confidence": "high",
  "unclear_rule": "",
  "evidence": [{"turn_id":"u2","quote":"Where does the 35% come from? Recalculate it."}]
}
```

校验范围：行为匹配、类型、标签/机会/N/A 原因一致、置信度枚举、引用 ID 在可见前缀内、quote 是原文子串。**这些是结构与证据存在性校验，不保证语义判断正确。** 语义仍需独立人工校准。

非法 JSON、模型 ID 不匹配、超限、伪造/越界引用等记录为 failed，不记成 N/A，不通过重新生成挑一个更方便的标签。可解析的适配器响应（包括不合格的 annotation）、usage 和失败原因保留在 journal。如果适配器连外层 JSON envelope 都未返回，程序只记录失败；不会盲目复制可能含密钥的 stdout/stderr，也无法凭空补出 usage。Reason 应简短、转述身份信息，不能包含个人名、账号或路径。

## 6. 你应该向组员要什么

最重要的是先确认他交付的是 **模型服务、可运行推理程序、模型权重，还是一套已有 assessor**。不一定需要权重：有可复现的 API/CLI 就足以接入。

### 必须提供

| 内容 | 具体要什么 | 为什么需要 |
| --- | --- | --- |
| 调用方式 | API endpoint + request/response 示例，或命令行程序 + 运行步骤；权重交付则需要加载代码、tokenizer、依赖和硬件要求 | 决定适配方式，避免默认是 Chat Completions |
| 固定模型身份 | exact model ID/checkpoint revision、base model、fine-tuning 版本；最好有权重或版本哈希 | 复现实验，避免别名悄悄切换版本 |
| 输入能力 | 是否接受完整 system rubric 和一段对话；最大上下文、JSON 输出、是否需要固定 chat template | 确认能正确处理真实 prefix 和冻结规则 |
| 任务语义 | 是通用 LLM 还是已训练的分类器；已有类别定义、N/A 处理、是否判断 opportunity | 不能把旧 label 编码或旧 rubric 误当成 v0.2 |
| 输出能力 | 标签、简短理由、证据、confidence/概率能否返回；一条脱敏成功响应 | 对齐合同；不要伪造模型不支持的置信度或解释 |
| 训练/调参数据范围 | 用过哪些 participants、sessions、pilot/main items；是否接触我们的 A/B/裁决标签；固定 prompt 在哪些案例上调过 | 排除数据泄漏，构造真实 held-out test |
| 参数支持 | temperature/top_p/seed、max output tokens、支持/不支持哪些参数，实际返回 model ID 与 usage 格式 | 避免 API 不支持参数或偷偷走默认值 |
| 运行约束 | 速率、并发、超时、成本；数据保留政策；鉴权变量名和安全获取方式 | 限额和隐私管理，不把密钥写进仓库 |

### 还应确认

- 是否无状态；每个 request 是否会继承之前的会话、缓存内容、工具或检索结果。我们的标准是不继承其他 item 的内容、不浏览、不调用外部工具。
- 模型的答案解释和 confidence 是原生输出、分类概率映射，还是外部规则生成？三者必须区别记录。若它只输出类别，先定义一个明确的 label-only 评估接口或修改合同；不要用另一模型补理由后声称全部来自原 assessor。
- 如输出是 classifier logits，需要 label-index mapping、校准方式与 checkpoint 版本。不能把 `class 0` 擅自解释成行为标签 0。
- 是否能用 2–3 个合成样例先做接口测试。这里测试 JSON/参数/引用能力，不据此宣称准确率。

### 可以直接发给组员的话

> 我这边已经搭好 RQ1 assessment pipeline：每次输入一个行为和截至目标 user turn 的对话，输出 2/1/0/N/A、简短理由、confidence 和证据。模型位置先留空。你能提供可运行的 API 或 CLI、固定 model/checkpoint 版本、输入输出样例、上下文限制和支持参数吗？另外请说明模型/提示词用过哪些训练和调参数据，尤其有没有用我们这 20 条 pilot 或新增 60 条，以及 participant/session 范围。我们要保证测试集不重叠。密钥不要放 GitHub，用安全渠道或本地环境变量配置就可以。如果模型只能输出类别或 logits，也告诉我，不用先拼造解释字段。

## 7. Adapter 合同

沿用项目的 JSON-over-stdio `command` adapter，详细公共协议见 [adapters.md](adapters.md)。

输入外层包含：
- `protocol_version: "1"`, `role: "assessment"`
- `session_id`：每个 decision point 独立。
- `system_prompt`：完整版本化 rubric + 单行为 JSON 合同。
- `prompt_version: "decision-point-v1/v0.2"`（模拟器使用对应 sim 版本）
- `payload`：仅 `behavior,target_turn_id,messages,visible_instructions,rubric_version`。
- `model`：exact model ID、temperature、supports_seed。
- `sample_seed` 和 `limits`。

stdout 必须只返回以下 envelope；日志写 stderr（不要输出密钥）：

```json
{
  "output": {"behavior":"B3","label":2,"opportunity_status":"available","na_reason":null,"reason":"The user requests a calculation check.","confidence":"high","unclear_rule":"","evidence":[{"turn_id":"u2","quote":"Recalculate it."}]},
  "usage": {"input_tokens":1000,"output_tokens":150,"estimated":false},
  "provider_request_id":"provider-request-id",
  "model_id":"EXACT_PINNED_ID",
  "tool_calls":[]
}
```

以上 token 数仅为协议示例，不是真实调用记录。若本地服务没有 provider request ID，adapter 应生成可追踪的调用 ID；估算 token 时必须 `estimated: true`，不能假装真实计数。

模型身份、参数和调用方式确定后，再把 `assessment.team.example.json` 复制成实际配置，并替换 null：

```json
{
  "adapter": "command",
  "model_id": "EXACT_PINNED_ID",
  "family": "DECLARED_MODEL_FAMILY",
  "command": ["/absolute/path/to/python", "-m", "team_assessor_adapter"],
  "temperature": 0,
  "supports_seed": false,
  "timeout_seconds": 120
}
```

这只是说明格式，仓库没有假装可用的团队模型模块。若服务支持现有 Chat Completions bridge，可使用 `python -m adaptive_tutor.adapters.http_bridge`，并在环境中设置 `TUTOR_ASSESSMENT_URL`、`TUTOR_ASSESSMENT_API_KEY`。模型不支持其参数或格式时，要改专用 adapter，不能盲目套用。密钥通过环境/Keychain 注入，禁止提交到 Git。

Simulation 中则在现有 `configs/live.example.json` 的 `models.assessment` 填同样的 ModelSpec；其它 role 仍需各自配置。原样例不代表四个 role 已经接入。

## 8. 验证与结果比较

```bash
# A/B 原标签：讨论前计算，不能自动生成裁决。
tutor-assess compare-human --left private/A.csv --right private/B.csv \
  --save outputs/agreement.A-B.json

# 对同一个模型 run，分别比较 A、B、裁决标签；结果文件分别保留。
tutor-assess evaluate --run outputs/rq1-run \
  --reference private/A.csv --reference-provenance model-assisted \
  --save outputs/rq1-run/vs-A.json
```

Reference CSV 最少两列 `item_id,label`。0/1/2/N/A 是有效标签；空白是未完成，不自动补 N/A。额外人工说明列不会进入模型。Reference 可是 run 的子集，报告会列出缺参考行、空白、失败和实际配对数量。

指标：raw agreement、unweighted Cohen's kappa、四类混淆矩阵、按行为分组、disagreement 列表。False-missed rate 的分母明确为成功配对中 reference 为 1/2/N/A 的数量，分子为其中模型预测 0 的数量。失败单独报告，不从失败中“补出”好看的标签。

`--reference-provenance` 是调用者声明，代码无法证明独立性。我们现有 P2-A 和新增 60 条 A 有模型辅助，不能声称它们是独立 human-only reference。原 20 条是 development/cross-version 探索性材料，不能当 held-out test。后续人工审核也不会消除原来的模型辅助来源。

### Participant-disjoint test

```bash
tutor-assess run --items private/test.jsonl --config configs/team.local.json \
  --split test --development-items private/all-development-items.jsonl \
  --output outputs/rq1-heldout-v1
```

test 模式要求开发/测试双方均有 participant_id，并检查 participant/session/item 不重叠。不能用 session_id 伪装 participant_id；缺失参与者身份时，应报告只能做到 session-held-out，不能冒称 participant-disjoint。此检查依赖团队提供完整、诚实的开发/训练暴露清单，无法检测未披露的训练数据。

## 9. 输出、恢复和隐私

- `frozen_inputs.json`：模型、参数、rubric、代码哈希、仅截至目标的输入和 split 检查。
- `events.jsonl`：请求、可解析的适配器 JSON 响应、usage、失败与逐项结果，hash-chain 校验。
- `predictions.jsonl`、`labels.csv`、`summary.json`：由 journal 重建的派生文件。CSV 对可能被 Excel 当公式执行的文本加前导单引号；精确原文保留在 JSON/journal，程序化读取优先使用 JSON。
- `evaluate` 的各 reference comparison 文件：独立保存，不回填或篡改 A/B/裁决。

输出目录设置为仅当前用户可访问，并应放在已忽略的 `outputs/` 中。请求/原始响应可能仍含敏感可见证据，脱敏与发布审查仍由数据负责人负责。推理不读取 `.env` 文件，也不会把环境变量写入请求或日志。

相同版本恢复时复用已完成/终止失败的调用；无效模型输出不会重新抽样。网络失败按固定 transport_attempts 重试；请求远端完成但本地未记录时无法保证 exactly-once。所有正式运行应记录成本与未知 usage 的限制。

## 10. 进入正式研究前仍需完成

1. 组员交付模型接口和数据来源清单；检查它能否遵循上述合同。
2. 在开发样本上校准规则和输出，不看 held-out 标签调 prompt。
3. 收集真正独立的 human reference，预先确定可接受误报率和失败策略。
4. 明确 simulation rubric 映射，并修复独立 outcome evaluator 的未来信息输入边界。
5. 扩充相同目标行为的不同指导深度，验证 learner profile，加入真正 held-out 任务。

接上模型不等于模型已经验证。当前 proposal 里“No AI tools were used for coding or experiments at this stage”只适用于更早阶段；本次代码及测试有 AI assistance，提交新版本报告时应更新披露。
