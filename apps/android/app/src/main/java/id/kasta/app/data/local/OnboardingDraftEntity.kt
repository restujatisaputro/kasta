package id.kasta.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "onboarding_drafts")
data class OnboardingDraftEntity(
    @PrimaryKey val id: Int = 1,
    val step: Int = 1,
    val businessName: String = "",
    val businessType: String = "TRADE",
    val categoryId: String = "",
    val scale: String = "MICRO",
    val establishedYear: String = "",
    val employeeCount: String = "0",
    val address: String = "",
    val village: String = "",
    val district: String = "",
    val city: String = "",
    val province: String = "",
    val businessPhone: String = "",
    val businessEmail: String = "",
    val currency: String = "IDR",
    val timezone: String = "Asia/Jakarta",
    val recordingMethod: String = "CASH",
    val paymentMethods: String = "CASH",
    val openingBalance: String = "0",
    val hasProducts: Boolean = false,
    val tutorialDone: Boolean = false,
)
