export const outreachSlaDashboardSeed = {
  summary: {
    sent_count: 18,
    replied_count: 5,
    response_rate: 0.28,
    pending_count: 18,
    overdue_count: 3,
    compliance_waiting_count: 2,
    sla_risk_count: 5,
  },
  queue: [
    {
      customer_name: 'B 级客服跟进',
      grade: 'B',
      owner: 'Anna',
      status: 'customer_service_following',
      sla_hours: 48,
      waiting_hours: 50,
      risk_status: 'overdue',
      next_action: '立即跟进',
    },
    {
      customer_name: 'C 级销售推进',
      grade: 'C',
      owner: 'Boris',
      status: 'sales_following',
      sla_hours: 24,
      waiting_hours: 30,
      risk_status: 'compliance_waiting',
      compliance_status: 'pending',
      next_action: '等待合规复核',
    },
  ],
};
