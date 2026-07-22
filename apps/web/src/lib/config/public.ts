import { env } from '$env/dynamic/public';
import { z } from 'zod';

const publicConfigSchema = z.object({
  apiBaseUrl: z.string().url(),
  environment: z.enum(['local', 'test', 'staging', 'production']),
});

export const publicConfig = publicConfigSchema.parse({
  apiBaseUrl: env.PUBLIC_API_BASE_URL ?? 'http://localhost:8080/api/v1',
  environment: env.PUBLIC_APP_ENVIRONMENT ?? 'local',
});
