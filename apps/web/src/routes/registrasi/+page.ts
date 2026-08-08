import { redirect } from '@sveltejs/kit';

/* Pendaftaran memakai satu pintu di /onboarding. Rute ini dipertahankan sebagai
   pengalihan permanen agar tautan lama, penanda, dan materi promosi tetap hidup. */
export function load(): never {
  redirect(308, '/onboarding');
}
