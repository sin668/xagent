# Story E6-S3 验证记录：C 级线索合规复核

## 验证时间

- 2026-05-28

## TDD 记录

- Red：`PYTHONPATH=apps/api pytest -q apps/api/tests/test_compliance_review_api.py`
  - 初始失败：`/compliance/reviews/pending` 与 `/compliance/customers/{id}/review` 返回 404。
- Red：`node --test apps/mobile/tests/complianceReview.test.mjs`
  - 初始失败：`apps/mobile/src/services/complianceReview.js` 不存在。
- Green：补齐后端合规接口、服务、schema、迁移和移动端合规服务/详情页展示后，专项测试通过。

## 验收清单

- [x] C 级线索进入报价/合同动作前显示合规复核状态。
- [x] 未复核时不能标记为已报价。
- [x] 复核记录包含复核人、时间、结论和风险备注。
- [x] 普通销售角色不可提交或覆盖复核记录。
- [x] 待复核队列可通过后端管理接口查询。
- [x] AI 只输出风险提示，不替代合规结论或法律意见。
- [x] 移动端详情页展示复核状态、复核人、复核时间、结论、风险备注和风险提示。

## 验证命令

- `cd apps/api && alembic upgrade head`
  - 结果：通过，已应用 `20260528_0006`。
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_compliance_review_api.py`
  - 结果：`2 passed, 8 warnings`
- `node --test apps/mobile/tests/complianceReview.test.mjs`
  - 结果：`2 passed`
- `PYTHONPATH=apps/api pytest -q apps/api/tests/test_compliance_review_api.py apps/api/tests/test_inventory_matching_api.py apps/api/tests/test_inventory_api.py apps/api/tests/test_customer_dnc_api.py`
  - 结果：`9 passed, 51 warnings`
- `npm --prefix apps/mobile run test`
  - 结果：`28 passed`
- `python -m compileall apps/api/app`
  - 结果：通过
- `node --check apps/mobile/src/services/complianceReview.js && node --check apps/mobile/src/data/complianceReviewSeed.js`
  - 结果：通过

## 两轮独立评审

### 第一轮评审

- 结论：发现 1 个非阻塞但实质 UI 逻辑问题，修复后复测通过。
- 发现项：移动端详情页在默认 B 级线索下继承了 C 级 seed 的 `quoteContractBlocked: true`，可能误显示非 C 级也被报价阻断。
- 修正结果：详情页按线索等级构造合规复核视图；非 C 级显示 `not_required` 且不阻断，C 级才使用待复核 seed 或真实复核记录。
- 复测：`node --test apps/mobile/tests/complianceReview.test.mjs` 通过；`npm --prefix apps/mobile run test` 通过。

### 第二轮评审

- 结论：未发现新增实质阻塞问题，Story 可收口。
- 复核点：后端 C 级自动入队、未复核报价阻断、合规角色审批、普通用户 403、AI 风险提示边界、移动端非 C 级不误阻断、勿扰/库存匹配回归。
- 修正结果：无新增修正。

## 残留风险

- 现有代码仍有 `datetime.utcnow()` 弃用警告，属于既有技术债，不影响本 Story 验收。
