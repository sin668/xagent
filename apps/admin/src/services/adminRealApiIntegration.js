const DOMAIN_LABELS = {
  prompt: 'Prompt 治理',
  knowledge: '知识库治理',
  emailReview: '邮件审核台',
  emailReplyQuality: '邮件回复质量',
  phase5GoNoGo: '第五阶段 Go/No-Go',
  phase5E2E: '第五阶段端到端联调',
};

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl || '').replace(/\/$/, '');
}

function itemCountFromPayload(payload = {}) {
  return Array.isArray(payload.items) ? payload.items.length : 0;
}

export function buildAdminApiErrorState({ status, domainLabel = '后台页面', detail } = {}) {
  const code = Number(status);
  const messages = {
    401: {
      title: `${domainLabel}鉴权失败`,
      message: '当前会话未通过后台鉴权，请检查登录态或 API Token 后重试。',
    },
    403: {
      title: `${domainLabel}权限不足`,
      message: '当前角色没有执行该后台操作的权限，请切换具备权限的角色或联系管理员授权。',
    },
    422: {
      title: `${domainLabel}参数校验失败`,
      message: '请求参数未通过后端校验，请检查筛选条件、分页参数和提交字段。',
    },
    500: {
      title: `${domainLabel}后端服务异常`,
      message: '后端服务处理异常，请查看 apps/api 日志、PostgreSQL 和 Redis 状态后重试。',
    },
  };
  const matched = messages[code] || {
    title: `${domainLabel}真实 API 异常`,
    message: detail || `真实 API 返回 ${status || 'unknown'}，请检查后端服务和网络连接。`,
  };
  return {
    status: code || status || 'unknown',
    statusClass: 'red',
    title: matched.title,
    message: matched.message,
  };
}

function buildRecord({ key, payload = {} }) {
  const label = DOMAIN_LABELS[key] || key;
  const ok = Boolean(payload.ok);
  return {
    key,
    name: label,
    url: payload.url || 'Unknown',
    status: payload.status || 'unknown',
    itemCount: itemCountFromPayload(payload.payload || { items: Array(payload.itemCount || 0).fill({}) }),
    statusLabel: ok ? '真实 API 已联通' : '真实 API 异常',
    statusClass: ok ? 'green' : 'red',
    error: ok ? null : buildAdminApiErrorState({ status: payload.status, domainLabel: label, detail: payload.error }),
  };
}

export function buildPhase5AdminIntegrationView({
  prompt = {},
  knowledge = {},
  emailReview = {},
  emailReplyQuality = {},
  phase5GoNoGo = {},
  phase5E2E = {},
  actorRole = 'operator',
  seedFallbackAllowed = false,
} = {}) {
  const integrationRecords = [
    buildRecord({ key: 'prompt', payload: prompt }),
    buildRecord({ key: 'knowledge', payload: knowledge }),
    buildRecord({ key: 'emailReview', payload: emailReview }),
    buildRecord({ key: 'emailReplyQuality', payload: emailReplyQuality }),
    buildRecord({ key: 'phase5GoNoGo', payload: phase5GoNoGo }),
    buildRecord({ key: 'phase5E2E', payload: phase5E2E }),
  ];
  const realApiReady = integrationRecords.every((record) => record.statusClass === 'green');
  const firstError = integrationRecords.find((record) => record.error)?.error || null;
  return {
    seedFallbackAllowed: Boolean(seedFallbackAllowed),
    realApiReady,
    statusLabel: realApiReady ? '真实 API 联调通过' : '真实 API 待修复',
    statusClass: realApiReady ? 'green' : 'red',
    integrationRecords,
    firstError,
    permission: {
      roleLabel: actorRole || 'operator',
      notice: '第五阶段后台页面必须使用真实 API、PostgreSQL 和权限上下文；页面不得以 seed 静态数据作为验收依据。',
    },
  };
}

async function fetchJsonRecord({ fetcher, url, domainLabel }) {
  const response = await fetcher(url);
  if (!response.ok) {
    return {
      ok: false,
      status: response.status || 'unknown',
      url,
      itemCount: 0,
      error: buildAdminApiErrorState({ status: response.status, domainLabel }).message,
    };
  }
  const payload = await response.json();
  return {
    ok: true,
    status: response.status || 200,
    url,
    payload,
    itemCount: itemCountFromPayload(payload),
  };
}

export async function fetchPhase5AdminIntegration({
  baseUrl = '',
  actorRole = 'operator',
  fetcher = globalThis.fetch,
} = {}) {
  if (typeof fetcher !== 'function') {
    throw new Error('fetcher is required to load phase5 admin integration');
  }
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const [prompt, knowledge, emailReview, emailReplyQuality, phase5GoNoGo, phase5E2E] = await Promise.all([
    fetchJsonRecord({
      fetcher,
      url: `${normalizedBaseUrl}/llm-prompt-templates`,
      domainLabel: DOMAIN_LABELS.prompt,
    }),
    fetchJsonRecord({
      fetcher,
      url: `${normalizedBaseUrl}/knowledge/items?limit=100`,
      domainLabel: DOMAIN_LABELS.knowledge,
    }),
    fetchJsonRecord({
      fetcher,
      url: `${normalizedBaseUrl}/email-reply/drafts?limit=100`,
      domainLabel: DOMAIN_LABELS.emailReview,
    }),
    fetchJsonRecord({
      fetcher,
      url: `${normalizedBaseUrl}/dashboard/email-reply-quality`,
      domainLabel: DOMAIN_LABELS.emailReplyQuality,
    }),
    fetchJsonRecord({
      fetcher,
      url: `${normalizedBaseUrl}/dashboard/phase5-go-no-go-report`,
      domainLabel: DOMAIN_LABELS.phase5GoNoGo,
    }),
    fetchJsonRecord({
      fetcher,
      url: `${normalizedBaseUrl}/dashboard/phase5-e2e-integration-report`,
      domainLabel: DOMAIN_LABELS.phase5E2E,
    }),
  ]);
  return {
    actorRole,
    prompt,
    knowledge,
    emailReview,
    emailReplyQuality,
    phase5GoNoGo,
    phase5E2E,
    seedFallbackAllowed: false,
  };
}
