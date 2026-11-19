from pathlib import Path
import sys

root = Path(sys.argv[1])
gradle = root / "app/build.gradle.kts"
manifest = root / "app/src/main/AndroidManifest.xml"
activity = root / "app/src/main/java/com/example/MainActivity.kt"
rules = root / "firestore.rules"
service = root / "app/src/main/java/com/example/DefFirebaseMessagingService.kt"

g = gradle.read_text()
if 'com.google.firebase:firebase-messaging' not in g:
    g = g.replace('dependencies {', 'dependencies {\n  implementation("com.google.firebase:firebase-messaging")', 1)
gradle.write_text(g)

m = manifest.read_text()
entry = '''        <service
            android:name=".DefFirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>
'''
if 'DefFirebaseMessagingService' not in m:
    m = m.replace('        <activity', entry + '        <activity', 1)
manifest.write_text(m)

a = activity.read_text()
needle = '                                        if (user?.isEmailVerified == true) {'
replacement = needle + '\n                                            AdminFcmTokenRegistrar.register()'
if 'AdminFcmTokenRegistrar.register()' not in a:
    if needle not in a:
        raise SystemExit('Verified admin login insertion point not found')
    a = a.replace(needle, replacement, 1)
activity.write_text(a)

service.write_text(r'''package com.example

import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import java.security.MessageDigest

object AdminFcmTokenRegistrar {
    fun register() {
        FirebaseMessaging.getInstance().token
            .addOnSuccessListener { token -> saveToken(token) }
    }

    fun saveToken(token: String) {
        val user = FirebaseAuth.getInstance().currentUser ?: return
        if (!user.email.equals("halimehhalimeh669@gmail.com", ignoreCase = true) ||
            user.isEmailVerified != true) return

        val documentId = MessageDigest.getInstance("SHA-256")
            .digest(token.toByteArray())
            .joinToString("") { "%02x".format(it) }

        FirebaseFirestore.getInstance().collection("adminDevices")
            .document(documentId)
            .set(mapOf(
                "token" to token,
                "email" to user.email,
                "updatedAt" to FieldValue.serverTimestamp()
            ))
    }
}

class DefFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        AdminFcmTokenRegistrar.saveToken(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val title = message.notification?.title
            ?: message.data["title"] ?: "DEF Delivery - New Order"
        val body = message.notification?.body
            ?: message.data["body"] ?: "A new delivery request has arrived."

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "def_new_orders_v2",
                "DEF Delivery - New Orders",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
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
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, "def_new_orders_v2")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(this)
            .notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notification)
    }
}
''')

if rules.exists():
    r = rules.read_text()
    if 'match /adminDevices/{deviceId}' not in r:
        addition = '''
    // Only the verified admin device can register its own FCM destination token.
    match /adminDevices/{deviceId} {
      allow read: if isAdmin();
      allow create, update: if isAdmin()
        && request.resource.data.keys().hasOnly(['token', 'email', 'updatedAt'])
        && request.resource.data.token is string
        && request.resource.data.email == 'halimehhalimeh669@gmail.com';
      allow delete: if isAdmin();
    }

'''
        r = r.replace('  }\n}', addition + '  }\n}', 1)
        rules.write_text(r)
print('FCM Android client integration patched')
