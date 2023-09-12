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

arg = sys.argv[1].replace("\\","/").split("/")[-1]
if arg == "osrs":
  osrs()
elif arg == "rs":
  rs()
else:
  print(f"{arg} is an unsupported game mode!")

