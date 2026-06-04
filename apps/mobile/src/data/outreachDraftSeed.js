export const outreachLeadSeed = {
  id: 'ru-auto-city',
  customerName: 'AutoCity Moscow',
  grade: 'B',
  riskLevel: 'Low',
  doNotContact: false,
  channel: 'Email',
};

export const outreachDraftSeed = {
  id: 'draft-ru-b-001',
  templateId: 'TMP-RU-B-001',
  templateStatus: '可外发',
  version: 'v1',
  generatedAt: '2026-05-28T12:00:00Z',
  subject: 'Поставка подержанных автомобилей из Китая',
  body:
    'Здравствуйте! Мы изучаем возможности сотрудничества с автодилерами по поставкам автомобилей с пробегом, почти новых и складских автомобилей. Если вам интересно, пожалуйста, сообщите, какие модели и форматы сотрудничества для вас актуальны.',
  refusalPath:
    'Если вам не интересно получать такие сообщения, пожалуйста, сообщите нам, и мы больше не будем вас беспокоить.',
  riskTips: ['仅人工发送', '不得承诺最终价格、物流时效、清关结果、付款安全或交付周期'],
  audit: {
    model: 'Unknown',
    promptVersion: 'outreach-template-v1',
    inputSaved: true,
    outputSaved: true,
  },
};
