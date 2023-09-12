import requests
import os
import sys
import time

WORKSPACE = os.path.abspath(".")


def osrs():
  """
  Update OSRS database.
  """
  print("updating OSRS...")
  for i in range(10):
    time.sleep(1)
    print("updating OSRS... testing multiprocessing")
    

def rs():
  """
  Update RS database.
  """
  print("updating RS3...")
  for i in range(10):
    time.sleep(1)
    print("updating RS3... testing multiprocessing")

if __name__ == "__main__":
  print("running")
  ready_for_updates = []
  print('dir:', os.listdir(f"{WORKSPACE}/updater/status/"))
  for fn in os.listdir(f"{WORKSPACE}/updater/status/"):
    if os.path.isfile(f"{WORKSPACE}/updater/status/{fn}"):
      with open(f"{WORKSPACE}/updater/status/{fn}", 'r') as f:
        if f.read().strip() == "READY":
          ready_for_updates.append(fn.split("/")[-1])

  # TODO: change to multiprocess/multithread? thats why its seperate loop? idk
  for fn in ready_for_updates:
    if fn == "osrs":
      osrs()
    elif fn == "rs":
      rs()
    else:
      print(f"{fn} is an unsupported game mode!")


