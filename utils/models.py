import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

class PostRequestException(Exception):
    pass

class RequestTimeoutException(Exception):
    pass

class InvalidPathError(Exception):
    pass

class ReadJSONFileError(Exception):
    pass