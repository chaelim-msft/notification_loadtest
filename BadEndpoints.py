import json
import requests
import uuid
import datetime
import subprocess
from urllib.request import urlopen
import re
import random

from multiprocessing.pool import Pool

# The OAuth authority.
AUTHORITY = "https://login.windows-ppe.net"         # PPE
#AUTHORITY = "https://login.microsoftonline.com"    # PROD

# The authorize URL that initiates the OAuth2 client credential flow for admin consent.
AUTHORIZE_URL = '{0}{1}'.format(AUTHORITY, '/common/oauth2/authorize?{0}')

# The token issuing endpoint.
TOKEN_URL = '{0}{1}'.format(AUTHORITY, '/{0}/oauth2/token')

RESOURCE_URL="https://graph.microsoft-ppe.com/" # PPE
#RESOURCE_URL="https://graph.microsoft.com/"     # PROD


# The base URL for the Microsoft Graph API.
GRAPH_API_ENDPOINT = 'https://graph.microsoft-ppe.com/beta/{0}' # PPE
#GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/beta/{0}' # PROD

SUBSCRIPTION_URL = GRAPH_API_ENDPOINT.format('subscriptions/')


def get_access_token(client_id, client_secret, tenantSubscriptionId, username, password):
    # Build the post form for the token request
    post_data = { 'grant_type': 'password',
                'client_id': client_id,
                'client_secret': client_secret,
                'resource': RESOURCE_URL,
                'username': username,
                'password': password
              }

    token_url = TOKEN_URL.format(tenantSubscriptionId)
    r = requests.post(token_url, data = post_data)

    try:
        return r.json()
    except:
        return 'Error retrieving token: {0} - {1}'.format(r.status_code, r.text)

def get_email_text(alias):
    return "<html><head><meta http-equiv='Content-Type' content='text/html; charset=us-ascii'> <title></title></head><body style='font-family:calibri'><p>Congratulations " + alias + ",</p><p>This is a message from the Office 365 Connect sample. You are well on your way to incorporating Office 365 services in your apps.</p><h3>What&#8217;s next?</h3><ul><li>Check out <a href='http://dev.office.com' target='_blank'>dev.office.com</a> to start building Office 365 apps today with all the latest tools, templates, and guidance to get started quickly.</li><li>Head over to the <a href='https://msdn.microsoft.com/office/office365/howto/office-365-unified-api-reference' target='blank'>API reference on MSDN</a> to explore the rest of the APIs.</li><li>Browse other <a href='https://github.com/OfficeDev/' target='_blank'>samples on GitHub</a> to see more of the APIs in action.</li></ul><h3>Give us feedback</h3> <ul><li>If you have any trouble running this sample, please <a href='http://github.com/OfficeDev/O365-Python-Microsoft-Graph-Connect/issues' target='_blank'>log an issue</a>.</li><li>For general questions about the Office 365 APIs, post to <a href='http://stackoverflow.com/' target='blank'>Stack Overflow</a>. Make sure that your questions or comments are tagged with [office365].</li></ul><p>Thanks and happy coding!<br>Your Office 365 Development team </p> <div style='text-align:center; font-family:calibri'> <table style='width:100%; font-family:calibri'> <tbody> <tr> <td><a href='http://github.com/OfficeDev/O365-Python-Microsoft-Graph-Connect'>See on GitHub</a> </td> <td><a href='http://officespdev.uservoice.com/'>Suggest on UserVoice</a> </td> <td><a href='http://twitter.com/share?text=I%20just%20started%20developing%20Python%20apps%20using%20the%20%23Office365%20Connect%20app!%20%40OfficeDev&url=http://github.com/OfficeDev/O365-Python-Microsoft-Graph-Connect'>Share on Twitter</a> </td> </tr> </tbody></table></div></body></html>"

def call_sendMail_endpoint(access_token, alias, emailAddress):
    # The resource URL for the sendMail action.
    send_mail_url = GRAPH_API_ENDPOINT.format('me/microsoft.graph.sendMail')
    
    # Set request headers.
    headers = { 
        'User-Agent' : 'BadEndPoint/1.0',
        'Authorization' : 'Bearer {0}'.format(access_token),
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    }
                        
    # Use these headers to instrument calls. Makes it easier
    # to correlate requests and responses in case of problems
    # and is a recommended best practice.
    request_id = str(uuid.uuid4())
    instrumentation = { 
        'client-request-id' : request_id,
        'return-client-request-id' : 'true' 
    }
    headers.update(instrumentation)
    
    # Create the email that is to be sent with API.
    email = {
        'Message': {
            'Subject': 'Simple Load Test : Sent at {0}'.format(datetime.datetime.now().strftime('%H%M%S.%f')),
            'Body': {
                'ContentType': 'HTML',
                'Content': get_email_text(alias)
            },
            'ToRecipients': [
                {
                    'EmailAddress': {
                        'Address': emailAddress
                    }
                }
            ]
        },
        'SaveToSentItems': 'false'
    }   

    response = requests.post(url = send_mail_url, headers = headers, data = json.dumps(email), params = None)

    # Check if the response is 202 (success) or not (failure).
    if (response.status_code == requests.codes.accepted):
        print("Message send Succeeded: {0}".format(response));
    else:
        print("Message send failed: {0}, {1}".format(response.status_code, response.text))

