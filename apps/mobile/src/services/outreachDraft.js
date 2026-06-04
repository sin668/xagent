const BLOCKED_RISK_LEVELS = new Set(['High', 'Forbidden']);
const FORBIDDEN_PATTERNS = [
  /финальн\w*\s+цен/i,
  /гарант\w*/i,
  /быстр\w*\s+достав/i,
  /таможенн\w*\s+оформлен/i,
  /безопасн\w*\s+оплат/i,
  /final price/i,
  /guarantee/i,
  /customs clearance/i,
  /payment safety/i,
  /delivery time/i,
  /最终价格/,
  /物流时效/,
  /清关/,
  /付款安全/,
  /交付周期/,
];

function isDoNotContact(lead) {
  return Boolean(lead?.doNotContact || lead?.do_not_contact || lead?.status === 'do_not_contact');
}

function riskLevelOf(lead) {
  return String(lead?.riskLevel || 'Unknown').trim();
}

function hasRefusalPath(draft) {
  return Boolean(String(draft?.refusalPath || '').trim());
}

function hasAudit(draft) {
  return Boolean(draft?.audit?.inputSaved && draft?.audit?.outputSaved);
}

function isExternallyUsableTemplate(draft) {
  return draft?.templateStatus === '可外发';
}

export function hasForbiddenCommitments(draft = {}) {
  const text = `${draft.subject || ''}\n${draft.body || ''}\n${draft.refusalPath || ''}`;
  return FORBIDDEN_PATTERNS.some((pattern) => pattern.test(text));
}

export function buildComplianceChecks({ lead = {}, draft = {} } = {}) {
  const riskBlocked = BLOCKED_RISK_LEVELS.has(riskLevelOf(lead));
  return [
    {
      key: 'no_forbidden_commitments',
      label: '未承诺价格/物流/清关/付款/交付周期',
      passed: !hasForbiddenCommitments(draft),
    },
    {
      key: 'has_refusal_path',
      label: '包含拒绝联系路径',
      passed: hasRefusalPath(draft),
    },
    {
      key: 'channel_allowed',
      label: '渠道风险允许人工触达',
      passed: !riskBlocked,
    },
    {
      key: 'customer_not_dnc',
      label: '客户未标记勿扰',
      passed: !isDoNotContact(lead),
    },
    {
      key: 'audit_saved',
      label: 'AI 输入输出审计已保存',
      passed: hasAudit(draft),
    },
    {
      key: 'template_approved',
      label: '模板状态可外发',
      passed: isExternallyUsableTemplate(draft),
    },
  ];
}

export function buildOutreachDraftViewModel({ lead = {}, draft = {} } = {}) {
  const blockReasons = [];
  if (isDoNotContact(lead)) {
    blockReasons.push('客户已标记勿扰');
  }
  if (BLOCKED_RISK_LEVELS.has(riskLevelOf(lead))) {
    blockReasons.push('渠道风险不允许触达动作');
  }

  const complianceChecks = buildComplianceChecks({ lead, draft });
  const allCompliancePassed = complianceChecks.every((check) => check.passed);
  const canGenerateDraft = blockReasons.length === 0;
  const canRecordSent = canGenerateDraft && allCompliancePassed;

  return {
    leadId: lead.id,
    customerName: lead.customerName || 'Unknown',
    channel: lead.channel || 'Unknown',
    riskLevel: riskLevelOf(lead),
    gradeLabel: lead.grade ? `${String(lead.grade).toUpperCase()} 级` : 'Unknown',
    draftId: draft.id || 'Unknown',
    templateId: draft.templateId || 'Unknown',
    versionLabel: `${draft.templateId || 'Unknown'} · ${draft.version || 'Unknown'}`,
    generatedAt: draft.generatedAt || 'Unknown',
    subject: draft.subject || 'Unknown',
    body: draft.body || 'Unknown',
    refusalPath: draft.refusalPath || '',
    riskTips: Array.isArray(draft.riskTips) ? draft.riskTips : [],
    audit: draft.audit || {},
    complianceChecks,
    blockReasons,
    canGenerateDraft,
    canRecordSent,
    manualOnly: true,
    autoSendEnabled: false,
  };
}

export function canRecordManualSend(viewModel, { humanConfirmed } = {}) {
  return Boolean(viewModel?.canRecordSent && humanConfirmed);
}

export function createManualSendRecord(viewModel, { humanConfirmed, sender, sentAt, channel } = {}) {
  if (!canRecordManualSend(viewModel, { humanConfirmed })) {
    throw new Error('Manual confirmation is required before recording sent outreach.');
  }

  return {
    leadId: viewModel.leadId,
    draftId: viewModel.draftId,
    templateId: viewModel.templateId,
    sender: sender || 'Unknown',
    sentAt: sentAt || new Date().toISOString(),
    channel: channel || viewModel.channel,
    status: 'sent_manual',
    autoSend: false,
  };
}
