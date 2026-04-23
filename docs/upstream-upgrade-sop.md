# Upstream Upgrade SOP

本文档描述平台分支吸收上游 CowAgent 更新时的最小操作流程。

## 目标

- 尽量吸收上游功能和修复
- 尽量减少对平台层的破坏
- 让升级过程可重复、可回归、可审计

## 升级步骤

1. 拉取上游最新代码并建立独立升级分支
2. 优先查看 `docs/patch-register.md`
3. 对 patch register 中登记的文件逐个做差异比对
4. 先解决编译或导入错误，再处理行为兼容问题
5. 跑全量测试：
   `pytest -q`
6. 重点复核以下链路：
   - legacy `app.py` 启动
   - platform API 启动
   - platform worker 处理 job
   - web 控制台 `agent_id / binding_id` 路由
   - usage / quota / audit / doctor
7. 如果 patch 点发生变化，更新 `docs/patch-register.md`
8. 如果有新的重要架构取舍，新增或更新 `docs/adr/`

## 升级判定标准

满足以下条件才视为升级完成：

- 全量测试通过
- `cow platform doctor` 不报缺失治理文档
- patch register 已同步更新
- legacy 与 platform 两种模式都能正常启动

## 不建议的做法

- 不要在升级时顺手重构大量平台代码
- 不要把 legacy 和 platform 的问题混在一次提交里处理
- 不要绕过 patch register 直接修改上游核心文件
