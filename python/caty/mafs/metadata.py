#coding: utf-8
u"""mafs メタデータモジュール。
mafs バックエンドの実装者以外はこのモジュールを直接使う必要はない。
"""

import os
import time
import datetime
import re
from caty.util import merge_dict

def timestamp(sec):
    return datetime.datetime(*(time.localtime(sec)[:-3]))

class MetadataRegistrar(object):
    def __init__(self, mime_types):
        if mime_types is None: mime_types = {}
        TEXT_TYPES = [
        ]
        self._types = merge_dict(mime_types, default_types, 'pre')
        for k, v in self._types.items():
            if v['isText']:
                TEXT_TYPES.append(v['contentType'])

        def mime_type(ext):
            if not ext: return 'application/octet-stream'
            return self._types.get(ext, {}).get('contentType', 'application/octet-stream')

        def is_text_ext(ext):
            return mime_type(ext) in TEXT_TYPES

        class FileMetadata(object):
            is_dir = False
            def __init__(self, 
                    contentLength, 
                    lastModified, 
                    contentType,
                    executable = False,
                    hidden = False,
                    readOnly = False,
                    created = 0):
                self.__contentLength = contentLength
                self.__lastModified = timestamp(lastModified)
                self.__contentType = contentType
                self.__executable = executable
                self.__hidden = hidden
                self.__readOnly = readOnly
                if created:
                    self.__created = timestamp(created)
                else:
                    self.__created = None

            @property
            def contentLength(self):
                return self.__contentLength

            @property
            def lastModified(self):
                return self.__lastModified

            @property
            def contentType(self):
                return self.__contentType
                
            @property
            def isText(self):
                return self.contentType in TEXT_TYPES

            @property
            def executable(self):
                return self.__executable

            @property
            def hidden(self):
                return self.__hidden

            @property
            def readOnly(self):
                return self.__readOnly

            @property
            def created(self):
                return self.__created

        class DirectoryMetadata(object):
            is_dir = True
            def __init__(self, lastModified, hidden=False, readOnly=False, created=0):
                self.__lastModified = timestamp(lastModified)
                self.__hidden = hidden
                self.__readOnly = readOnly
                if created:
                    self.__created = timestamp(created)
                else:
                    self.__created = None

            @property
            def lastModified(self):
                return self.__lastModified

            @property
            def readOnly(self):
                return self.__readOnly

            @property
            def hidden(self):
                return self.__hidden
                
            @property
            def created(self):
                return self.__created


        self._mime_type = mime_type
        self._is_text_ext = is_text_ext
        self._fm = FileMetadata
        self._dm = DirectoryMetadata

    @property
    def mime_type(self):
        return self._mime_type
    
    @property
    def is_text_ext(self):
        return self._is_text_ext

    @property
    def FileMetadata(self):
        return self._fm

    def all_types(self):
        import copy
        d = {}
        for k, v in self._types.items():
            d[k] = copy.deepcopy(v)
            if 'assoc' in d[k]: # 本来 assoc はあるはずだが？
                del d[k]['assoc']
        return d

    @property
    def DirectoryMetadata(self):
        return self._dm

class DirectoryEntry(object):
    def __init__(self, path, metadata):
        self.__name = os.path.basename(path)
        self.__metadata = metadata
        self.__path = path

    @property
    def path(self):
        return self.__path

    @property
    def name(self):
        return self.__name

    @property
    def metadata(self):
        return self.__metadata

    @property
    def is_dir(self):
        return self.metadata.is_dir


default_types = {
    u".js": {
        u"isText": True, 
        u"contentType": u"application/x-javascript"
    }, 
    u".css": {
        u"isText": True, 
        u"contentType": u"text/css"
    }, 
    u".pdf": {
        u"isText": False, 
        u"contentType": u"application/pdf"
    }, 
    u".jpe": {
        u"isText": False, 
        u"contentType": u"image/jpeg"
    }, 
    u".jpg": {
        u"isText": False, 
        u"contentType": u"image/jpeg"
    }, 
    u".xml": {
        u"isText": True, 
        u"contentType": u"text/xml"
    }, 
    u".jpeg": {
        u"isText": False, 
        u"contentType": u"image/jpeg"
    }, 
    u".ps": {
        u"isText": False, 
        u"contentType": u"application/postscript"
    }, 
    u".tsv": {
        u"isText": True, 
        u"contentType": u"text/tab-separated-values"
    }, 
    u".caty": {
        u"isText": True, 
        u"contentType": u"application/x-tex"
    }, 
    u".gif": {
        u"isText": False, 
        u"contentType": u"image/gif"
    }, 
    u".html": {
        u"isText": True, 
        u"contentType": u"text/html"
    }, 
    u".txt": {
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".mpeg": {
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".rdf": {
        u"isText": True, 
        u"contentType": u"application/rdf+xml"
    }, 
    u".wav": {
         
        u"isText": False, 
        u"contentType": u"audio/x-wav"
    }, 
    u".mpg": {
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".mpe": {
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".htm": {
        u"isText": True, 
        u"contentType": u"text/html"
    }, 
    u".xhtml": {
        u"isText": True, 
        u"contentType": u"text/html"
    }, 
    u".zip": {
        u"isText": False, 
        u"contentType": u"application/zip"
    }, 
    u".png": {
        u"isText": False, 
        u"contentType": u"image/png"
    }, 
    u".svg": {
        u"isText": True, 
        u"contentType": u"image/svg+xml"
    },
    u".svge": {
        u"isText": True, 
        u"contentType": u"image/svg+xml"
    },
    u".mp3": {
        u"isText": False, 
        u"contentType": u"audio/mpeg"
    }, 
    u".caty": {
        u"isText": True,
        u"contentType": u""
    },
    u".icaty": {
        u"isText": True,
        u"contentType": u""
    },
    u".json": {
        u"isText": True,
        u"contentType": u"application/json"
    },
    u".atom": {
        u"isText": True,
        u"contentType": u"application/atom+xml"
    },
    u".casm": {
        u"isText": True,
        u"contentType": u""
    },
    u".xjson": {
        u"isText": True,
        u"contentType": u"application/json"
    },
    u".csv": {
        u"isText": True,
        u"contentType": u"text/csv"
    },
    # 一応、念のため
    u".cgi": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".eps": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".dot": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".beh": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".cara": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".lit": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".tar": {
        u"isText": False,
        u"contentType": u"application/x-tar"
    },
    u".gz": {
        u"isText": False,
        u"contentType": u"application/gzip"
    },
    u".ogg": {
        u"isText": False,
        u"contentType": u"application/ogg"
    },
    u".bmp": {
        u"isText": False,
        u"contentType": u"image/bmp"
    },
    u".tex": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
    # これがないと一部システムが正常に動作しない
    u".py": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
}

