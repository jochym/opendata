#!/usr/bin/env python3

'''
This is a tester module for the example/OpenData.yaml metadata file
'''

import yaml
from pprint import pprint

with open("example/OpenData.yaml") as stream:
    try:
        pprint(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        pprint(exc)