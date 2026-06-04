const STATUS_OPTIONS = [
  { value: 'sent', label: '已发送' },
  { value: 'replied', label: '已回复' },
  { value: 'rejected', label: '拒绝' },
  { value: 'no_response', label: '无回复' },
  { value: 'bad_contact', label: '错误联系方式' },
];

const STATUS_LABELS = Object.fromEntries(STATUS_OPTIONS.map((option) => [option.value, option.label]));
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isDoNotContact(lead) {
  return Boolean(lead?.doNotContact || lead?.do_not_contact || lead?.status === 'do_not_contact');
}

export function isBackendCustomerId(value) {
  return UUID_PATTERN.test(String(value || '').trim());
}

export function normalizeOutreachChannel(value) {
  const channel = String(value || '').trim().toLowerCase();
  if (channel.includes('telegram')) {
    return 'telegram';
  }
  if (channel.includes('whatsapp')) {
    return 'whatsapp';
  }
  if (channel.includes('vkontakte') || channel.includes('vk')) {
    return 'vkontakte';
  }
  if (channel.includes('odnoklassniki') || channel.includes('ok')) {
    return 'odnoklassniki';
  }
  if (channel.includes('tiktok')) {
    return 'tiktok';
  }
  if (channel.includes('max')) {
    return 'max';
  }
  if (channel.includes('phone') || channel.includes('电话') || channel.includes('短信')) {
    return 'phone';
  }
  if (channel.includes('email') || channel.includes('邮箱') || channel.includes('邮件')) {
    return 'email';
  }
  if (channel.includes('官网') || channel.includes('website')) {
    return 'website';
  }

  return [
    'email',
    'phone',
    'whatsapp',
    'telegram',
    'vkontakte',
    'odnoklassniki',
    'tiktok',
    'max',
    'website',
    'website_form',
    'other',
  ].includes(channel)
    ? channel
    : 'other';
}

export function getOutreachStatusOptions() {
  return STATUS_OPTIONS;
}

export function canCreateOutreachRecord({ lead, status, manualConfirmed }) {
  if (isDoNotContact(lead)) {
    return { allowed: false, reason: '勿扰客户无法新增触达记录' };
  }
  if (status === 'sent' && !manualConfirmed) {
    return { allowed: false, reason: '已发送必须对应人工确认动作' };
  }

  return { allowed: true, reason: null };
}

export function buildOutreachRecordPayload({
  channel,
  status,
  sender,
  owner,
  summary,
  nextAction,
  manualConfirmed,
  doNotContactReason,
  scriptVersion,
}) {
  return {
    channel: normalizeOutreachChannel(channel),
    status,
    sent_by: sender,
    owner,
    response_summary: summary,
    next_action: nextAction,
    manual_confirmed: manualConfirmed,
    do_not_contact_reason: doNotContactReason || null,
    script_version: scriptVersion || null,
  };
}

export function buildOutreachHistoryView(records = []) {
  return records.map((record) => {
    const statusLabel = STATUS_LABELS[record.status] || record.status || 'Unknown';
    const channelLabel = record.channel ? `${record.channel.charAt(0).toUpperCase()}${record.channel.slice(1)}` : 'Unknown';
    const nextAction = record.next_action ? `下一步：${record.next_action}` : '暂无下一步';
    const owner = record.owner || record.sent_by || '未分配';
    return {
      id: record.id,
      statusLabel,
      title: `${channelLabel} · ${statusLabel}`,
      detail: `${record.response_summary || '无摘要'} · ${nextAction} · 负责人：${owner}`,
      scriptVersion: record.script_version || 'Unknown',
      triggersDoNotContact: Boolean(record.triggers_do_not_contact),
    };
  });
}
