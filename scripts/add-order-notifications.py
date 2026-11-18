from pathlib import Path
import sys

root = Path(sys.argv[1])
activity = root / "app/src/main/java/com/example/MainActivity.kt"
manifest = root / "app/src/main/AndroidManifest.xml"
s = activity.read_text()

s = s.replace("import android.os.Bundle\n", """import android.os.Bundle
import android.Manifest
import android.content.pm.PackageManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
""", 1)
s = s.replace("import androidx.compose.ui.platform.LocalLayoutDirection\n",
              "import androidx.compose.ui.platform.LocalLayoutDirection\nimport androidx.compose.ui.platform.LocalContext\n", 1)

old = """class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { MyApplicationTheme { DEFDeliveryApp() } }
    }
}"""
new = """class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createOrderNotificationChannel()
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 7001)
        }
        enableEdgeToEdge()
        setContent { MyApplicationTheme { DEFDeliveryApp() } }
    }

    private fun createOrderNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "def_new_orders_v2", "DEF Delivery - New Orders", NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts when a new delivery request arrives"
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 250, 500)
                setSound(android.provider.Settings.System.DEFAULT_NOTIFICATION_URI,
                    android.media.AudioAttributes.Builder()
                        .setUsage(android.media.AudioAttributes.USAGE_NOTIFICATION)
                        .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build())
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    fun showNewOrderNotification(customerName: String, orderId: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        val notification = NotificationCompat.Builder(this, "def_new_orders_v2")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("DEF Delivery - New Order!")
            .setContentText(if (customerName.isBlank()) "A new delivery request has arrived." else "New order from $customerName")
            .setStyle(NotificationCompat.BigTextStyle().bigText("A new delivery request has arrived. Open DEF Delivery to view order $orderId."))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setAutoCancel(true)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .build()
        NotificationManagerCompat.from(this).notify(orderId.hashCode(), notification)
    }
}"""
if old not in s:
    raise SystemExit("MainActivity class template not found")
s = s.replace(old, new, 1)
s = s.replace("fun DEFDeliveryApp() {\n    var arabic", "fun DEFDeliveryApp() {\n    val context = LocalContext.current\n    var arabic", 1)

needle = """                                            adminListener?.remove()
                                            adminListener = FirebaseFirestore.getInstance().collection("deliveryRequests")"""
replacement = """                                            adminListener?.remove()
                                            var isFirstOrdersSnapshot = true
                                            adminListener = FirebaseFirestore.getInstance().collection("deliveryRequests")"""
if needle not in s:
    raise SystemExit("Admin listener setup not found")
s = s.replace(needle, replacement, 1)

needle = """                                                    } else if (snapshot != null) {
                                                        adminOrders = snapshot.documents.map { doc ->"""
replacement = """                                                    } else if (snapshot != null) {
                                                        if (isFirstOrdersSnapshot) {
                                                            isFirstOrdersSnapshot = false
                                                        } else if (!snapshot.metadata.isFromCache && snapshot.documentChanges.isNotEmpty()) {
                                                            snapshot.documentChanges
                                                                .filter { it.type == com.google.firebase.firestore.DocumentChange.Type.ADDED }
                                                                .forEach { change ->
                                                                    val customer = change.document.getString("customerName") ?: ""
                                                                    (context as? MainActivity)?.showNewOrderNotification(customer, change.document.id)
                                                                }
                                                        }
                                                        adminOrders = snapshot.documents.map { doc ->"""
if needle not in s:
    raise SystemExit("Snapshot callback insertion point not found")
s = s.replace(needle, replacement, 1)
activity.write_text(s)

m = manifest.read_text()
perm = '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />'
if perm not in m:
    m = m.replace('    <uses-permission android:name="android.permission.INTERNET" />',
                  '    <uses-permission android:name="android.permission.INTERNET" />\n' + perm, 1)
manifest.write_text(m)
