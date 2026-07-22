export const KASTA_ENVIRONMENTS = ['local', 'test', 'staging', 'production'] as const;

export type KastaEnvironment = (typeof KASTA_ENVIRONMENTS)[number];

export const API_VERSION = 'v1' as const;

export function isKastaEnvironment(value: string): value is KastaEnvironment {
  return KASTA_ENVIRONMENTS.some((environment) => environment === value);
}
