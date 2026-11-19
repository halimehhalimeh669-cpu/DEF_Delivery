const { initializeApp } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const { getMessaging } = require("firebase-admin/messaging");
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const logger = require("firebase-functions/logger");

initializeApp();

exports.notifyAdminOnNewOrder = onDocumentCreated(
  {
    document: "deliveryRequests/{orderId}",
    region: "europe-west1",
  },
  async (event) => {
    const order = event.data?.data();
    if (!order) return;

    const devices = await getFirestore().collection("adminDevices").get();
    const tokens = devices.docs
      .map((doc) => ({ id: doc.id, token: doc.get("token") }))
      .filter((device) => typeof device.token === "string" && device.token.length > 0);

    if (tokens.length === 0) {
      logger.info("No registered DEF Delivery admin devices yet.");
      return;
    }

    const customer = String(order.customerName || "Customer").slice(0, 80);
    const result = await getMessaging().sendEachForMulticast({
      tokens: tokens.map((device) => device.token),
      notification: {
        title: "DEF Delivery - New Order",
        body: "New delivery request from " + customer,
      },
      data: {
        orderId: String(event.params.orderId),
        title: "DEF Delivery - New Order",
        body: "New delivery request from " + customer,
      },
      android: {
        priority: "high",
        notification: {
          channelId: "def_new_orders_v2",
          sound: "default",
          priority: "high",
        },
      },
    });

    const invalid = [];
    result.responses.forEach((response, index) => {
      if (!response.success) {
        const code = response.error?.code || "";
        if (
          code.includes("registration-token-not-registered") ||
          code.includes("invalid-registration-token")
        ) invalid.push(tokens[index].id);
        logger.warn("FCM send failed for an admin device", { code });
      }
    });

    await Promise.all(
      invalid.map((id) => getFirestore().collection("adminDevices").doc(id).delete())
    );
    logger.info("New-order push completed", {
      successCount: result.successCount,
      failureCount: result.failureCount,
    });
  }
);
