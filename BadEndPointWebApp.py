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

app = Flask(__name__)

# The base URL for the Microsoft Graph API.
GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0/{0}'
SUBSCRIPTION_URL = GRAPH_API_ENDPOINT.format('subscriptions/')

DEF_PORT = 65100
DEF_DELAY_SECONDS = 30

global g_access_token, g_port, g_delay
g_access_token = ''
g_port = DEF_PORT
g_delay = DEF_DELAY_SECONDS

total_notifications = 0


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def delete_mail(resource):
    # The resource URL for the sendMail action.
    resource_url = GRAPH_API_ENDPOINT.format(resource)
    
    # Set request headers.
    headers = { 
        'User-Agent' : 'BadEndPoint/1.0',
        'Authorization' : 'Bearer {0}'.format(g_access_token),
    }
    
    response = requests.delete(url = resource_url, headers = headers, params = None)

    if (response.status_code == 204):
        print("Message delete Succeeded: {0}".format(resource));
    else:
        print("Message delete failed: {0}, {1}".format(response.status_code, response.text))

@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    shutdown_server()
    return ('Server shutting down', 200)


@app.route('/notification', methods=['POST'])
def notification_callback():
    '''Receiving notificaion callback from Publisher
    '''
    cur_time = datetime.now()

    # Reply on validation request happens whenever subscription created
    validationToken = request.args.get('validationToken')
    if not validationToken:
        validationToken = request.args.get('validationtoken')
    if validationToken:
        print("{0}: Validation request received, token={1} ".format( \
            cur_time.isoformat(),
            validationToken))

        return (validationToken, 200)
    else:
        responses = json.loads(request.data.decode('utf-8'))
        #print(json.dumps(responses, indent=4, separators=(',', ': ')))

        if (g_delay != 0):
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
            # Delete message if created
            #if (resp["ChangeType"]  == "created"):
            #    delete_mail(resp["Resource"])

        print("###########################################################################")
        print("### {0}: {1:3d} notifications found in this message ###".format( \
            cur_time.isoformat(),
            len(responses["value"])))
        print("###########################################################################")

        return ('', 200)
#        return ('', 422)


@app.route("/")
def hello():
    return "Hello World!"


def usage():
    print("   -t, --token: Access Token (required)")
    print("   -d, --delay: Average random delay (Default={0} secs)".format(DEF_DELAY_SECONDS))

if __name__ == '__main__':
    import sys
    import getopt

    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "?ht:p:d:", ["help", "token=", "port=", "delay="])
    except getopt.GetoptError as err:
        print(err)
        print("for help use --help")
        sys.exit(2)

    # process options
    for o, a in opts:
        if o in ("-?", "-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-t", "--token"):
            g_access_token = str(a)
        elif o in ("-p", "--port"):
            g_port = int(a)
        elif o in ("-d", "--delay"):
            g_delay = int(a)

    app.run(debug=True, port=g_port)
