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
    sleep(1)
    print("updating OSRS... testing multiprocessing")
    

def rs():
  """
  Update RS database.
  """
  print("updating RS3...")
  for i in range(10):
    sleep(1)
    print("updating RS3... testing multiprocessing")


if sys.argv[1] == "osrs":
  osrs()
elif sys.argv[1] == "rs":
  rs()
else:
  print(f"{sys.argv[1]} is an unsupported game mode!")

