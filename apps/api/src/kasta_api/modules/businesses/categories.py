from uuid import UUID, uuid5

BUSINESS_CATEGORY_NAMESPACE = UUID("30e46f66-2958-42ef-84cb-196ca15d9c2f")

BUSINESS_CATEGORY_SEED: tuple[tuple[str, str, str, int], ...] = (
    ("retail", "Toko dan Eceran", "TRADE", 10),
    ("wholesale", "Grosir dan Distributor", "TRADE", 20),
    ("food", "Makanan", "CULINARY", 30),
    ("beverage", "Minuman", "CULINARY", 40),
    ("personal_service", "Jasa Perorangan", "SERVICE", 50),
    ("professional_service", "Jasa Profesional", "SERVICE", 60),
    ("craft", "Kerajinan", "PRODUCTION", 70),
    ("manufacturing", "Produksi dan Pengolahan", "PRODUCTION", 80),
    ("fashion", "Pakaian dan Aksesori", "CREATIVE", 90),
    ("creative", "Desain, Foto, dan Karya Kreatif", "CREATIVE", 100),
    ("agriculture", "Pertanian dan Perkebunan", "AGRICULTURE", 110),
    ("fishery", "Perikanan dan Peternakan", "AGRICULTURE", 120),
    ("other", "Usaha Lainnya", "OTHER", 999),
)


def business_category_id(code: str) -> UUID:
    return uuid5(BUSINESS_CATEGORY_NAMESPACE, code)
