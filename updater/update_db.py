import requests
import os
import sys
WORKSPACE = os.path.abspath(".")


def osrs():
  """
  Update OSRS database.
  """
  print("updating OSRS...")

def rs():
  """
  Update RS database.
  """
  print("updating RS3...")


if sys.argv[1] == "osrs":
  osrs()
elif sys.argv[1] == "rs":
  rs()
else:
  print(f"{sys.argv[1]} is an unsupported game mode!")

