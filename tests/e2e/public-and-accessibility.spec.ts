import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const publicPages = [
  { path: '/', heading: 'Urus keuangan usaha tanpa harus menjadi ahli.' },
  { path: '/tentang', heading: 'Keuangan usaha yang lebih mudah dipahami.' },
  { path: '/fitur', heading: 'Dari transaksi harian hingga pendampingan.' },
  { path: '/bantuan', heading: 'Apa yang ingin Anda pelajari?' },
  { path: '/kebijakan-privasi', heading: 'Kebijakan Privasi' },
  { path: '/syarat-penggunaan', heading: 'Syarat Penggunaan' },
  { path: '/login', heading: 'Selamat datang kembali' },
  { path: '/registrasi', heading: 'Mulai catat usaha' },
  { path: '/lupa-password', heading: 'Atur ulang kata sandi' },
];

test('halaman publik utama dapat dinavigasi pada desktop dan ponsel', async ({ page }) => {
  for (const item of publicPages) {
    await page.goto(item.path);
    await expect(page.getByRole('heading', { level: 1, name: item.heading })).toBeVisible();
    await expect(page.locator('main#main-content')).toBeVisible();
  }
});

test('navigasi keyboard menyediakan skip link dan urutan fokus form', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  const skipLink = page.getByRole('link', { name: 'Lewati ke isi utama' });
  await expect(skipLink).toBeFocused();
  await skipLink.press('Enter');
  await expect(page).toHaveURL(/#main-content$/);

  await page.goto('/login');
  const businessId = page.getByLabel('ID usaha');
  const identifier = page.getByLabel('Email atau nomor telepon');
  const password = page.getByLabel('Kata sandi');
  await businessId.focus();
  await page.keyboard.press('Tab');
  await expect(identifier).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(password).toBeFocused();
});

for (const item of publicPages) {
  test(`@a11y ${item.path} tidak memiliki pelanggaran WCAG serius atau kritis`, async ({
    page,
  }) => {
    await page.goto(item.path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const blocking = result.violations.filter(
      (violation) => violation.impact === 'critical' || violation.impact === 'serious',
    );
    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}
