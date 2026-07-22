import type { PageLoad } from './$types';
export const load: PageLoad = ({ params }) => ({ businessId: params.businessId });
