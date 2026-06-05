import { apiClient } from './apiClient.js';

function compactParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  );
}

function buildQuery(params = {}) {
  const entries = Object.entries(compactParams(params));
  return entries.length ? `?${new URLSearchParams(entries).toString()}` : '';
}

function normalizeDecision(value) {
  const decision = String(value || '').toLowerCase();
  if (['auto_send_allowed', 'auto_send', 'allowed'].includes(decision)) {
    return 'auto_send_allowed';
  }
  if (['blocked', 'hard_blocked', 'dnc_blocked'].includes(decision)) {
    return 'blocked';
  }
  return 'manual_review';
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : 'Unknown';
}

export function mapEmailReplyItem(item = {}) {
  const decision = normalizeDecision(item.auto_send_decision || item.autoSendDecision || item.decision);
  const hardBlocks = item.hard_block_reasons || item.hardBlockReasons || [];
  const knowledgeHits = item.knowledge_hits || item.knowledgeHits || [];
  const customer = item.customer || {};
  const message = item.message || item.email_message || item.emailMessage || item;

  return {
    id: item.id || item.reply_id || item.replyId || message.id,
    threadId: item.thread_id || item.threadId || message.thread_id || message.threadId || '',
    customerName: item.customer_name || item.customerName || customer.name || 'Unknown customer',
    customerGrade: item.customer_grade || item.customerGrade || customer.grade || 'Unknown',
    subject: message.subject || item.subject || 'Unknown subject',
    preview: message.preview || message.body_preview || message.bodyPreview || message.body || '',
    language: item.language || message.language || 'Unknown',
    decision,
    decisionLabel:
      decision === 'auto_send_allowed' ? '可自动发' : decision === 'blocked' ? '硬拦截' : '需确认',
    hardBlocks,
    knowledgeHits,
    knowledgeSummary: knowledgeHits[0]?.title || knowledgeHits[0]?.knowledge_key || knowledgeHits[0]?.key || '待匹配知识',
    similarityText: formatPercent(knowledgeHits[0]?.similarity_score ?? knowledgeHits[0]?.similarityScore),
    riskLevel: item.risk_level || item.riskLevel || 'Unknown',
    receivedAt: message.received_at || message.receivedAt || item.received_at || '',
    canAutoSend: decision === 'auto_send_allowed' && hardBlocks.length === 0,
  };
}

export function mapEmailReplyDetail(payload = {}) {
  const item = mapEmailReplyItem(payload);
  const draft = payload.draft || payload.reply_draft || payload.replyDraft || {};
  const autoSendCheck = payload.auto_send_check || payload.autoSendCheck || {};
  const knowledgeHits = payload.knowledge_hits || payload.knowledgeHits || item.knowledgeHits || [];
  const audit = payload.audit || payload.ai_audit || payload.aiAudit || {};

  return {
    ...item,
    inboundBody: payload.inbound_body || payload.inboundBody || payload.message?.body || item.preview,
    replySubject: draft.subject || payload.reply_subject || payload.replySubject || '回复建议待生成',
    replyBody: draft.body || payload.reply_body || payload.replyBody || '',
    promptVersion: draft.prompt_version || draft.promptVersion || payload.prompt_version || 'email-reply-v1',
    modelName: audit.model || audit.model_name || audit.modelName || payload.model_name || 'Unknown',
    knowledgeHits: knowledgeHits.map((hit) => ({
      id: hit.id || hit.knowledge_key || hit.key || hit.title,
      title: hit.title || hit.knowledge_key || hit.key || 'Unknown knowledge',
      note: hit.note || hit.summary || hit.content_preview || hit.contentPreview || '',
      similarityText: formatPercent(hit.similarity_score ?? hit.similarityScore),
      autoReplyAllowed: Boolean(hit.auto_reply_allowed ?? hit.autoReplyAllowed),
    })),
    autoSendCheck: {
      decision: normalizeDecision(autoSendCheck.decision || item.decision),
      allowAutoSend: Boolean(autoSendCheck.allow_auto_send ?? autoSendCheck.allowAutoSend ?? item.canAutoSend),
      reasons: autoSendCheck.reasons || payload.hard_block_reasons || payload.hardBlockReasons || item.hardBlocks || [],
      hardBlocks: autoSendCheck.hard_blocks || autoSendCheck.hardBlocks || item.hardBlocks || [],
    },
  };
}

export function summarizeEmailReplies(items = []) {
  return {
    total: items.length,
    autoSend: items.filter((item) => item.decision === 'auto_send_allowed').length,
    manual: items.filter((item) => item.decision === 'manual_review').length,
    blocked: items.filter((item) => item.decision === 'blocked').length,
  };
}

export function filterEmailReplies(items = [], filter = 'all') {
  if (filter === 'auto') {
    return items.filter((item) => item.decision === 'auto_send_allowed');
  }
  if (filter === 'manual') {
    return items.filter((item) => item.decision === 'manual_review');
  }
  if (filter === 'blocked') {
    return items.filter((item) => item.decision === 'blocked');
  }
  return items;
}

export function buildEmailReplyActionPayload({ actor = 'mobile-operator', note = '' } = {}) {
  return {
    actor,
    review_note: note || null,
    manual_confirmed: true,
  };
}

export function createEmailRepliesService({ client = apiClient } = {}) {
  return {
    async listEmailReplies(params = {}) {
      const payload = await client.get(`/email-replies${buildQuery(params)}`);
      const items = Array.isArray(payload) ? payload : payload.items || [];
      return {
        items: items.map(mapEmailReplyItem),
        total: Number(payload.total ?? items.length),
      };
    },

    async getEmailReply(replyId) {
      const payload = await client.get(`/email-replies/${encodeURIComponent(replyId)}`);
      return mapEmailReplyDetail(payload);
    },

    async confirmManualSend(replyId, options = {}) {
      const payload = await client.post(
        `/email-replies/${encodeURIComponent(replyId)}/confirm-send`,
        buildEmailReplyActionPayload(options),
      );
      return mapEmailReplyDetail(payload);
    },

    async rejectReply(replyId, options = {}) {
      const payload = await client.post(
        `/email-replies/${encodeURIComponent(replyId)}/reject`,
        buildEmailReplyActionPayload(options),
      );
      return mapEmailReplyDetail(payload);
    },
  };
}

export const emailRepliesService = createEmailRepliesService();
