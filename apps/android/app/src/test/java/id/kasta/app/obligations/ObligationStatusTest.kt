package id.kasta.app.obligations

import org.junit.Assert.assertEquals
import org.junit.Test

class ObligationStatusTest {
    @Test
    fun `status teknis ditampilkan dengan bahasa sederhana`() {
        assertEquals("Belum Dibayar", obligationStatusLabel("OPEN"))
        assertEquals("Dibayar Sebagian", obligationStatusLabel("PARTIALLY_PAID"))
        assertEquals("Sudah Lunas", obligationStatusLabel("PAID"))
        assertEquals("Terlambat", obligationStatusLabel("OVERDUE"))
    }
}
