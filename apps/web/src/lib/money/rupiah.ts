export function digitsOnly(value: string): string {
  return value.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
}

export function formatRupiahDigits(value: string): string {
  const digits = digitsOnly(value);
  if (!digits) return '';
  return new Intl.NumberFormat('id-ID').format(Number(digits));
}

export function formatRupiah(value: string | number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}
