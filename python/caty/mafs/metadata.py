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
    u".obj": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".ra": {
         
        u"isText": False, 
        u"contentType": u"audio/x-pn-realaudio"
    }, 
    u".wsdl": {
         
        u"isText": False, 
        u"contentType": u"application/xml"
    }, 
    u".dll": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".ras": {
         
        u"isText": False, 
        u"contentType": u"image/x-cmu-raster"
    }, 
    u".ram": {
         
        u"isText": False, 
        u"contentType": u"application/x-pn-realaudio"
    }, 
    u".bcpio": {
         
        u"isText": False, 
        u"contentType": u"application/x-bcpio"
    }, 
    u".m1v": {
         
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".xwd": {
         
        u"isText": False, 
        u"contentType": u"image/x-xwindowdump"
    }, 
    u".avi": {
         
        u"isText": False, 
        u"contentType": u"video/x-msvideo"
    }, 
    u".bmp": {
         
        u"isText": False, 
        u"contentType": u"image/x-ms-bmp"
    }, 
    u".shar": {
         
        u"isText": False, 
        u"contentType": u"application/x-shar"
    }, 
    u".js": {
         
        u"isText": True, 
        u"contentType": u"application/x-javascript"
    }, 
    u".dvi": {
         
        u"isText": False, 
        u"contentType": u"application/x-dvi"
    }, 
    u".aif": {
         
        u"isText": False, 
        u"contentType": u"audio/x-aiff"
    }, 
    u".ksh": {
         
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".dot": {
         
        u"isText": False, 
        u"contentType": u"application/msword"
    }, 
    u".mht": {
         
        u"isText": True, 
        u"contentType": u"message/rfc822"
    }, 
    u".vcf": {
         
        u"isText": False, 
        u"contentType": u"text/x-vcard"
    }, 
    u".css": {
         
        u"isText": True, 
        u"contentType": u"text/css"
    }, 
    u".csh": {
         
        u"isText": True, 
        u"contentType": u"application/x-csh"
    }, 
    u".pwz": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-powerpoint"
    }, 
    u".pdf": {
         
        u"isText": False, 
        u"contentType": u"application/pdf"
    }, 
    u".cdf": {
         
        u"isText": False, 
        u"contentType": u"application/x-netcdf"
    }, 
    u".pl": {
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".p12": {
         
        u"isText": False, 
        u"contentType": u"application/x-pkcs12"
    }, 
    u".jpe": {
         
        u"isText": False, 
        u"contentType": u"image/jpeg"
    }, 
    u".jpg": {
         
        u"isText": False, 
        u"contentType": u"image/jpeg"
    }, 
    u".py": {
         
        u"isText": True, 
        u"contentType": u"text/plain"
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
    u".gtar": {
         
        u"isText": False, 
        u"contentType": u"application/x-gtar"
    }, 
    u".tif": {
         
        u"isText": False, 
        u"contentType": u"image/tiff"
    }, 
    u".hdf": {
         
        u"isText": False, 
        u"contentType": u"application/x-hdf"
    }, 
    u".nws": {
         
        u"isText": False, 
        u"contentType": u"message/rfc822"
    }, 
    u".tsv": {
        u"isText": True, 
        u"contentType": u"text/tab-separated-values"
    }, 
    u".xpdl": {
         
        u"isText": True, 
        u"contentType": u"application/xml"
    }, 
    u".src": {
         
        u"isText": False, 
        u"contentType": u"application/x-wais-source"
    }, 
    u".sh": {
         
        u"isText": True, 
        u"contentType": u"application/x-sh"
    }, 
    u".p7c": {
         
        u"isText": False, 
        u"contentType": u"application/pkcs7-mime"
    }, 
    u".ief": {
         
        u"isText": False, 
        u"contentType": u"image/ief"
    }, 
    u".so": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".xlb": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-excel"
    }, 
    u".pbm": {
         
        u"isText": False, 
        u"contentType": u"image/x-portable-bitmap"
    }, 
    u".texinfo": {
         
        u"isText": False, 
        u"contentType": u"application/x-texinfo"
    }, 
    u".xls": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-excel"
    }, 
    u".tex": {
         
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
    u".aiff": {
         
        u"isText": False, 
        u"contentType": u"audio/x-aiff"
    }, 
    u".aifc": {
         
        u"isText": False, 
        u"contentType": u"audio/x-aiff"
    }, 
    u".exe": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".sgm": {
         
        u"isText": False, 
        u"contentType": u"text/x-sgml"
    }, 
    u".xpm": {
         
        u"isText": False, 
        u"contentType": u"image/x-xpixmap"
    }, 
    u".mpeg": {
         
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".ms": {
         
        u"isText": False, 
        u"contentType": u"application/x-troff-ms"
    }, 
    u".rtx": {
         
        u"isText": True, 
        u"contentType": u"text/richtext"
    }, 
    u".ppt": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-powerpoint"
    }, 
    u".pps": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-powerpoint"
    }, 
    u".sgml": {
         
        u"isText": False, 
        u"contentType": u"text/x-sgml"
    }, 
    u".ppm": {
         
        u"isText": False, 
        u"contentType": u"image/x-portable-pixmap"
    }, 
    u".latex": {
         
        u"isText": True, 
        u"contentType": u"application/x-latex"
    }, 
    u".bat": {
         
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".mov": {
         
        u"isText": False, 
        u"contentType": u"video/quicktime"
    }, 
    u".ppa": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-powerpoint"
    }, 
    u".rgb": {
        u"isText": False, 
        u"contentType": u"image/x-rgb"
    }, 
    u".rdf": {
        u"isText": True, 
        u"contentType": u"application/rdf+xml"
    }, 
    u".xsl": {
         
        u"isText": True, 
        u"contentType": u"application/xml"
    }, 
    u".eml": {
         
        u"isText": False, 
        u"contentType": u"message/rfc822"
    }, 
    u".ai": {
         
        u"isText": False, 
        u"contentType": u"application/postscript"
    }, 
    u".nc": {
         
        u"isText": False, 
        u"contentType": u"application/x-netcdf"
    }, 
    u".sv4cpio": {
         
        u"isText": False, 
        u"contentType": u"application/x-sv4cpio"
    }, 
    u".bin": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".h": {
         
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".tcl": {
         
        u"isText": True, 
        u"contentType": u"application/x-tcl"
    }, 
    u".wiz": {
         
        u"isText": False, 
        u"contentType": u"application/msword"
    }, 
    u".o": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".a": {
         
        u"isText": False, 
        u"contentType": u"application/octet-stream"
    }, 
    u".c": {
         
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".wav": {
         
        u"isText": False, 
        u"contentType": u"audio/x-wav"
    }, 
    u".xbm": {
         
        u"isText": False, 
        u"contentType": u"image/x-xbitmap"
    }, 
    u".txt": {
         
        u"isText": True, 
        u"contentType": u"text/plain"
    }, 
    u".au": {
         
        u"isText": False, 
        u"contentType": u"audio/basic"
    }, 
    u".eps": {
         
        u"isText": False, 
        u"contentType": u"application/postscript"
    }, 
    u".t": {
         
        u"isText": True, 
        u"contentType": u"application/x-troff"
    }, 
    u".tiff": {
         
        u"isText": False, 
        u"contentType": u"image/tiff"
    }, 
    u".texi": {
         
        u"isText": True, 
        u"contentType": u"application/x-texinfo"
    }, 
    u".oda": {
         
        u"isText": False, 
        u"contentType": u"application/oda"
    }, 
    u".ustar": {
         
        u"isText": False, 
        u"contentType": u"application/x-ustar"
    }, 
    u".tr": {
         
        u"isText": False, 
        u"contentType": u"application/x-troff"
    }, 
    u".me": {
         
        u"isText": False, 
        u"contentType": u"application/x-troff-me"
    }, 
    u".sv4crc": {
         
        u"isText": False, 
        u"contentType": u"application/x-sv4crc"
    }, 
    u".qt": {
         
        u"isText": False, 
        u"contentType": u"video/quicktime"
    }, 
    u".mpa": {
         
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".mpg": {
         
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".mpe": {
         
        u"isText": False, 
        u"contentType": u"video/mpeg"
    }, 
    u".doc": {
         
        u"isText": False, 
        u"contentType": u"application/msword"
    }, 
    u".pgm": {
         
        u"isText": False, 
        u"contentType": u"image/x-portable-graymap"
    }, 
    u".pot": {
         
        u"isText": False, 
        u"contentType": u"application/vnd.ms-powerpoint"
    }, 
    u".mif": {
         
        u"isText": False, 
        u"contentType": u"application/x-mif"
    }, 
    u".roff": {
         
        u"isText": False, 
        u"contentType": u"application/x-troff"
    }, 
    u".htm": {
        u"isText": True, 
        u"contentType": u"text/html"
    }, 
    u".xhtml": {
        u"isText": True, 
        u"contentType": u"text/html"
    }, 
    u".man": {
         
        u"isText": False, 
        u"contentType": u"application/x-troff-man"
    }, 
    u".etx": {
         
        u"isText": False, 
        u"contentType": u"text/x-setext"
    }, 
    u".zip": {
         
        u"isText": False, 
        u"contentType": u"application/zip"
    }, 
    u".movie": {
         
        u"isText": False, 
        u"contentType": u"video/x-sgi-movie"
    }, 
    u".pyc": {
         
        u"isText": False, 
        u"contentType": u"application/x-python-code"
    }, 
    u".png": {
         
        u"isText": False, 
        u"contentType": u"image/png"
    }, 
    u".svg": {
         
        u"isText": False, 
        u"contentType": u"image/svg+xml"
    },
    u".pfx": {
         
        u"isText": False, 
        u"contentType": u"application/x-pkcs12"
    }, 
    u".mhtml": {
         
        u"isText": False, 
        u"contentType": u"message/rfc822"
    }, 
    u".tar": {
         
        u"isText": False, 
        u"contentType": u"application/x-tar"
    }, 
    u".pnm": {
         
        u"isText": False, 
        u"contentType": u"image/x-portable-anymap"
    }, 
    u".pyo": {
         
        u"isText": False, 
        u"contentType": u"application/x-python-code"
    }, 
    u".snd": {
         
        u"isText": False, 
        u"contentType": u"audio/basic"
    }, 
    u".cpio": {
         
        u"isText": False, 
        u"contentType": u"application/x-cpio"
    }, 
    u".swf": {
         
        u"isText": False, 
        u"contentType": u"application/x-shockwave-flash"
    }, 
    u".mp3": {
         
        u"isText": False, 
        u"contentType": u"audio/mpeg"
    }, 
    u".mp2": {
         
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
    u".pcasm": {
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
    u".beh": {
        
        u"isText": True,
        u"contentType": u"text/plain"
    },
    u".cara": {
        u"isText": True,
        u"contentType": u"text/plain"
    },
}

