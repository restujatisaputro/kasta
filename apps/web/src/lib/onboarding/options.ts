import type { BusinessScale, BusinessType, PaymentMethodCode } from '@kasta/contracts';

export const businessTypes: { value: BusinessType; label: string; hint: string }[] = [
  { value: 'TRADE', label: 'Jual beli', hint: 'Toko, warung, grosir' },
  { value: 'CULINARY', label: 'Makanan & minuman', hint: 'Katering, kedai, produksi makanan' },
  { value: 'SERVICE', label: 'Jasa', hint: 'Salon, bengkel, konsultasi' },
  { value: 'PRODUCTION', label: 'Produksi', hint: 'Membuat atau mengolah barang' },
  { value: 'CREATIVE', label: 'Kreatif', hint: 'Fashion, desain, foto, karya' },
  { value: 'AGRICULTURE', label: 'Tani & ternak', hint: 'Pertanian, ikan, peternakan' },
  { value: 'OTHER', label: 'Lainnya', hint: 'Jenis usaha lainnya' },
];

export const businessScales: { value: BusinessScale; label: string; hint: string }[] = [
  { value: 'MICRO', label: 'Mikro', hint: 'Dikelola sendiri atau tim kecil' },
  { value: 'SMALL', label: 'Kecil', hint: 'Sudah memiliki beberapa pegawai' },
  { value: 'MEDIUM', label: 'Menengah', hint: 'Operasional dan tim lebih besar' },
];

export const paymentOptions: { value: PaymentMethodCode; label: string }[] = [
  { value: 'CASH', label: 'Tunai' },
  { value: 'BANK_TRANSFER', label: 'Transfer bank' },
  { value: 'QRIS', label: 'QRIS' },
  { value: 'E_WALLET', label: 'Dompet digital' },
  { value: 'CARD', label: 'Kartu debit/kredit' },
];
