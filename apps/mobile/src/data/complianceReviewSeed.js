export const complianceReviewSeed = {
  grade: 'C',
  status: 'pending',
  reviewer: null,
  reviewedAt: null,
  reason: 'C级线索报价/合同前自动进入合规复核',
  riskNote: '待复核贸易、支付、物流、清关风险',
  quoteContractBlocked: true,
};

export const approvedComplianceReviewSeed = {
  grade: 'C',
  status: 'approved',
  reviewer: 'Compliance Anna',
  reviewedAt: '2026-05-28T12:00:00Z',
  reason: '贸易路径初步可行',
  riskNote: '付款、物流、清关仍需人工确认',
  quoteContractBlocked: false,
};
