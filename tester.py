#!/usr/bin/env python3

'''
This is a tester module for the example/OpenData.yaml metadata file
'''

import yaml
from pprint import pprint

with open("example/OpenData.yaml") as stream:
    try:
        yml = yaml.load(stream, yaml.SafeLoader)  
        pprint(yml)
    except yaml.YAMLError as exc:
        print ("Error while parsing YAML file:")
        if hasattr(exc, 'problem_mark'):
            if exc.context != None:
                print ('  parser says\n' + str(exc.problem_mark) + '\n  ' +
                    str(exc.problem) + ' ' + str(exc.context) +
                    '\nPlease correct data and retry.')
            else:
                print ('  parser says\n' + str(exc.problem_mark) + '\n  ' +
                    str(exc.problem) + '\nPlease correct data and retry.')
        else:
            print ("Something went wrong while parsing yaml file")
        
