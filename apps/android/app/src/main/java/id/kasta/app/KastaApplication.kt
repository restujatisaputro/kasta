package id.kasta.app

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import id.kasta.app.notifications.KastaNotificationManager
import id.kasta.app.notifications.NotificationScheduler
import javax.inject.Inject

@HiltAndroidApp
class KastaApplication : Application(), Configuration.Provider {
    @Inject lateinit var workerFactory: HiltWorkerFactory

    @Inject lateinit var notificationManager: KastaNotificationManager

    @Inject lateinit var notificationScheduler: NotificationScheduler

    override fun onCreate() {
        super.onCreate()
        notificationManager.createChannels()
        notificationScheduler.schedule()
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder().setWorkerFactory(workerFactory).build()
}
