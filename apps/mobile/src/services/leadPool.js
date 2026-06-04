const ACTIONABLE_GRADES = new Set(['A', 'B', 'C']);
const SOCIAL_CONTACT_TYPES = new Set(['telegram', 'whatsapp', 'vkontakte', 'vk', 'odnoklassniki', 'ok', 'tiktok', 'max']);

function normalizedGrade(lead) {
  return String(lead?.grade || '').trim().toUpperCase();
}

function normalizedRiskLevel(lead) {
  return String(lead?.riskLevel || 'Unknown').trim();
}

function isDoNotContact(lead) {
  return Boolean(lead?.doNotContact || lead?.do_not_contact || lead?.status === 'do_not_contact');
}

function isActionableLead(lead) {
  return ACTIONABLE_GRADES.has(normalizedGrade(lead)) && !isDoNotContact(lead);
}

function needsHighSecondaryReview(lead) {
  return (
    String(lead?.riskLevel || '').trim() === 'High' ||
    Boolean(lead?.requiresSecondaryVerification) ||
    String(lead?.reviewStatus || '').toLowerCase() === 'needs_secondary_verification'
  );
}

function hasContact(lead) {
  if (typeof lead?.hasContact === 'boolean') {
    return lead.hasContact;
  }
  return Array.isArray(lead?.contacts) ? lead.contacts.some((item) => String(item?.value || '').trim()) : true;
}

function leadContacts(lead) {
  return Array.isArray(lead?.contacts) ? lead.contacts : [];
}

function hasEmailContact(lead) {
  return leadContacts(lead).some((item) => {
    const type = String(item?.type || '').trim().toLowerCase();
    const value = String(item?.value || '').trim().toLowerCase();
    return Boolean(value) && (type === 'email' || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
  });
}

function hasSocialContact(lead) {
  return leadContacts(lead).some((item) => {
    const type = String(item?.type || '').trim().toLowerCase();
    const value = String(item?.value || '').trim().toLowerCase();
    if (!value) {
      return false;
    }
    return (
      SOCIAL_CONTACT_TYPES.has(type) ||
      value.includes('t.me') ||
      value.includes('telegram') ||
      value.includes('whatsapp') ||
      value.includes('vk.com') ||
      value.includes('ok.ru') ||
      value.includes('tiktok') ||
      value.includes('max')
    );
  });
}

function isBcGrade(lead) {
  return ['B', 'C'].includes(normalizedGrade(lead)) && !isDoNotContact(lead);
}

function isAbcGrade(lead) {
  return ['A', 'B', 'C'].includes(normalizedGrade(lead)) && !isDoNotContact(lead);
}

function isDeGrade(lead) {
  return ['WATCH', 'INVALID'].includes(normalizedGrade(lead));
}

function displayGradeLabel(grade) {
  if (grade === 'WATCH') {
    return 'D 级';
  }
  if (grade === 'INVALID') {
    return 'E 级';
  }
  return grade ? `${grade} 级` : 'Unknown';
}

function displayGradeClass(grade) {
  if (grade === 'C') {
    return 'grade-c';
  }
  if (grade === 'B') {
    return 'grade-b';
  }
  if (grade === 'WATCH') {
    return 'grade-d';
  }
  if (grade === 'INVALID') {
    return 'grade-e';
  }
  return 'grade-a';
}

export function filterLeadPool(leads = [], filterKey = 'pending') {
  switch (filterKey) {
    case 'all':
      return leads;
    case 'with-contact':
      return leads.filter((lead) => hasContact(lead));
    case 'email-contact':
      return leads.filter((lead) => hasEmailContact(lead));
    case 'social-contact':
      return leads.filter((lead) => hasSocialContact(lead));
    case 'grade-bc':
      return leads.filter((lead) => isBcGrade(lead));
    case 'grade-abc':
      return leads.filter((lead) => isAbcGrade(lead));
    case 'grade-de':
      return leads.filter((lead) => isDeGrade(lead));
    case 'high-secondary':
      return leads.filter((lead) => needsHighSecondaryReview(lead));
    case 'missing-contact':
      return leads.filter((lead) => !hasContact(lead));
    case 'watch-invalid':
      return leads.filter((lead) => ['WATCH', 'INVALID'].includes(normalizedGrade(lead)));
    case 'pending':
    default:
      return leads.filter((lead) => String(lead?.status || '').toLowerCase() === 'pending' && isActionableLead(lead));
  }
}

export function buildLeadFilterTabs(leads = []) {
  return [
    { key: 'all', label: '全部', count: filterLeadPool(leads, 'all').length },
    { key: 'email-contact', label: '有邮箱联系', count: filterLeadPool(leads, 'email-contact').length },
    { key: 'social-contact', label: '有社交媒体', count: filterLeadPool(leads, 'social-contact').length },
    { key: 'grade-abc', label: 'A/B/C级线索', count: filterLeadPool(leads, 'grade-abc').length },
    { key: 'grade-de', label: 'D/E级线索', count: filterLeadPool(leads, 'grade-de').length },
  ];
}

export function buildLeadPoolStats(leads = []) {
  return [
    { key: 'email', label: '有邮箱联系线索', count: filterLeadPool(leads, 'email-contact').length, className: 'source-number-green' },
    { key: 'social', label: '有社交媒体联系线索', count: filterLeadPool(leads, 'social-contact').length, className: 'source-number-blue' },
    { key: 'grade-abc', label: 'A/B/C级线索', count: filterLeadPool(leads, 'grade-abc').length, className: 'source-number-green' },
    { key: 'grade-de', label: 'D/E级线索', count: filterLeadPool(leads, 'grade-de').length, className: 'source-number-red' },
  ];
}

export function getLeadCardViewModel(lead) {
  const grade = normalizedGrade(lead);
  const riskLevel = normalizedRiskLevel(lead);
  const isCGrade = grade === 'C';
  const complianceStatus = String(lead?.complianceReviewStatus || '').trim();
  const complianceLabelMap = {
    required: '待合规复核',
    approved: '合规已通过',
    rejected: '合规未通过',
  };

  return {
    id: lead?.id,
    customerName: lead?.customerName || 'Unknown',
    city: lead?.city || 'Unknown',
    customerType: lead?.customerType || 'Unknown',
    channel: lead?.channel || 'Unknown',
    evidenceNote: lead?.evidenceNote || '',
    gradeLabel: displayGradeLabel(grade),
    gradeClass: displayGradeClass(grade),
    riskLabel: riskLevel === 'Low' ? '低风险' : riskLevel === 'Medium' ? '中风险' : `${riskLevel} 风险`,
    riskClass: riskLevel === 'Low' ? 'risk-low' : riskLevel === 'Medium' ? 'risk-medium' : 'risk-high',
    handoffLabel: isCGrade ? '交付销售' : lead?.handoffTeam === 'customer_service' ? '交付客服' : 'AI 推荐复核',
    complianceLabel: isCGrade ? complianceLabelMap[complianceStatus] || '待合规复核' : '',
    riskMarkers: lead?.riskMarkers || [],
    isDoNotContact: isDoNotContact(lead),
    isOverdue: Boolean(lead?.isOverdue),
  };
}
