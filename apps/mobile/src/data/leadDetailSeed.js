export const leadDetailSeed = {
  id: 'ru-auto-city',
  customerName: 'AutoCity Moscow',
  country: 'Russia',
  city: 'Moscow',
  customerType: '当地车商/二级经销商',
  grade: 'B',
  status: 'pending',
  riskLevel: 'Low',
  handoffTeam: 'customer_service',
  operatingSummary: '官网展示进口二手车库存，近期更新，门店地址清晰，适合作为客服首批跟进线索。',
  aiRecommendation: {
    confidence: 0.84,
    suggestion: '建议交付客服，先确认是否长期采购中国二手/准新车。',
    reason: '官网展示进口二手车库存，公开邮箱可联系，城市和经营类型清晰。',
    missingInfo: ['主营车型', '月采购量'],
    nextAction: '人工触达',
  },
  sources: [
    {
      type: '官网来源',
      url: 'https://autocity.example.ru',
      evidence: '展示进口二手车库存与门店地址。',
    },
    {
      type: '公开邮箱',
      url: 'mailto:sales@autocity.example.ru',
      evidence: '公开邮箱可人工邮件触达。',
    },
  ],
  contacts: [
    { type: 'Email', value: 'sales@autocity.example.ru', usage: '人工邮件触达' },
    { type: 'Website', value: 'autocity.example.ru', usage: '查看公开库存' },
  ],
  followUps: [
    { title: '待客服首次触达', detail: '分配给 Anna，剩余 18 小时。' },
    { title: 'AI 生成俄语草稿', detail: '未承诺价格、物流、清关、付款或交付周期。' },
  ],
  inventoryMatch: {
    label: '查看 6 台匹配车源',
    path: '/pages/inventory/index?leadId=ru-auto-city',
  },
  doNotContact: false,
};

export const cGradeLeadDetailSeed = {
  ...leadDetailSeed,
  id: 'ru-siberia',
  customerName: 'Siberia Auto Trade',
  city: 'Novosibirsk',
  customerType: '已询价车商',
  grade: 'C',
  riskLevel: 'Medium',
  handoffTeam: 'export_sales',
  complianceReviewStatus: 'required',
  operatingSummary: '客户询问 2023 年准新 SUV 批发价，存在明确采购意向，报价前需合规复核。',
  aiRecommendation: {
    confidence: 0.91,
    suggestion: '建议交付出口销售，先完成人工合规复核再进入报价。',
    reason: '客户已提出车型和价格相关问题，意向高，但涉及报价动作。',
    missingInfo: ['采购预算', '目标配置', '贸易路径'],
    nextAction: '合规复核',
  },
};
