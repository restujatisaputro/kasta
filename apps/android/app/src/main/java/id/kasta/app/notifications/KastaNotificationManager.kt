package id.kasta.app.notifications

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import dagger.hilt.android.qualifiers.ApplicationContext
import id.kasta.app.MainActivity
import id.kasta.app.R
import id.kasta.app.data.local.NotificationEntity
import javax.inject.Inject
import javax.inject.Singleton

const val NOTIFICATION_ACTION_PATH = "notification_action_path"
private const val CHANNEL_REMINDERS = "kasta_reminders"

@Singleton
class KastaNotificationManager
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        fun createChannels() {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel =
                    NotificationChannel(
                        CHANNEL_REMINDERS,
                        "Pengingat KASTA",
                        NotificationManager.IMPORTANCE_DEFAULT,
                    ).apply {
                        description = "Pengingat transaksi, tagihan, stok, nota, dan pendampingan"
                    }
                context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
            }
        }

        @SuppressLint("MissingPermission")
        fun show(item: NotificationEntity) {
            if (
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) {
                return
            }
            val intent =
                Intent(context, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
                    putExtra(NOTIFICATION_ACTION_PATH, item.actionPath)
                }
            val pendingIntent =
                PendingIntent.getActivity(
                    context,
                    item.serverId.hashCode(),
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
                )
            val notification =
                NotificationCompat.Builder(context, CHANNEL_REMINDERS)
                    .setSmallIcon(R.drawable.ic_launcher)
                    .setContentTitle(item.title)
                    .setContentText(item.message)
                    .setStyle(NotificationCompat.BigTextStyle().bigText(item.message))
                    .setContentIntent(pendingIntent)
                    .setAutoCancel(true)
                    .setCategory(NotificationCompat.CATEGORY_REMINDER)
                    .build()
            try {
                NotificationManagerCompat.from(context).notify(item.serverId.hashCode(), notification)
            } catch (_: SecurityException) {
                // Izin dapat dicabut setelah pemeriksaan; pengingat cukup dilewati tanpa crash.
            }
        }
    }
