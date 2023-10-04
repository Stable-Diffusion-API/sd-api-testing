import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

# Headers for the POST request
HEADERS = {
    "Content-Type": "application/json",
}

API_KEY = "pmuIKpTqevUMwwsBTFZX4EMnmURGEhL6hFZdbJgs0yVQOMkqoJxGt3bXQkUk"

# Maximum number of retries
MAX_RETRIES = 3

# Timeout in seconds
TIMEOUT = 120
SLEEP_TIME = 30

API_CALLS = 50