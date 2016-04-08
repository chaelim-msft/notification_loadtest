"""
Python simple test framework for Graph Notification service
by cslim@microsoft.com
"""
import json
import string
import random
import uuid
import requests
import hashlib
import base64
import datetime
from flask import Flask, request
from time import sleep
from datetime import datetime

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

app = Flask(__name__)

CHANGE_TYPES = ["Updated", "Created", "Deleted"]

DEF_PORT = 65000
DEF_NOTIFICATION_COUNT = 30
DEF_SUBSCRIPTION_URL = "http://localhost:202/1.0/subscriptions"
DEF_CLIENTSTATE = "SimpleLoadTest"
DEF_DELAY_SECONDS = 30
CLIENTSTATE_SECRET_PREFIX = "SubscriptionSecret-Begin-528e101c-a1e9-41df-bfb0-88caddc832de"

global g_port, g_notification_count, g_subscription_url, g_delay
g_port = DEF_PORT
g_notification_count = DEF_NOTIFICATION_COUNT
g_subscription_url = DEF_SUBSCRIPTION_URL
#g_clientState = DEF_CLIENTSTATE
g_delay = DEF_DELAY_SECONDS

total_notifications = 0

def encode_clientstate(clientState):
    return "".join( \
        [CLIENTSTATE_SECRET_PREFIX, "#1.0#", clientState])

###############################################################################
## Original format
###############################################################################

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


###############################################################################
## OneAPI format
###############################################################################
'''
Here we are using original PublishBatch request but recently Publish
API started using OneAPI format.

Note on Publish OneAPI format (internal wokrload to PubWeb):
    Must have: subscriptionId, clientState,  resource, userId
    Optional: changeType, tenantId, resourceData

{
    "subscriptionId":"d3b9c948-24f1-4fdb-a5d2-b597e22dbdc0",  <== This must be ExternalId. In EXO it's different from SubscriptionId
    "clientState":"test",
    "resource":"http://test/users/678f1640-3a40-4e6c-8d45-37c7743c0c82",
    "changeType":"Created",
    "tenantId":null,
    "resourceData":null
}
'''

def generate_random_notification_object_oneapi(extId, userId, tenantId, clientState):
    entityId = str(uuid.uuid4())
    resourceUrl = "https://sdfpilot.outlook.com/api/beta/users('{}@{}')/messages('{}')".format(userId, tenantId, entityId)
    
    notification_object = {
        "subscriptionId": extId,
        "clientState": clientState,
        "resource": resourceUrl,
        "changeType": random.choice(CHANGE_TYPES),
        "userId" :  userId,
        "tenantId" :  tenantId
    }
    
    return notification_object

def generate_random_notifications_oneapi(extId, userId, tenantId, clientState=DEF_CLIENTSTATE, secret=None, object_count=1):
    # Create test payload: Many notification for one subscription
    objects = []
    
    if secret:
        clientState = encode_clientstate(secret)

    for x in range(0, object_count):
        objects.append(generate_random_notification_object_oneapi(extId, userId, tenantId, clientState)) 

    return objects
    
# Create many notifications for one same subscriber
def create_notifications_for_one_sub_oneapi(pub_count, extId, clientState=DEF_CLIENTSTATE, secret=None):
    # Create test payload: Many notification for one subscription

    userId = str(uuid.uuid4())
    tenantId = str(uuid.uuid4())

    objects = generate_random_notifications_oneapi( \
        extId=extId, userId=userId, tenantId=tenantId, \
        clientState=clientState, \
        secret=secret, object_count=pub_count)

    payload = {
        "value": objects
    }

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

    if event_type.lower() == "create":
        # Create notification for one subscription
        # For OneAPI Format, especially in EXO, ExternalId is different from SubscriptionId
        # and that should be sent instead of SubscriptionId.
        create_notifications_for_one_sub_oneapi(g_notification_count, resp["ExternalId"], resp["Secret"], resp["Secret"])
        #create_notifications_for_one_sub(g_notification_count, resp["ExternalId"], resp["ClientState"])

    return ('', 200)


def random_str(size=1000, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

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
        #return (random_str(250), 200)
    else:
        responses = json.loads(request.data.decode('utf-8'))
        #print(json.dumps(responses, indent=4, separators=(',', ': ')))

        if (g_delay != 0 and len(responses["value"]) == 1):
            delay_seconds = abs(random.gauss(0, 1)) * g_delay
            print("Delay response for {0} seconds\n".format(delay_seconds))
            sleep(delay_seconds)

        for resp in responses["value"]:
            global total_notifications
            total_notifications += 1
            subId = resp["subscriptionId"] if "subscriptionId" in resp else resp["SubscriptionId"]
            print("[{0}] SubId={1}\n{2}\n".format( \
                total_notifications, \
                subId, \
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
    print("   -d, --delay: Average random delay (Default={0} secs)".format(DEF_DELAY_SECONDS))
    print("   -s, --suburl: Subscription url (Default={0})".format(DEF_SUBSCRIPTION_URL))

if __name__ == '__main__':
    import sys
    import getopt

    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "?hp:c:d:", ["help", "port=", "count=", "delay="])
    except getopt.GetoptError as err:
        print(err)
        print("for help use --help")
        sys.exit(2)

    # process options
    for o, a in opts:
        if o in ("-?", "-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-p", "--port"):
            g_port = int(a)
        elif o in ("-c", "--count"):
            g_notification_count = int(a)
        elif o in ("-d", "--delay"):
            g_delay = int(a)

    #app.run(debug=True, port=g_port)

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(g_port)
    IOLoop.instance().start()
