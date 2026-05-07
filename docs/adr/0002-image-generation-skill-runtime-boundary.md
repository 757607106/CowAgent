# ADR 0002: 平台文生图复用 CoreAgent Skill 内核

## 状态

已采纳

## 背景

CoreAgent 2.0.7 新增内置 `image-generation` Skill，封装多厂商文生图、图生图和多图融合能力。
当前平台分支已经有租户级模型能力配置，用户在页面上按能力选择 `model / url / key`，运行时由 `CapabilityConfigService` 生成 Agent 覆盖配置。

如果平台继续保留旧的 `IMAGE_CREATE` 直连路径，同时再接入 2.0.7 Skill，会形成两套文生图执行逻辑：

- 平台 capability 配置和 Skill 配置各自解释模型
- 子进程环境变量和内存配置可能不一致
- 后续吸收上游 Skill 修复时需要同步维护两处执行入口

## 决策

平台文生图能力统一复用 CoreAgent 2.0.7 `skills/image-generation` 作为执行内核：

- `CapabilityConfigService` 仍是平台能力配置真源
- runtime overrides 写入厂商 key/base/model，同时写入 `skill.image-generation.model`
- `ImageGenerationService` 是平台 capability 文生图的唯一执行服务，负责调用 `image-generation` Skill 脚本
- `ChatChannel` 在平台 capability 文生图场景只委托 `ImageGenerationService`，不再拼 subprocess、环境变量或 Skill 参数
- Skill 子进程环境统一由 `build_runtime_environment()` 生成，平台 runtime scope 覆盖宿主环境变量
- legacy 非平台路径仍保持原有消息类型能力，不作为平台配置后的第二执行入口

## 结果

这样可以把平台配置、CoreAgent Skill 内核和上游 2.0.7 后续修复收敛到一条路径，减少重复逻辑。
代价是平台文生图依赖内置 Skill 存在；如果 Skill 缺失，应直接返回明确错误，而不是静默回退到另一套旧逻辑。

## 后续约束

- 新增图像生成厂商时，优先更新 Skill 与 capability provider 映射
- 不在 `ChatChannel` 内新增厂商级文生图分支
- 子进程型 Skill 必须复用 `build_runtime_environment()`，避免平台数据库配置被旧环境变量覆盖
