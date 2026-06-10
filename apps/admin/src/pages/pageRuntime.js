const defaultApiBaseUrl = 'http://localhost:8000';

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl;
export const adminActorRole = import.meta.env.VITE_ADMIN_ACTOR_ROLE || 'operator';

export function formatLoadError(prefix, error) {
  return `${prefix}：${error?.message || 'Unknown'}`;
}
