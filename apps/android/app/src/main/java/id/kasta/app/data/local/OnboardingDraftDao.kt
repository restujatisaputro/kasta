package id.kasta.app.data.local

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface OnboardingDraftDao {
    @Query("SELECT * FROM onboarding_drafts WHERE id = 1")
    fun observe(): Flow<OnboardingDraftEntity?>

    @Upsert
    suspend fun save(draft: OnboardingDraftEntity)

    @Query("DELETE FROM onboarding_drafts")
    suspend fun clear()
}
