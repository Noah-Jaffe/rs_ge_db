import os
import requests
with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
  print(requests.get("https://api.weirdgloop.org/exchange").json(), file=fh)
