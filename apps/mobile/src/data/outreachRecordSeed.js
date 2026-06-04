export const outreachRecordSeed = [
  {
    id: 'outreach-1',
    status: 'sent',
    channel: 'email',
    sent_by: 'Anna',
    owner: 'Anna',
    response_summary: '已人工发送俄语初次触达草稿。',
    next_action: '等待回复',
    script_version: 'TMP-RU-B-001/v1',
    triggers_do_not_contact: false,
  },
  {
    id: 'outreach-2',
    status: 'replied',
    channel: 'email',
    sent_by: 'Anna',
    owner: 'Anna',
    response_summary: '客户询问是否可了解 SUV 车型。',
    next_action: '补充车型需求',
    script_version: 'TMP-RU-B-001/v1',
    triggers_do_not_contact: false,
  },
];
