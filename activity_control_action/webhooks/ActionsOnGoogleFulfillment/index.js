const {
  conversation,
  Suggestion,
} = require('@assistant/conversation');
const functions = require('firebase-functions');
const {GoogleAuth} = require('google-auth-library');
const request = require('request');
const util = require('util');

const auth = new GoogleAuth({
  scopes: 'https://www.googleapis.com/auth/actions.fulfillment.conversation'
});
let client;

const sendPostRequest = util.promisify(request.post);
const sendGetRequest = util.promisify(request.get);

/**
 * Send a push notification via POST request to the Actions API endpoint
 * @param {object} accessToken Access token provided as the Authorization bearer token.
 * @param {object} notification Push notification specifying target user and intent.
 * @return {object} the response of the post request.
 */
async function sendPushNotification(accessToken, notification) {
  const response = await sendPostRequest('https://actions.googleapis.com/v2/conversations:send', {
    'auth': {
      'bearer': accessToken,
    },
    'json': true,
    'body': {'customPushMessage': notification, 'isInSandbox': true},
  });
  return response;
}

const app = conversation({debug: true});

app.handle('classes', (conv) => {
  const day = conv.intent.params.day ?
    conv.intent.params.day.resolved : DAYS[new Date().getDay()];
  const classes =
    [...new Set(schedule.days[day].map((d) => `${d.name} at ${d.startTime}`))]
    .join(', ');
  conv.add(`On ${day} we offer the following classes: ${classes}. ` +
    `Would you like to receive daily reminders of upcoming ` +
    `classes, subscribe to notifications about cancelations, or can I help ` +
    `you with anything else?`);
  conv.add(new Suggestion({ title: SuggestionTitle.DAILY}));
  conv.add(new Suggestion({ title: SuggestionTitle.NOTIFICATIONS}));
  conv.add(new Suggestion({ title: SuggestionTitle.HOURS}));
});


app.handle('activity_control_webhook', async (conv) => {
  console.log('here');
  
  var act = conv.intent.params.activities.resolved;
	var period = conv.intent.params.period.resolved;
  console.log(act);
  console.log(period);
  var resp = await sendPostRequest('http://40.112.89.136:3390/setwarningvalue',{
      'json': true,
      'body': {'activity' : act, 'hours': period, 'minutes': 0}
    } );
  
  conv.add(resp.body);
  conv.add(new Suggestion({ title: 'Ok!'}));
});

app.handle('subscribe_to_notifications', (conv) => {
  const intentName = 'notification_trigger';
  const notificationsSlot =
    conv.session.params[`NotificationsSlot_${intentName}`];
  if (notificationsSlot.permissionStatus === 'PERMISSION_GRANTED') {
    const updateUserId = notificationsSlot.additionalUserData.updateUserId;
    // Store the user ID and the notification’s target intent for later use.
    // (Use a database like Firestore for best practice).
    if (!conv.user.params.notificationSubscriptions) {
      conv.user.params.notificationSubscriptions = [];
    }
    conv.user.params.notificationSubscriptions.push({
      userId: updateUserId,
      intent: intentName,
    });
  }
});

// Trigger a test push notification mid-conversation
app.handle('cancel_class', async (conv) => {
  // Lazy-load client
  // See https://github.com/googleapis/google-auth-library-nodejs/issues/798
  if (!client) {
    client = await auth.getClient()
  }

  let accessToken;
  try {
    accessToken = await client.getAccessToken();
  } catch(err) {
    throw new Error(`Auth error: ${err}`);
  }
  // Send push notifications to every user who’s
  // currently opted in to receiving notifications.
  const notificationPromises =
    conv.user.params.notificationSubscriptions.map((subscription) => {
      const notification = {
        userNotification: {
          title: 'Test Notification from Action Gym',
        },
        target: {
          userId: subscription.userId,
          intent: subscription.intent,
        },
      };
      return sendPushNotification(accessToken, notification);
    });
  try {
    await Promise.all(notificationPromises);
    conv.add('A notification has been sent to all subscribed users.');
  } catch(err) {
    throw new Error(`Error when sending notifications: ${err}`);
  }
});

exports.ActionsOnGoogleFulfillment = functions.https.onRequest(app);

