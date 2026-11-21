// BlForeground.kt — a foreground service any beam-lisp app can start.
//
// Android 14+ freezes an app's process seconds after it leaves the screen, so
// a BEAM that watches something on the user's behalf (sessions on a machine,
// a delivery, a timer) stops between frames. While this service runs, the
// process is not frozen. It shows one quiet ongoing notification, whose title
// and text the app chooses (intent extras "title" and "text"); tapping it
// opens the app. Started and stopped from bl with android.foreground.
//
// Type specialUse (the manifest says why, in the app's words, through the
// android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE property).
//
// One file on purpose: the build copies it as-is next to the app's sources.
// Lifted from Pocket Harness's WatchService (tiny-tools/mobile-app,
// scripts/add-watch-service.py), which ran it on API 35.
package io.beamlisp.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

class BlForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "Running in the background", NotificationManager.IMPORTANCE_MIN).apply {
            description = "Shown while the app keeps working with the screen off"
            setShowBadge(false)
        })
        val open = PendingIntent.getActivity(this, 0, packageManager.getLaunchIntentForPackage(packageName),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val title = intent?.getStringExtra("title") ?: applicationInfo.loadLabel(packageManager).toString()
        val text = intent?.getStringExtra("text") ?: "Working in the background"
        val n = Notification.Builder(this, CHANNEL)
            .setSmallIcon(applicationInfo.icon)
            .setContentTitle(title)
            .setContentText(text)
            .setContentIntent(open)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(ID, n)
        }
        return START_STICKY
    }

    companion object {
        const val CHANNEL = "bl_foreground"
        const val ID = 4711
    }
}
