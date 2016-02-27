# Using ngrok and listening PROD events #

----------

1. Run `ngrok 65000` and get URL
2. Run python `WebApp.py`
3. Go to `http://notificationstest2.azurewebsites.net/`
4. Select Resource and Change Types and Enter Notification Url from #1 (e.g. `https://69dde936.ngrok.io/notification`)
5. Inspect from `http://127.0.0.1:4040/inspect/http` 