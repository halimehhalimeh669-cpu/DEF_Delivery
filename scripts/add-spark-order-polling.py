from pathlib import Path
import sys

root = Path(sys.argv[1])
gradle = root / "app/build.gradle.kts"
manifest = root / "app/src/main/AndroidManifest.xml"
activity = root / "app/src/main/java/com/example/MainActivity.kt"
worker = root / "app/src/main/java/com/example/AdminOrderPollingWorker.kt"

g = gradle.read_text()
if 'androidx.work:work-runtime-ktx' not in g:
    g = g.replace('dependencies {', 'dependencies {\n    implementation("androidx.work:work-runtime-ktx:2.10.1")', 1)
gradle.write_text(g)

m = manifest.read_text()
perm = '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />'
if perm not in m:
    m = m.replace('    <uses-permission android:name="android.permission.INTERNET" />',
                  '    <uses-permission android:name="android.permission.INTERNET" />\n' + perm, 1)
manifest.write_text(m)

a = activity.read_text()
if "import androidx.compose.ui.platform.LocalContext" not in a:
    a = a.replace("import androidx.compose.ui.platform.LocalLayoutDirection\\n", "import androidx.compose.ui.platform.LocalLayoutDirection\\nimport androidx.compose.ui.platform.LocalContext\\n", 1)
if "val context = LocalContext.current" not in a:
    a = a.replace("fun DEFDeliveryApp() {", "fun DEFDeliveryApp() {\\n    val context = LocalContext.current", 1)
needle = '                                            if (user?.isEmailVerified == true) {'
if 'AdminOrderPolling.start(context)' not in a:
    if needle not in a:
        raise SystemExit('Verified admin login insertion point not found')
    a = a.replace(needle, needle + '\n                                                AdminOrderPolling.start(this@MainActivity)', 1)
activity.write_text(a)

worker.write_text(r'''package com.example

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import com.google.firebase.firestore.Timestamp
import com.google.android.gms.tasks.Tasks
import java.util.Date
import java.util.concurrent.TimeUnit

object AdminOrderPolling {
    private const val PREFS = "def_admin_order_polling"
    private const val LAST_SEEN = "last_seen_created_at"

    fun start(context: Context) {
        val user = FirebaseAuth.getInstance().currentUser ?: return
        if (!user.email.equals("halimehhalimeh669@gmail.com", ignoreCase = true) ||
            user.isEmailVerified != true) return

        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        FirebaseFirestore.getInstance().collection("deliveryRequests")
            .orderBy("createdAt", Query.Direction.DESCENDING)
            .limit(1).get()
            .addOnSuccessListener { snapshot ->
                val latest = snapshot.documents.firstOrNull()?.getTimestamp("createdAt")
                if (latest != null && !prefs.contains(LAST_SEEN)) {
                    prefs.edit().putLong(LAST_SEEN, latest.toDate().time).apply()
                } else if (!prefs.contains(LAST_SEEN)) {
                    prefs.edit().putLong(LAST_SEEN, 0L).apply()
                }
                val request = PeriodicWorkRequestBuilder<AdminOrderPollingWorker>(15, TimeUnit.MINUTES)
                    .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                    .build()
                WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                    "def_delivery_new_order_poll",
                    ExistingPeriodicWorkPolicy.UPDATE,
                    request
                )
            }
    }
}

class AdminOrderPollingWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        val user = FirebaseAuth.getInstance().currentUser ?: return Result.success()
        if (!user.email.equals("halimehhalimeh669@gmail.com", ignoreCase = true) ||
            user.isEmailVerified != true) return Result.success()

        return try {
            val prefs = applicationContext.getSharedPreferences("def_admin_order_polling", Context.MODE_PRIVATE)
            val lastSeen = prefs.getLong("last_seen_created_at", 0L)
            val query = FirebaseFirestore.getInstance().collection("deliveryRequests")
                .whereGreaterThan("createdAt", Timestamp(Date(lastSeen)))
                .orderBy("createdAt", Query.Direction.ASCENDING)
            val snapshot = Tasks.await(query.get())
            if (snapshot.isEmpty) return Result.success()

            ensureChannel()
            var newest = lastSeen
            snapshot.documents.forEach { doc ->
                val createdAt = doc.getTimestamp("createdAt")?.toDate()?.time ?: lastSeen
                val name = doc.getString("customerName") ?: "Customer"
                showNotification(name, doc.id)
                if (createdAt > newest) newest = createdAt
            }
            if (newest > lastSeen) prefs.edit().putLong("last_seen_created_at", newest).apply()
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "def_new_orders_v2", "DEF Delivery - New Orders", NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts for new delivery requests"
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 250, 500)
                setSound(
                    android.provider.Settings.System.DEFAULT_NOTIFICATION_URI,
                    android.media.AudioAttributes.Builder()
                        .setUsage(android.media.AudioAttributes.USAGE_NOTIFICATION)
                        .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
            }
            (applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(channel)
        }
    }

    private fun showNotification(customerName: String, orderId: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(applicationContext, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) return
        val notification = NotificationCompat.Builder(applicationContext, "def_new_orders_v2")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("DEF Delivery - New Order!")
            .setContentText("New order from $customerName")
            .setStyle(NotificationCompat.BigTextStyle().bigText("A new delivery request has arrived. Order: $orderId"))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(applicationContext).notify(orderId.hashCode(), notification)
    }
}
''')
print("Spark-compatible WorkManager order polling patched")
