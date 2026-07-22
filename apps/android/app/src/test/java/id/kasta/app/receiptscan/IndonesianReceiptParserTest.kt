package id.kasta.app.receiptscan

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal

class IndonesianReceiptParserTest {
    @Test
    fun `reads supported rupiah formats`() {
        assertEquals(BigDecimal("25000.00"), IndonesianReceiptParser.parseMoney("Rp25.000"))
        assertEquals(BigDecimal("25000.00"), IndonesianReceiptParser.parseMoney("Rp 25.000"))
        assertEquals(BigDecimal("25000.00"), IndonesianReceiptParser.parseMoney("25.000,00"))
        assertEquals(BigDecimal("25000.00"), IndonesianReceiptParser.parseMoney("25,000"))
    }

    @Test
    fun `extracts identity totals and payment`() {
        val parsed =
            IndonesianReceiptParser.parse(
                """
                TOKO MAJU
                No Nota: INV-2026-007
                Tanggal 21/07/2026
                SUBTOTAL 25.000
                DISKON 2.000
                PPN 2.500
                GRAND TOTAL Rp 25.500
                QRIS
                """.trimIndent(),
            )
        assertEquals("TOKO MAJU", parsed.fields.getValue("merchant_name").value)
        assertEquals("INV-2026-007", parsed.fields.getValue("receipt_number").value)
        assertEquals("2026-07-21", parsed.fields.getValue("receipt_date").value)
        assertEquals("25000.00", parsed.fields.getValue("subtotal").value)
        assertEquals("2000.00", parsed.fields.getValue("discount").value)
        assertEquals("2500.00", parsed.fields.getValue("tax").value)
        assertEquals("25500.00", parsed.fields.getValue("total").value)
        assertEquals("QRIS", parsed.fields.getValue("payment_method").value)
    }

    @Test
    fun `recommends expense and raw material category`() {
        val parsed = IndonesianReceiptParser.parse("TOKO BAHAN\nTepung 25.000\nTOTAL 25.000\nTUNAI")
        assertEquals("EXPENSE", parsed.fields.getValue("transaction_kind").value)
        assertEquals("RAW_MATERIALS", parsed.fields.getValue("category_account").value)
        assertTrue(parsed.items.any { it.description == "Tepung" })
    }

    @Test
    fun `recognizes sales receipt as income`() {
        val parsed = IndonesianReceiptParser.parse("TOKO MAJU\nSALES RECEIPT\nTOTAL 25.000\nDEBIT")
        assertEquals("INCOME", parsed.fields.getValue("transaction_kind").value)
        assertEquals("CARD", parsed.fields.getValue("payment_method").value)
    }
}
