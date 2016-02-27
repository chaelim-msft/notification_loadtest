"""
Generating test Json files can be used input for Publisher.Client.Tool
by cslim@microsoft.com
"""
import json
import requests
import uuid

DEF_SUBSCRIPTION_URL = "http://localhost:202/1.0/subscriptions"

def create_subscription(\
    sub_url="http://localhost:202/1.0/subscriptions", \
    request_id=str(uuid.uuid4())):
    """Create a subscription and return subscription object from the reponse
    """

    headers = { 
        'User-Agent' : 'SimpleLoadTest/1.0',
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    }
    
    # Use these headers to instrument calls. Makes it easier
    # to correlate requests and responses in case of problems
    # and is a recommended best practice.
    instrumentation = { 
        'client-request-id' : request_id,
        'return-client-request-id' : 'true' 
    }
    headers.update(instrumentation)

    with open('Subscription.json') as data_file:    
        subscription = json.load(data_file)

    response = requests.post( \
        url = sub_url, \
        headers = headers, \
        data = json.dumps(subscription), params = None)

    response_json = json.loads(response.text)
    
    print("StatusCode = {0}\nReponse Body:\n{1}".format(response.status_code, json.dumps(response_json, indent=4, separators=(',', ': '))))

    # Check if the response is 201 (created) or not (failure).
    if (response.status_code == requests.codes.created):
        return response_json
    else:
        raise


def usage():
    print("   -s, --suburl: Subscription url (Default={0})".format(DEF_SUBSCRIPTION_URL))


def main():
    import sys
    import getopt

    subscription_url = DEF_SUBSCRIPTION_URL

    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "?hs:", ["help", "suburl"])
    except getopt.GetoptError as err:
        print(err)
        print("for help use --help")
        sys.exit(2)

    # process options
    for o, a in opts:
        if o in ("-?", "-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("-s", "--suburl"):
            subscription_url = str(a)

    # Create Subscription
    subscription = create_subscription(subscription_url)

    print("\nSubscription Created: subscriptionId = {0}".format(subscription["subscriptionId"]))

if __name__ == "__main__":
    main()