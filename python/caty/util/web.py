# coding: utf-8
import caty.jsontools.xjson as json
from caty.util import merge_dict, memoize

import os.path

def merge_config(fs, path, config):
    conffile = '_filetypes.json'
    d, _ = os.path.split(path)
    f = os.path.join(d, conffile)
    fo = fs.FileObject(f, 'rb')
    if fo.exists:
        newconf = json.loads(fo.read())
    else:
        newconf = {}
    return merge_dict(config, newconf)
    #if d != '/' or d != '':
    #    return merge_config(fs, d, config)
    #else:

def is_hidden_path(path):
    if path == '/':
        return False
    d, f = os.path.split(path)
    if f.startswith('_'):
        return True
    else:
        return is_hidden_path(d)

def get_virtual_path(sitepath, access):
    if sitepath == '/' or len(sitepath) > len(access):
        return access
    else:
        l = len(os.path.commonprefix((sitepath, access)))
        return access[l:]

def find_encoding(content_type):
    if ';' in content_type:
        content_type, rest = map(lambda x: x.strip(), content_type.split(';', 1))
        if rest.startswith('charset'):
            return rest.split('=').pop(1)


HTTP_STATUS = {
    200: '200 OK',
    201: '201 Created',
    202: '202 Accepted',
    301: '301 Moved Permanently',
    302: '302 Found',
    400: '400 Bad Request',
    403: '403 Forbidden',
    404: '404 Not Found',
    405: '405 Method Not Allowed',
    415: '415 Unsupported Media Type',
    422: '422 Unprocessable Entity',
    409: '409 Conflict',
    500: '500 Internal Server Error',
    503: '503 Service Unavailable'
}

