package id.kasta.app.receiptscan

import java.math.BigDecimal
import java.time.DateTimeException
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

private val moneyPattern =
    Regex("(?i)(?<![A-Z0-9])((?:RP\\s*)?-?\\d{1,3}(?:(?:[.,]\\d{3})+|[.,]\\d{2})|(?:RP\\s*)?-?\\d+)(?![A-Z0-9])")
private val numericDatePattern =
    Regex("\\b(?:(\\d{4})[-/.](\\d{1,2})[-/.](\\d{1,2})|(\\d{1,2})[-/.](\\d{1,2})[-/.](\\d{2,4}))\\b")
private val receiptNumberPattern =
    Regex("(?i)\\b(?:NO\\.?\\s*(?:NOTA|STRUK|TRANSAKSI)?|NOTA|INVOICE|INV|RECEIPT|TRX)\\s*[:#-]?\\s*([A-Z0-9][A-Z0-9./-]{2,})\\b")

object IndonesianReceiptParser {
    fun parseMoney(raw: String): BigDecimal {
        var value = raw.uppercase(Locale.ROOT).replace("RP", "").replace(" ", "")
        val negative = value.startsWith("-")
        value = value.trimStart('-', '+')
        require(value.matches(Regex("\\d+(?:[.,]\\d+)*"))) { "Format nominal tidak dikenali" }
        val lastSeparator = maxOf(value.lastIndexOf('.'), value.lastIndexOf(','))
        var integerPart = value
        var decimalPart = "00"
        if (lastSeparator >= 0) {
            val trailing = value.substring(lastSeparator + 1)
            val separatorCount = value.count { it == '.' || it == ',' }
            if (trailing.length == 2 && separatorCount >= 1) {
                integerPart = value.substring(0, lastSeparator)
                decimalPart = trailing
            }
        }
        val amount = BigDecimal("${integerPart.replace(".", "").replace(",", "")}.$decimalPart")
        return if (negative) amount.negate() else amount
    }

    fun parse(rawText: String): LocalParsedReceipt {
        val lines =
            rawText.lineSequence()
                .map { it.trim().replace(Regex("[ \\t]+"), " ") }
                .filter(String::isNotBlank)
                .toList()
        if (lines.isEmpty()) return LocalParsedReceipt(emptyMap(), emptyList())
        val fields = linkedMapOf<String, ReceiptFieldValue>()
        merchant(lines)?.let { fields["merchant_name"] = it }
        receiptDate(lines)?.let { fields["receipt_date"] = it }
        receiptNumber(lines)?.let { fields["receipt_number"] = it }
        labelledMoney(lines, listOf("SUBTOTAL", "SUB TOTAL"))?.let { fields["subtotal"] = it }
        labelledMoney(lines, listOf("DISKON", "DISC", "DISCOUNT"))?.let {
            fields["discount"] = it
        }
        labelledMoney(lines, listOf("PAJAK", "PPN", "TAX"))?.let { fields["tax"] = it }
        total(lines)?.let { fields["total"] = it }
        payment(lines)?.let { fields["payment_method"] = it }
        val combined = lines.joinToString(" ").uppercase(Locale.ROOT)
        val kind =
            if (listOf("PENJUALAN", "SALES RECEIPT", "PELANGGAN").any(combined::contains)) {
                "INCOME"
            } else {
                "EXPENSE"
            }
        fields["transaction_kind"] = ReceiptFieldValue(kind, 0.78f, "Kata kunci nota")
        fields["category_account"] = category(combined)
        return LocalParsedReceipt(fields, items(lines))
    }

    private fun merchant(lines: List<String>): ReceiptFieldValue? {
        val ignored = listOf("ALAMAT", "TELP", "NOTA", "INVOICE", "TANGGAL", "TOTAL")
        return lines.take(8).firstOrNull { line ->
            line.count(Char::isLetter) >= 3 &&
                line.length <= 80 &&
                ignored.none { line.contains(it, ignoreCase = true) } &&
                numericDatePattern.find(line) == null
        }?.let { ReceiptFieldValue(it, if (it == lines.first()) 0.92f else 0.78f, it) }
    }

    private fun receiptDate(lines: List<String>): ReceiptFieldValue? {
        for (line in lines) {
            val match = numericDatePattern.find(line) ?: continue
            val groups = match.groupValues
            try {
                val date =
                    if (groups[1].isNotBlank()) {
                        LocalDate.of(groups[1].toInt(), groups[2].toInt(), groups[3].toInt())
                    } else {
                        var year = groups[6].toInt()
                        if (year < 100) year += 2000
                        LocalDate.of(year, groups[5].toInt(), groups[4].toInt())
                    }
                return ReceiptFieldValue(date.toString(), 0.95f, line)
            } catch (_: DateTimeException) {
                continue
            }
        }
        val months =
            mapOf(
                "JANUARI" to 1,
                "FEBRUARI" to 2,
                "MARET" to 3,
                "APRIL" to 4,
                "MEI" to 5,
                "JUNI" to 6,
                "JULI" to 7,
                "AGUSTUS" to 8,
                "SEPTEMBER" to 9,
                "OKTOBER" to 10,
                "NOVEMBER" to 11,
                "DESEMBER" to 12,
            )
        val regex = Regex("(?i)\\b(\\d{1,2})\\s+(${months.keys.joinToString("|")})\\s+(\\d{4})\\b")
        lines.forEach { line ->
            regex.find(line)?.let { match ->
                val date =
                    LocalDate.of(
                        match.groupValues[3].toInt(),
                        months.getValue(match.groupValues[2].uppercase(Locale.ROOT)),
                        match.groupValues[1].toInt(),
                    )
                return ReceiptFieldValue(date.format(DateTimeFormatter.ISO_DATE), 0.92f, line)
            }
        }
        return null
    }

