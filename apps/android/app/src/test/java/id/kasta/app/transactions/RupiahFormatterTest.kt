package id.kasta.app.transactions

import org.junit.Assert.assertEquals
import org.junit.Test

class RupiahFormatterTest {
    @Test
    fun digitsAreGroupedWithoutUsingFloatingPoint() {
        assertEquals("125.000", formatRupiahDigits("125000"))
    }

    @Test
    fun blankDigitsStayBlank() {
        assertEquals("", formatRupiahDigits(""))
    }
}
