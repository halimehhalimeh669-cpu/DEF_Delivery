# تفعيل إشعارات الطلبات عبر FCM — DEF Delivery

تمت إضافة عميل Firebase Cloud Messaging إلى تطبيق Android ووظيفة Cloud Function لإرسال إشعار عند إنشاء طلب جديد.

## المطلوب مرة واحدة من مالك مشروع Firebase

1. افتح https://console.firebase.google.com/project/def-delivery/usage/details
2. فعّل خطة Blaze (الدفع حسب الاستخدام). Cloud Functions تحتاج مشروعاً على Blaze. أضف وسيلة دفع وتأكد من وضع ميزانية وتنبيهات إنفاق.
3. افتح Firebase Console > Project settings > Cloud Messaging وتأكد أن Cloud Messaging مفعّل للمشروع.
4. افتح Firebase Console > Firestore Database > Rules وانشر محتوى ملف `firestore.rules` الموجود بهذا المستودع. هذا يسمح فقط لحساب الإدارة الموثّق بتسجيل رمز جهازه في `adminDevices`.
5. انشر Cloud Function من Google Cloud Shell بعد تفعيل Blaze:
   - افتح https://console.cloud.google.com/?project=def-delivery
   - افتح Cloud Shell واكتب:
     ```bash
     git clone https://github.com/halimehhalimeh669-cpu/DEF_Delivery.git
     cd DEF_Delivery
     npm --prefix functions install
     npx firebase-tools login --no-localhost
     npx firebase-tools deploy --only functions --project def-delivery
     ```
   - وافق على تسجيل الدخول، ثم أكمل النشر. عند السؤال عن تفعيل APIs وافق.
6. بعد نجاح النشر، ثبّت آخر APK على هاتف الإدارة، افتح التطبيق وسجّل الدخول ببريد الإدارة الموثّق. التطبيق يسجّل FCM token تلقائياً في Firestore.
7. اطلب طلباً تجريبياً من هاتف آخر. يجب أن يصل إشعار حتى لو تطبيق الإدارة بالخلفية أو مغلقاً، ما دام الهاتف متصلاً بالإنترنت ولم يفرض النظام إيقاف التطبيق.

## ملاحظات أمان
- لا تضع Service Account JSON أو مفاتيح خاصة داخل المستودع أو APK.
- لا تشارك كلمات المرور أو مفاتيح Firebase.
- Cloud Function تعمل بصلاحيات Firebase Admin SDK وتقرأ رموز الأجهزة المسجلة فقط.
- إذا كان المشروع على Spark، لن تعمل Cloud Functions قبل الترقية إلى Blaze.
