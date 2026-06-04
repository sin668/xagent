function parseTime(value) {
  return value ? new Date(value).getTime() : null;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('en-US');
}

export function isInventoryExpired(item, { now = new Date().toISOString() } = {}) {
  const validUntil = parseTime(item.validUntil || item.valid_until);
  if (!validUntil) {
    return false;
  }
  return validUntil < parseTime(now);
}

export function getAiQuoteSafety(item, options = {}) {
  const blockingReasons = [];
  const quoteStatus = item.quoteStatus || item.quote_status;
  const quotedPrice = item.quotedPrice ?? item.quoted_price;
  const exportReady = item.exportReady ?? item.export_ready;

  if (quoteStatus !== 'confirmed') {
    blockingReasons.push('价格未确认');
  }
  if (isInventoryExpired(item, options)) {
    blockingReasons.push('车源已过期');
  }
  if (!exportReady) {
    blockingReasons.push('不可出口');
  }
  if (quotedPrice == null) {
    blockingReasons.push('缺少价格');
  }

  return {
    canAiQuote: blockingReasons.length === 0,
    blockingReasons,
  };
}

export function filterPriorityInventory(items = [], options = {}) {
  return items.filter((item) => getAiQuoteSafety(item, options).canAiQuote);
}

export function buildInventoryCardView(item, options = {}) {
  const mediaUrls = item.mediaUrls || item.media_urls || [];
  const quotedPrice = item.quotedPrice ?? item.quoted_price;
  const mileageKm = item.mileageKm ?? item.mileage_km;
  const safety = getAiQuoteSafety(item, options);
  const expired = isInventoryExpired(item, options);
  const validUntil = item.validUntil || item.valid_until;
  const quoteStatus = item.quoteStatus || item.quote_status;

  return {
    id: item.id,
    title: `${item.brand} ${item.model}${item.year ? ` ${item.year}` : ''}`,
    meta: `${mileageKm ? `${formatNumber(mileageKm)} km` : '里程 Unknown'} · ${item.vehicleType || item.vehicle_type || '车型 Unknown'} · ${item.exportReady || item.export_ready ? '可出口' : '不可出口'}`,
    conditionSummary: item.conditionSummary || item.condition_summary || 'Unknown',
    configuration: item.configuration || 'Unknown',
    priceText: quotedPrice == null ? '价格待补充' : `${item.currency || 'USD'} ${formatNumber(quotedPrice)}`,
    mediaCountText: `${mediaUrls.length} 个图片/视频`,
    expiryLabel: expired ? '已过期' : validUntil ? `有效至 ${validUntil.slice(0, 10)}` : '有效期 Unknown',
    quoteStatusLabel: quoteStatus === 'confirmed' ? '价格已确认' : '价格未确认',
    canAiQuote: safety.canAiQuote,
    blockingReasons: safety.blockingReasons,
    priorityRecommendable: safety.canAiQuote,
    imageUrl: mediaUrls.find((url) => /\.(png|jpe?g|webp)(?:$|\?)/i.test(url)) || mediaUrls[0] || '',
  };
}
