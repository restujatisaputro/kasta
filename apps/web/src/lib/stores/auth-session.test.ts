import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const session = {
  accessToken: 'access-token',
  refreshToken: 'refresh-token',
  businessId: '4c7c67e2-9c91-53e9-b636-c57a77cd0d13',
};

describe('authSession', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.resetModules();
  });

  it('restores the active session after a page reload', async () => {
    sessionStorage.setItem('kasta-auth-session', JSON.stringify(session));
    const { authSession } = await import('./auth-session');
    expect(get(authSession)).toEqual(session);
  });

  it('writes and clears the tab-scoped session', async () => {
    const { authSession } = await import('./auth-session');
    authSession.set(session);
    expect(JSON.parse(sessionStorage.getItem('kasta-auth-session') ?? 'null')).toEqual(session);
    authSession.set(null);
    expect(sessionStorage.getItem('kasta-auth-session')).toBeNull();
  });
});
