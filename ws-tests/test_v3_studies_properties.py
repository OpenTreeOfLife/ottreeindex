
# tests the v2/v3 (oti) implementation of the 'properties' method
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
CONTROLLER = DOMAIN + '/v3/studies'
SUBMIT_URI = CONTROLLER + '/properties'
r = test_http_json_method(SUBMIT_URI,
                          'POST',
                          expected_status=200,
                          return_bool_data=True)
assert r[0] is True
k = r[1].keys()
assert 'study_properties' in k
assert isinstance(r[1]['tree_properties'], list)
# print 'study props:',len(r[1]['study_properties'])
# print 'tree props:',len(r[1]['tree_properties'])
