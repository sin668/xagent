const TOP_LEVEL_TABS = [
  { key: 'home', label: '首页', icon: '⌂', path: '/pages/home/index' },
  { key: 'leads', label: '线索', icon: '☷', path: '/pages/leads/index' },
  { key: 'customers', label: '客户', icon: '☏', path: '/pages/customers/index' },
  { key: 'sources', label: '来源', icon: '⌁', path: '/pages/sources/index' },
  { key: 'insights', label: '洞察', icon: '▥', path: '/pages/inventory/index' },
];

export function buildBottomTabs(activeKey) {
  return TOP_LEVEL_TABS.map((tab) => ({
    ...tab,
    active: tab.key === activeKey,
  }));
}

export function navigateBottomTab(tab, uniApi = globalThis.uni) {
  if (!tab?.path || tab.active || !uniApi) {
    return false;
  }

  if (typeof uniApi.redirectTo === 'function') {
    uniApi.redirectTo({ url: tab.path });
    return true;
  }

  if (typeof uniApi.navigateTo === 'function') {
    uniApi.navigateTo({ url: tab.path });
    return true;
  }

  return false;
}