def create_subscription( \
    access_token=None,
    notification_url='https://287d4a7a.ngrok.io/notification',
    request_id=str(uuid.uuid4())):
    """Create a subscription and return subscription object from the reponse
    Reference: https://github.com/OfficeDev/O365-Python-Microsoft-Graph-Connect/blob/master/connect/graph_service.py
    """

    headers = { 
        'User-Agent' : 'BadEndPoint/1.0',
        'Authorization' : 'Bearer {0}'.format(access_token),
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

    expiration_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=4230)

    subscription = {
        "changeType": "Created,Updated,Deleted",
        "notificationUrl": notification_url,
        "clientState": "SimpleLoadTest{0}".format(datetime.datetime.now().strftime('%H%M%S.%f')),
        "resource": "me/messages",
        "expirationDateTime": expiration_time.astimezone().isoformat()  # iso 8601 with local time zone
    }

    response = requests.post( \
        url = SUBSCRIPTION_URL, \
        headers = headers, \
        data = json.dumps(subscription), params = None)

    response_json = json.loads(response.text)
    
    print("StatusCode = {0}\nReponse Body:\n{1}".format(response.status_code, json.dumps(response_json, indent=4, separators=(',', ': '))))

    # Check if the response is 201 (created) or not (failure).
    if (response.status_code == requests.codes.created):
        return response_json
    else:
        raise

def create_subscriptions(sub_data):
    DETACHED_PROCESS = 8

    pid = subprocess.Popen('ngrok.exe http 65100', creationflags=DETACHED_PROCESS, close_fds=True)

    for i in range(1, 40):
        try:
            response = urlopen('http://localhost:4040/status')
            html = response.read()

            # \"URL\":\"https://6f95a243.ngrok.io\"
            s = re.search(r'\\\\"URL\\\\":\\\\"([^\\]+)*', str(html))
            notification_url = '{0}/notification'.format(s.group(1))
            print('notification_url : {0}'.format(notification_url))

            #username = 'graphnot_cs1@a830edad9050849180E16031623.onmicrosoft.com'
            username = 'graphnot{0}@{1}'.format(i, sub_data['domain_name'])
            
            token = get_access_token( \
                'f0b94b56-53c6-4374-b651-c5c1b86a6ea1',
                'rURvVG3aL6UnYRzcxp42/64onaKdusrdGYtHmswlLec=',
                sub_data['urn'],
                username,
                'Hpop1234')
            access_token = token['access_token']

            print('access_token : ', access_token)

            # Create Subscription
            for j in range(1, 10):
                subscription = create_subscription(access_token, notification_url)

            #print("\nSubscription Created: subscriptionId = {0}".format(subscription["id"]))

            #for i in range(1):
            #    call_sendMail_endpoint(access_token, 'BadEndpoint', username)
            
            #call_sendMail_endpoint(access_token, 'BadEndpoint', 'cslim@microsoft.com')
        except:
            pass

    pid.kill()

def send_emails(sub_data):
    username = 'graphnot{0}@{1}'.format(random.randint(2, 40), sub_data['domain_name'])

    token = get_access_token( \
        'f0b94b56-53c6-4374-b651-c5c1b86a6ea1',         # CLIENT_ID
        'rURvVG3aL6UnYRzcxp42/64onaKdusrdGYtHmswlLec=', # APP_SECRET
        sub_data['urn'],
        username,
        'Hpop1234')

    access_token = token['access_token']
    print('access_token : ', access_token)

    for i in range(2000):
        recipient = 'graphnot{0}@{1}'.format(random.randint(1, 40), sub_data['domain_name'])
        print("{0} - {1}".format(recipient, i))
        call_sendMail_endpoint(access_token, 'BadEndpoint', username)

def usage():
    print("   -t, --token: Access Token (required)")

def main():
    import sys
    import getopt

    access_token = None
    
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "?hs:t:", ["help", "token"])
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
            access_token = str(a)

    subscriptions = [
        {
            'domain_name' : 'a830edad9050849337E16030415.ccsctp.net',
            'urn' : '735a5dce-2144-4d15-86c8-3f5634b3052b'
        },
        {
            'domain_name' : 'a830edad9050849337E16030414.ccsctp.net',
            'urn' : 'd5e5e640-572f-4800-83fe-9cbf029be31f'
        },
        {
            'domain_name' : 'a830edad9050849337E16030413.ccsctp.net',
            'urn' : '1a67a39b-8466-4e6a-9dab-655b259a5346'
        },
        { 
            'domain_name' : 'a830edad9050849337E16030411.ccsctp.net',
            'urn' : 'f91736e5-e674-467b-8f8f-db7cce818b5a'
        },
        {
            'domain_name' : 'a830edad9050849337E16030405.ccsctp.net',
            'urn' : 'ad1bffc8-1b93-4415-af6c-0b594fb3a0d0'
        }
    ]

    with Pool(20) as p:
        p.map(create_subscriptions, subscriptions)

    #for sub in subscriptions:
    #    create_subscriptions(sub['domain_name'], sub['urn'])

    # 2^3 times: To make total 40 tasks running in parallel.
    subscriptions.extend(subscriptions)
    subscriptions.extend(subscriptions)
    subscriptions.extend(subscriptions)
    with Pool(100) as p:
        p.map(send_emails, subscriptions)

    #send_emails()

if __name__ == "__main__":
    main()