    private fun receiptNumber(lines: List<String>): ReceiptFieldValue? =
        lines.firstNotNullOfOrNull { line ->
            receiptNumberPattern.find(line)?.groupValues?.get(1)?.let {
                ReceiptFieldValue(it, 0.94f, line)
            }
        }

    private fun labelledMoney(
        lines: List<String>,
        labels: List<String>,
    ): ReceiptFieldValue? =
        lines.asReversed().firstNotNullOfOrNull { line ->
            if (labels.none { line.contains(it, ignoreCase = true) }) return@firstNotNullOfOrNull null
            moneyValues(line).lastOrNull()?.let {
                ReceiptFieldValue(it.abs().setScale(2).toPlainString(), 0.94f, line)
            }
        }

    private fun total(lines: List<String>): ReceiptFieldValue? {
        for ((index, label) in listOf("GRAND TOTAL", "TOTAL", "JUMLAH", "BAYAR").withIndex()) {
            lines.asReversed().forEach { line ->
                val upper = line.uppercase(Locale.ROOT)
                if (label == "TOTAL" && (upper.contains("SUBTOTAL") || upper.contains("SUB TOTAL"))) {
                    return@forEach
                }
                if (!Regex("\\b${Regex.escape(label)}\\b").containsMatchIn(upper)) return@forEach
                moneyValues(line).lastOrNull()?.let {
                    return ReceiptFieldValue(
                        it.abs().setScale(2).toPlainString(),
                        0.99f - (index * 0.03f),
                        line,
                    )
                }
            }
        }
        return null
    }

    private fun payment(lines: List<String>): ReceiptFieldValue? {
        val methods =
            linkedMapOf(
                "QRIS" to "QRIS",
                "TRANSFER" to "BANK_TRANSFER",
                "DEBIT" to "CARD",
                "KARTU" to "CARD",
                "TUNAI" to "CASH",
                "CASH" to "CASH",
            )
        lines.asReversed().forEach { line ->
            if (line.contains("KEMBALI", ignoreCase = true)) return@forEach
            methods.entries.firstOrNull { Regex("(?i)\\b${it.key}\\b").containsMatchIn(line) }
                ?.let { return ReceiptFieldValue(it.value, 0.92f, line) }
        }
        return null
    }

    private fun items(lines: List<String>): List<LocalReceiptItem> =
        lines.mapNotNull { line ->
            val upper = line.uppercase(Locale.ROOT)
            if (listOf("TOTAL", "JUMLAH", "BAYAR", "DISKON", "PAJAK", "PPN", "KEMBALI").any(upper::contains)) {
                return@mapNotNull null
            }
            val match = Regex("(?i)^(.*?)\\s+(${moneyPattern.pattern})$").find(line) ?: return@mapNotNull null
            val description = match.groupValues[1].trim(' ', '.', ':', '-')
            if (description.length < 2 || description.none(Char::isLetter)) return@mapNotNull null
            val amount = moneyValues(line).lastOrNull() ?: return@mapNotNull null
            LocalReceiptItem(description, amount.abs().setScale(2).toPlainString(), 0.76f)
        }

    private fun category(combined: String): ReceiptFieldValue {
        val rules =
            listOf(
                listOf("BENSIN", "PERTALITE", "SOLAR", "ONGKIR") to "TRANSPORTATION",
                listOf("PLN", "LISTRIK") to "ELECTRICITY",
                listOf("INTERNET", "WIFI", "PULSA") to "INTERNET",
                listOf("IKLAN", "PROMOSI", "BANNER") to "PROMOTION",
                listOf("KERTAS", "TINTA", "ATK") to "ADMINISTRATION",
                listOf("TEPUNG", "GULA", "MINYAK", "SAYUR", "DAGING") to "RAW_MATERIALS",
            )
        rules.firstOrNull { (keywords, _) -> keywords.any(combined::contains) }?.let {
            return ReceiptFieldValue(it.second, 0.84f, "Kata kunci nota")
        }
        return ReceiptFieldValue("PURCHASES", 0.65f, "Kategori umum pembelian")
    }

    private fun moneyValues(line: String): List<BigDecimal> =
        moneyPattern.findAll(line).mapNotNull { runCatching { parseMoney(it.groupValues[1]) }.getOrNull() }.toList()
}
