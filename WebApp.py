"""
Python simple test framework for Graph Notification service
by cslim@microsoft.com
"""
import json
import random
import uuid
import requests
import hashlib
import base64
from flask import Flask, request
from time import sleep
from datetime import datetime

app = Flask(__name__)

CHANGE_TYPES = ["Updated", "Created"]

DEF_NOTIFICATION_COUNT = 30
DEF_SUBSCRIPTION_URL = "http://localhost:202/1.0/subscriptions"
DEF_CLIENTSTATE = "SimpleLoadTest"
CLIENTSTATE_SECRET_PREFIX = "SubscriptionSecret-Begin-528e101c-a1e9-41df-bfb0-88caddc832de"

global g_notification_count, g_subscription_url, g_delay
g_notification_count = DEF_NOTIFICATION_COUNT
g_subscription_url = DEF_SUBSCRIPTION_URL
#g_clientState = DEF_CLIENTSTATE
g_delay = False

total_notifications = 0

def encode_clientstate(clientState):
    return "".join( \
        [CLIENTSTATE_SECRET_PREFIX, "#1.0#", clientState])

'''
Here we are using original PublishBatch request but recently Publish
API started using OneAPI format.

Note on Publish OneAPI format:
    Must have: subscriptionId, clientState, resource
    Optional: changeType, userId, tenantId, resourceData

{
    "subscriptionId":"d3b9c948-24f1-4fdb-a5d2-b597e22dbdc0",  <== This must be ExternalId. In EXO it's different from SubscriptionID
    "changeType":"Create",
    "resource":"http://test/users/678f1640-3a40-4e6c-8d45-37c7743c0c82",
    "tenantId":null,
    "clientState":null,
    "resourceData":null
}
'''

def generate_random_notification_object(clientState):
    '''This is original notification format for PublishBatchAsync in 
    PublicationClient.cs.
    '''
    objectId = str(uuid.uuid4())
    notification_object = {
        "clientState": clientState,
        "Identifier" :  {
            "ObjectIdentifier": objectId,
            "ObjectType":"User"
        },
        "changeTypes": random.choice(CHANGE_TYPES),
        "resourceUrl": "http://test/users/" + objectId
    }
    
    return notification_object

def generate_random_notifications(subId=str(uuid.uuid4()), clientState=DEF_CLIENTSTATE, secret=None, object_count=1):
    # Create test payload: Many notification for one subscription
    objects = []
    
    if secret:
        clientState = encode_clientstate(secret)

    for x in range(0, object_count):
        objects.append(generate_random_notification_object(clientState)) 
    
    # NOTE: "Objects" will be removed and flattened as root level key/value pairs
    #   by "Publisher\Publisher\Client\PublicationClient.cs"
    notification = {
        "SubscriptionId": subId,
        "Options": "DisableUrlTranslation",
        "Objects": objects
    }

    return notification

# Create many notifications for one same subscriber
def create_notifications_for_one_sub(pub_count, subId = str(uuid.uuid4()), clientState=DEF_CLIENTSTATE, secret=None):
    # Create test payload: Many notification for one subscription
    payload = []

    for x in range(0, pub_count):
        payload.append(generate_random_notifications( \
            subId=subId, clientState=clientState, secret=secret, object_count=random.randint(1, 1)))

    with open('Notifications.json', 'w') as f:   
        json.dump(payload, f, sort_keys=False, indent=2, ensure_ascii=False)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    shutdown_server()
    return ('Server shutting down', 200)

@app.route('/interactive_event/<event_type>', methods=['POST'])
def oninteractive_event(event_type):
    '''Receiving interactive events from ExampleStorageExtension
    '''
    resp = json.loads(request.data.decode('utf-8'))
    print(json.dumps(resp, indent=4, separators=(',', ': ')))
    
    global notification_count
    
    if event_type.lower() == "create":
        # Create notification for one subscription
        # For OneAPI Format, especially in EXO, ExternalId is different from SubscriptionId
        # and that should be sent instead of SubscriptionId.
        #create_notifications_for_one_sub(notification_count, resp["SubscriptionId"], resp["Secret"], resp["Secret"]) <= OneAPI format
        create_notifications_for_one_sub(notification_count, resp["SubscriptionId"], resp["ClientState"])

    return ('', 200)


@app.route('/notification', methods=['POST'])
def notification_callback():
    '''Receiving notificaion callback from Publisher
    '''
    cur_time = datetime.now()

    # Reply on validation request happens whenever subscription created
    validationToken = request.args.get('validationToken')
    if validationToken:
        print("{0}: Validation request received, token={1} ".format( \
            cur_time.isoformat(),
            validationToken))

        return (validationToken, 200)
    else:
        responses = json.loads(request.data.decode('utf-8'))
        #print(json.dumps(responses, indent=4, separators=(',', ': ')))

        if g_delay:
            delay_seconds = abs(random.gauss(0, 1)) * 30
            print("Delay response for {0} seconds\n".format(delay_seconds))
            sleep(delay_seconds)

        for resp in responses["value"]:
            global total_notifications
            total_notifications += 1
            print("[{0}] SubId={1}\n{2}\n".format( \
                total_notifications, \
                resp["subscriptionId"], \
                json.dumps(resp, indent=4, separators=(',', ': '))))

        print("###########################################################################")
        print("### {0}: {1:3d} notifications found in this message ###".format( \
            cur_time.isoformat(),
            len(responses["value"])))
        print("###########################################################################")

        return ('', 200)


@app.route("/")
def hello():
    return "Hello World!"


def usage():
    print("   -c, --count : Number of notifications (Default={0})".format(DEF_NOTIFICATION_COUNT))
    print("   -s, --suburl: Subscription url (Default={0})".format(DEF_SUBSCRIPTION_URL))

if __name__ == '__main__':
    import sys
    import getopt

    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "?hc:d:", ["help", "count", "delay"])
    except getopt.GetoptError as err:
        print(err)
        print("for help use --help")
        sys.exit(2)

    # process options
    for o, a in opts:
        if o in ("-?", "-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-c", "--count"):
            g_notification_count = int(a)
        elif o in ("-d", "--delay"):
            g_delay = True

    app.run(debug=True, port=65000)