const PRIORITY_GRADES = new Set(['B', 'C']);
const ACTIONABLE_GRADES = new Set(['A', 'B', 'C']);
const CLEANED_GRADES = new Set(['D', 'E', 'WATCH', 'INVALID']);
const EXECUTABLE_RISK_LEVELS = new Set(['Low', 'Medium']);

function normalizeGrade(value) {
  return String(value || 'Unknown').toUpperCase();
}

function normalizeRiskLevel(value) {
  return String(value || 'Unknown').trim();
}

function isDoNotContact(lead) {
  return Boolean(lead?.doNotContact || lead?.do_not_contact);
}

function isPendingLead(lead) {
  return String(lead?.status || '').toLowerCase() === 'pending';
}

function formatRatio(numerator, denominator) {
  if (!denominator) {
    return '0%';
  }

  return `${Math.round((numerator / denominator) * 100)}%`;
}

function firstNumber(...values) {
  for (const value of values) {
    if (value == null || value === '') {
      continue;
    }
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }
  return null;
}

export function getPendingPriorityLeads(leads = []) {
  return leads.filter(
    (lead) =>
      PRIORITY_GRADES.has(String(lead?.grade || '').toUpperCase()) &&
      isPendingLead(lead) &&
      !isDoNotContact(lead),
  );
}

export function filterExecutableAiTasks(tasks = []) {
  return tasks.filter((task) => EXECUTABLE_RISK_LEVELS.has(normalizeRiskLevel(task?.channelRisk)));
}

export function filterExecutableChannelPerformance(channels = []) {
  return channels.filter((channel) => EXECUTABLE_RISK_LEVELS.has(normalizeRiskLevel(channel?.riskLevel)));
}

export function buildHomeCustomerStats(customers = []) {
  return [
    {
      key: 'grade_abc',
      label: 'A/B/C级客户',
      count: customers.filter((customer) => ACTIONABLE_GRADES.has(normalizeGrade(customer?.grade))).length,
    },
    {
      key: 'has_intent',
      label: '车型意向客户',
      count: customers.filter((customer) => Boolean(customer?.hasVehicleIntent)).length,
    },
    {
      key: 'today',
      label: '今日待跟进',
      count: customers.filter(
        (customer) =>
          ACTIONABLE_GRADES.has(normalizeGrade(customer?.grade)) &&
          (customer?.nextAction === '今日待跟进' || customer?.followupStatus === 'due_today'),
      ).length,
    },
  ];
}

export function buildHomeLeadStats({ leads = [], channels = [], summary = {} } = {}) {
  const abcLeadCount = firstNumber(
    summary.abcLeadsTotal,
    summary.abc_leads_total,
    summary.abcLeadTotal,
    summary.abc_lead_total,
    summary.abcGradeCount,
    summary.abc_grade_count,
    summary.actionableLeadCount,
    summary.actionable_lead_count,
  ) ?? leads.filter((lead) => ACTIONABLE_GRADES.has(normalizeGrade(lead?.grade))).length;
  const sourceCount = firstNumber(
    summary.sourceCandidatesTotal,
    summary.source_candidates_total,
    summary.sourceCandidateTotal,
    summary.source_candidate_total,
    summary.sourceCount,
    summary.source_count,
    summary.leadSourceCount,
    summary.lead_source_count,
    summary.sourceCandidateCount,
    summary.source_candidate_count,
  ) ?? channels.length;
  const cleanedLeadCount = firstNumber(
    summary.cleanedLeadsTotal,
    summary.cleaned_leads_total,
    summary.cleanedLeadTotal,
    summary.cleaned_lead_total,
    summary.cleanedLeadCount,
    summary.cleaned_lead_count,
    summary.invalidWatchCount,
    summary.invalid_watch_count,
    summary.invalidCount,
    summary.invalid_count,
  ) ?? leads.filter((lead) => CLEANED_GRADES.has(normalizeGrade(lead?.grade))).length;

  return [
    {
      key: 'grade_abc',
      label: 'A/B/C级线索',
      count: abcLeadCount,
    },
    {
      key: 'sources',
      label: '线索来源',
      count: sourceCount,
      className: 'metric-green',
    },
    {
      key: 'cleaned',
      label: '被清洗线索',
      count: cleanedLeadCount,
      className: 'metric-blue',
    },
  ];
}

export function buildHomeDashboard({ leads = [], aiTasks = [], channels = [], customers = [], leadStatsSummary = {} } = {}) {
  const actionableLeads = leads.filter((lead) => !isDoNotContact(lead));
  const bGradeCount = leads.filter((lead) => String(lead?.grade || '').toUpperCase() === 'B').length;
  const pendingPriorityLeads = getPendingPriorityLeads(leads);
  const pendingFollowUpCount = actionableLeads.filter(
    (lead) =>
      lead?.followUpDueToday &&
      isPendingLead(lead) &&
      ACTIONABLE_GRADES.has(String(lead?.grade || '').toUpperCase()),
  ).length;
  const executableAiTasks = filterExecutableAiTasks(aiTasks);
  const channelPerformance = filterExecutableChannelPerformance(channels);

  return {
    pendingPriorityCount: pendingPriorityLeads.length,
    totalCandidateLeads: leads.length,
    bGradeRatioText: formatRatio(bGradeCount, leads.length),
    pendingFollowUpCount,
    leadStats: buildHomeLeadStats({ leads, channels, summary: leadStatsSummary }),
    customerStats: buildHomeCustomerStats(customers),
    executableAiTasks,
    channelPerformance,
    aiStatusText: executableAiTasks.some((task) => task.status === 'running') ? '运行中' : '待启动',
    reviewRequiredCount: pendingPriorityLeads.filter((lead) => String(lead?.grade || '').toUpperCase() === 'C').length,
  };
}
