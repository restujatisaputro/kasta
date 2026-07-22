package id.kasta.app.transactions

enum class SyncWorkDecision {
    SUCCESS,
    RETRY,
}

fun decideSyncWork(completed: Boolean): SyncWorkDecision = if (completed) SyncWorkDecision.SUCCESS else SyncWorkDecision.RETRY
