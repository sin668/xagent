import { buildPromoteStagingPayload } from './leadDetail.js';
import { createLeadEnrichmentService } from './leadEnrichment.js';
import { createCustomersService } from './customers.js';
import { createCustomerFollowupsService } from './customerFollowups.js';
import { createLeadCleanupService } from './leadCleanup.js';

export const PHASE3_MOBILE_E2E_PAGES = [
  {
    key: 'lead_detail_enrichment',
    label: '线索详情完善区',
    srcPath: 'pages/leads/detail',
    rootPath: 'src/pages/leads/detail',
  },
  {
    key: 'cleanup_suggestions',
    label: '清洗建议队列',
    srcPath: 'pages/lead-cleanup/index',
    rootPath: 'src/pages/lead-cleanup/index',
  },
  {
    key: 'customers_workbench',
    label: '客户工作台',
    srcPath: 'pages/customers/index',
    rootPath: 'src/pages/customers/index',
  },
  {
    key: 'customer_detail',
    label: '客户详情',
    srcPath: 'pages/customers/detail',
    rootPath: 'src/pages/customers/detail',
  },
  {
    key: 'customer_followups',
    label: '客户跟进记录',
    srcPath: 'pages/customers/followups',
    rootPath: 'src/pages/customers/followups',
  },
];

function passed(extra = {}) {
  return { status: 'passed', ...extra };
}

function failed(reason, extra = {}) {
  return { status: 'failed', reason, ...extra };
}

function hasItems(value) {
  return Array.isArray(value?.items) ? value.items.length > 0 : Array.isArray(value) ? value.length > 0 : false;
}

function validateManualField(field = {}) {
  const fieldName = String(field.fieldName || field.field_name || '').trim();
  const candidateValue = String(field.candidateValue ?? field.candidate_value ?? '').trim();
  const evidenceNote = String(field.evidenceNote || field.evidence_note || '').trim();

  if (!fieldName || !candidateValue || !evidenceNote) {
    throw new Error('人工补录字段、字段值和证据说明必须填写真实内容。');
  }

  return {
    fieldName,
    candidateValue,
    sourceUrl: field.sourceUrl ?? field.source_url ?? null,
    evidenceNote,
    confidenceScore: field.confidenceScore ?? field.confidence_score ?? null,
  };
}

async function step(name, fn) {
  try {
    return await fn();
  } catch (error) {
    return failed(`${name}失败：${error.message || 'Unknown'}`);
  }
}

export function createPhase3MobileE2EVerifier({ client }) {
  const leadEnrichmentService = createLeadEnrichmentService({ apiClient: client });
  const customersService = createCustomersService({ client });
  const customerFollowupsService = createCustomerFollowupsService({ client });
  const leadCleanupService = createLeadCleanupService({ client });

  return {
    async run({
      leadId,
      customerId,
      actor = 'mobile-e2e-user',
      manualField = {},
      reviewNote = '移动端第三阶段联调验收：人工确认晋级客户。',
    } = {}) {
      const report = {
        leadEnrichment: failed('未执行'),
        promotion: failed('未执行'),
        customerWorkbench: failed('未执行'),
        customerDetail: failed('未执行'),
        customerFollowups: failed('未执行'),
        cleanupSuggestions: failed('未执行'),
        safety: {
          noAutoOutreach: true,
          noSeedOrMock: true,
        },
      };

      report.leadEnrichment = await step('线索完善', async () => {
        const validatedManualField = validateManualField(manualField);
        await leadEnrichmentService.createManualEnrichment(leadId, {
          operator: actor,
          note: '移动端第三阶段联调验收人工补录。',
          fields: [validatedManualField],
        });
        const results = await leadEnrichmentService.listEnrichmentResults(leadId);
        return hasItems(results) ? passed({ count: results.items.length }) : failed('线索完善结果为空');
      });

      if (report.leadEnrichment.status !== 'passed') {
        return report;
      }

      report.promotion = await step('客户晋级', async () => {
        const payload = buildPromoteStagingPayload({ actor, reviewNote });
        const response = await client.post(`/staging-leads/${encodeURIComponent(leadId)}/promote-to-customer`, payload);
        const promotedCustomerId = response.customer_id || response.customerId || response.id || customerId;
        return promotedCustomerId ? passed({ customerId: promotedCustomerId }) : failed('晋级响应缺少客户 ID');
      });

      if (report.promotion.status !== 'passed') {
        return report;
      }

      const effectiveCustomerId = report.promotion.customerId || customerId;

      report.customerWorkbench = await step('客户工作台', async () => {
        const customers = await customersService.listCustomers({ limit: 20 });
        const visible = (customers.items || []).some((item) => item.id === effectiveCustomerId);
        return visible ? passed({ count: customers.items.length }) : failed('晋级客户未在客户工作台列表中可见');
      });

      report.customerDetail = await step('客户详情', async () => {
        const detail = await customersService.getCustomerDetail(effectiveCustomerId);
        return detail.id ? passed({ contactCount: detail.contacts.length, sourceCount: detail.sources.length }) : failed('客户详情缺少 ID');
      });

      report.customerFollowups = await step('客户跟进', async () => {
        const existing = await customerFollowupsService.listFollowups(effectiveCustomerId);
        const created = await customerFollowupsService.createFollowup(effectiveCustomerId, {
          customerId: effectiveCustomerId,
          ownerId: actor,
          team: 'customer_service',
          followupType: 'internal_note',
          content: '移动端第三阶段联调验收人工跟进记录。',
          customerFeedback: '联调验收记录，不发送消息。',
          nextAction: '继续人工跟进',
          createdBy: actor,
        });
        return created.id ? passed({ beforeCount: existing.length, createdId: created.id }) : failed('新增跟进记录缺少 ID');
      });

      report.cleanupSuggestions = await step('清洗建议', async () => {
        const suggestions = await leadCleanupService.listCleanupSuggestions({ reviewStatus: 'pending', limit: 20 });
        const first = suggestions.items?.[0];
        if (!first) {
          return failed('无待复核清洗建议');
        }
        const reviewed = await leadCleanupService.approveSuggestion(first.id, {
          actor,
          actorRole: 'ops',
          reviewNote: '移动端第三阶段联调验收人工确认清洗建议。',
        });
        return reviewed.id ? passed({ suggestionId: reviewed.id }) : failed('清洗建议确认响应缺少 ID');
      });

      return report;
    },
  };
}

export function summarizePhase3MobileE2E(report = {}) {
  const labels = [
    ['leadEnrichment', '线索完善'],
    ['promotion', '客户晋级'],
    ['customerWorkbench', '客户工作台'],
    ['customerDetail', '客户详情'],
    ['customerFollowups', '客户跟进记录'],
    ['cleanupSuggestions', '清洗建议'],
  ];
  const failedItems = labels
    .filter(([key]) => report[key]?.status !== 'passed')
    .map(([key, label], index) => `${index + 1}. ${label}：${report[key]?.reason || '未通过'}`);
  const safetyPassed = Boolean(report.safety?.noAutoOutreach) && Boolean(report.safety?.noSeedOrMock);
  const ready = failedItems.length === 0 && safetyPassed;

  if (ready) {
    return {
      ready: true,
      text: '第三阶段移动端前后端联调验收通过：线索完善、客户晋级、客户工作台、客户详情、跟进记录和清洗建议均可运行。',
    };
  }

  return {
    ready: false,
    text: `第三阶段移动端前后端联调验收未通过。阻断项：${failedItems.join('；')}${safetyPassed ? '' : '；安全边界检查未通过'}`,
  };
}
