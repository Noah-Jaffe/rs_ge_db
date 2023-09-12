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

  ready_for_updates = []
  for fn in os.listdir(f"{WORKSPACE}/updater/status/"):
    if os.path.isfile(fn):
      with open(fn, 'r') as f:
        d = f.read().strip()
        print(fn, d)
        if d == "READY":
          ready_for_updates.append(fn.split("/")[-1])

  # TODO: change to multiprocess/multithread? thats why its seperate loop? idk
  for fn in ready_for_updates:
    if arg == "osrs":
      osrs()
    elif arg == "rs":
      rs()
    else:
      print(f"{arg} is an unsupported game mode!")


