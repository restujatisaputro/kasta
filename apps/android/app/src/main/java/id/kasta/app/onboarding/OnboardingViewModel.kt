package id.kasta.app.onboarding

import androidx.compose.runtime.State
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject

@HiltViewModel
class OnboardingViewModel
    @Inject
    constructor(
        private val repository: OnboardingRepository,
    ) : ViewModel() {
        private val mutableState = mutableStateOf(OnboardingUiState())
        val state: State<OnboardingUiState> = mutableState

        init {
            viewModelScope.launch {
                repository.session()?.let { session ->
                    mutableState.value =
                        mutableState.value.copy(
                            screen = OnboardingScreen.TRANSACTIONS,
                            businessId = session.businessId,
                            accessToken = session.accessToken,
                            refreshToken = session.refreshToken,
                        )
                    return@launch
                }
                val draft = repository.restoreDraft()
                val categories = runCatching { repository.categories() }.getOrDefault(emptyList())
                mutableState.value =
                    (draft?.let(mutableState.value::restore) ?: mutableState.value).copy(
                        categories = categories,
                    )
            }
        }

        fun update(next: OnboardingUiState) {
            mutableState.value = next.copy(error = null, notice = null)
            if (next.step >= 3) {
                viewModelScope.launch { repository.saveDraft(mutableState.value) }
            }
        }

        fun createAccount() {
            val current = mutableState.value
            val error =
                when {
                    current.fullName.trim().length < 2 -> "Isi nama lengkap Anda."
                    current.identifier.trim().length < 8 -> "Isi email atau nomor telepon yang benar."
                    current.password.length < 12 -> "Password minimal 12 karakter."
                    else -> null
                }
            if (error != null) {
                mutableState.value = current.copy(error = error)
                return
            }
            launchRequest {
                repository.createAccount(current)
                mutableState.value =
                    current.copy(
                        step = 2,
                        password = "",
                        notice = "Petunjuk verifikasi sudah dikirim.",
                    )
            }
        }

        fun verify() {
            val current = mutableState.value
            if (current.verificationToken.trim().length < 20) {
                mutableState.value = current.copy(error = "Masukkan kode verifikasi dari pesan KASTA.")
                return
            }
            launchRequest {
                val token = repository.verify(current.verificationToken)
                mutableState.value =
                    current.copy(
                        step = 3,
                        verificationToken = "",
                        onboardingToken = token,
                        notice = "Akun sudah terverifikasi.",
                    )
            }
        }

        fun next() {
            val current = mutableState.value
            val error =
                when (current.step) {
                    4 ->
                        if (current.businessName.trim().length < 2 || current.categoryId.isBlank()) {
                            "Isi nama dan pilih kategori usaha."
                        } else {
                            null
                        }
                    6 ->
                        if (current.city.trim().length < 2 || current.province.trim().length < 2) {
                            "Isi kota dan provinsi usaha."
                        } else {
                            null
                        }
                    7 -> if (current.paymentMethods.isEmpty()) "Pilih cara menerima pembayaran." else null
                    else -> null
                }
            if (error != null) {
                mutableState.value = current.copy(error = error)
                return
            }
            update(current.copy(step = (current.step + 1).coerceAtMost(9)))
        }

        fun back() = update(mutableState.value.copy(step = (mutableState.value.step - 1).coerceAtLeast(1)))

        fun finish() {
            val current = mutableState.value
            if (!current.tutorialDone) {
                mutableState.value = current.copy(error = "Tandai bahwa tutorial sudah dipahami.")
                return
            }
            launchRequest {
                val result = repository.complete(current)
                repository.clearDraft()
                mutableState.value =
                    current.copy(
                        screen = OnboardingScreen.PROFILE,
                        profile = result.profile,
                        password = "",
                        verificationToken = "",
                        onboardingToken = "",
                        businessId = result.businessId,
                        accessToken = result.tokens.accessToken,
                        refreshToken = result.tokens.refreshToken,
                        notice = "Usaha siap digunakan.",
                    )
            }
        }

        fun openTransactions() {
            mutableState.value = mutableState.value.copy(screen = OnboardingScreen.TRANSACTIONS)
        }

        private fun launchRequest(block: suspend () -> Unit) {
            mutableState.value = mutableState.value.copy(busy = true, error = null)
            viewModelScope.launch {
                try {
                    block()
                } catch (error: OnboardingInputException) {
                    mutableState.value = mutableState.value.copy(error = error.message)
                } catch (_: IOException) {
                    mutableState.value =
                        mutableState.value.copy(
                            error = "Tidak dapat terhubung. Periksa internet lalu coba lagi.",
                        )
                } catch (error: HttpException) {
                    mutableState.value =
                        mutableState.value.copy(
                            error =
                                if (error.code() == 409) {
                                    "Email atau nomor telepon sudah digunakan."
                                } else {
                                    "Data belum dapat diproses. Periksa kembali isian Anda."
                                },
                        )
                } finally {
                    mutableState.value = mutableState.value.copy(busy = false)
                }
            }
        }
    }
