package id.kasta.app.notifications

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalTime

class NotificationTimeTest {
    @Test
    fun `quiet hours spanning midnight are respected`() {
        assertTrue(isQuiet(LocalTime.of(22, 30), true, "21:00", "07:00"))
        assertTrue(isQuiet(LocalTime.of(6, 30), true, "21:00", "07:00"))
        assertFalse(isQuiet(LocalTime.of(12, 0), true, "21:00", "07:00"))
    }

    @Test
    fun `disabled quiet hours never suppress notification`() {
        assertFalse(isQuiet(LocalTime.of(23, 0), false, "21:00", "07:00"))
    }
}
