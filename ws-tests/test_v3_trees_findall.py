#!/usr/bin/env python

# tests the find_trees method
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
CONTROLLER = DOMAIN + '/v3/studies'
SUBMIT_URI = CONTROLLER + '/find_trees'

# TEST 1: no parameters (should return all trees with only ot:studyId for each)
r = test_http_json_method(SUBMIT_URI,
                          'POST',
                          expected_status=200,
                          return_bool_data=True)

#structure of r is (true/false,json-results,true/false)
assert r[0] is True
json_result = r[1]
assert len(json_result) > 0
print "len",len(json_result)

# I have no idea how this next line ever evaluated to true
# r[1] is a dict, so dict[0] = KeyError
# assert r[1][0].keys() == ['ot:studyId']

# structure is { 'matched_studies' : [] } where each item in the list
# is a dict with only the key 'ot:studyId'
top_level_key = json_result.keys()[0]
assert json_result[top_level_key][0].keys() == ['ot:studyId','matched_trees']
