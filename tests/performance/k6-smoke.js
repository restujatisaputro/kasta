import { check, group, sleep } from 'k6';
import http from 'k6/http';

const baseUrl = (__ENV.KASTA_BASE_URL || 'http://localhost:8080').replace(/\/$/, '');
const accessToken = __ENV.KASTA_ACCESS_TOKEN || '';
const businessId = __ENV.KASTA_BUSINESS_ID || '';
const hostHeader = __ENV.KASTA_HOST_HEADER || '';
const loadProfile = __ENV.KASTA_LOAD_PROFILE === 'load';

export const options = {
  vus: loadProfile ? 50 : 5,
  duration: loadProfile ? '5m' : '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<750', 'p(99)<1500'],
    checks: ['rate>0.99'],
  },
};

function authenticatedParams() {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(hostHeader ? { Host: hostHeader } : {}),
    },
  };
}

export default function () {
  group('health', () => {
    const response = http.get(`${baseUrl}/api/v1/health/ready`, {
      headers: hostHeader ? { Host: hostHeader } : {},
    });
    check(response, {
      'readiness returns 200': (result) => result.status === 200,
      'database is ready': (result) => result.body.includes('"database":"ok"'),
    });
  });

  if (accessToken && businessId) {
    group('authenticated core reads', () => {
      const params = authenticatedParams();
      const transactions = http.get(
        `${baseUrl}/api/v1/businesses/${businessId}/transactions?page=1&page_size=20`,
        params,
      );
      check(transactions, {
        'transaction list returns 200': (result) => result.status === 200,
        'transaction response stays below 256 KiB': (result) => result.body.length < 262_144,
      });

      const syncStatus = http.get(
        `${baseUrl}/api/v1/sync/status?business_id=${businessId}&device_id=k6-quality-test`,
        params,
      );
      check(syncStatus, { 'sync status returns 200': (result) => result.status === 200 });
    });
  }

  sleep(1);
}
