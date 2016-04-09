from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application, asynchronous
from WebApp import app, notification_callback
from tornado import gen

import json
import random
from datetime import datetime

DEF_PORT = 65000
DEF_DELAY_SECONDS = 30

global g_port, g_delay, g_total_notifications
g_port = DEF_PORT
g_delay = DEF_DELAY_SECONDS
g_total_notifications = 0

class MainHandler(RequestHandler):
    @asynchronous
    @gen.engine
    def post(self):
        cur_time = datetime.now()

        # Reply on validation request happens whenever subscription created
        validationToken = self.get_arguments('validationToken')
        if validationToken:
            print("{0}: Validation request received, token={1} ".format( \
                cur_time.isoformat(),
                validationToken))

            self.clear()
            self.set_status(200)
            self.finish(validationToken[0])
        else:
            responses = json.loads(self.request.body.decode('utf-8'))
            #print(json.dumps(responses, indent=4, separators=(',', ': ')))
            delay_seconds = 0
            if (g_delay != 0 and len(responses["value"]) == 1):
                delay_seconds = abs(random.gauss(0, 1)) * g_delay
                print("Delay response for {0:5.2f} seconds".format(delay_seconds))
                yield gen.sleep(delay_seconds)

            for resp in responses["value"]:
                global g_total_notifications
                g_total_notifications += 1
                subId = resp["subscriptionId"] if "subscriptionId" in resp else resp["SubscriptionId"]
                print("[{0}] SubId={1}\n{2}\n".format( \
                    g_total_notifications, \
                    subId, \
                    json.dumps(resp, indent=4, separators=(',', ': '))))

            print("###########################################################################")
            print("### {0} ({1:5.2f}): {2:3d} notifications found in this message ###".format( \
                cur_time.isoformat(),
                delay_seconds,
                len(responses["value"])))
            print("###########################################################################")

            self.clear()
            self.set_status(200)
            self.finish()

tr = WSGIContainer(app)

application = Application([
    (r"/notification", MainHandler),
    (r".*", FallbackHandler, dict(fallback=tr)),
])

if __name__ == "__main__":
    application.listen(65000)
    IOLoop.instance().start()