import os
import requests
WORKSPACE = os.getenv("WORKSPACE")
latest = requests.get("https://api.weirdgloop.org/exchange").json()
for k in latest:
  fn = f"{WORKSPACE}/updater/status/{k}"
  status = None
  if os.path.isfile(fn):
    with open(f"{WORKSPACE}/updater/status/{k}",'r') as f:
      status = f.read().strip()
  if status in {"UPDATING","READY"}:
    quit(0)
  elif latest[k] != status:
    print(f"{k} is out of date!")
    with open(f"{WORKSPACE}/updater/status/{k}",'r') as f:
      f.write("READY")  # Mark as ready to start the update action
