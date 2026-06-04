const PRIORITY_GRADES = new Set(['B', 'C']);
const ACTIONABLE_GRADES = new Set(['A', 'B', 'C']);
const EXECUTABLE_RISK_LEVELS = new Set(['Low', 'Medium']);

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

export function buildHomeDashboard({ leads = [], aiTasks = [], channels = [] } = {}) {
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
    executableAiTasks,
    channelPerformance,
    aiStatusText: executableAiTasks.some((task) => task.status === 'running') ? '运行中' : '待启动',
    reviewRequiredCount: pendingPriorityLeads.filter((lead) => String(lead?.grade || '').toUpperCase() === 'C').length,
  };
}
