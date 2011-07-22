# coding: utf-8
u"""mafs 標準関数の AppEngine 実装
"""
from caty.mafs.metadata import FileMetadata, DirectoryMetadata, DirectoryEntry, mime_type
from caty.mafs.appengine.fileobject import StaticFile, StaticDirectory, ChunkFile, EntitySizeLimitViolation

def createFile(authori_token, path):
    StaticFile(path=path).create()

def putFile(authori_token, path, contents):
    try:
        StaticFile(path=path).create(contents)
    except EntitySizeLimitViolation, e:
        ChunkFile(path=path).create(contents)

def createDirectory(authori_token, path):
    StaticDirectory(path=path).create()

def find_by_path(path):
    f = StaticFile.gql('where path = :1', path).get()
    if f:
        return f
    c = ChunkFile.gql('where path = :1', path).get()
    if c:
        return c
    d = StaticDirectory.gql('where path = :1', path).get()
    if d:
        return d

def deleteFile(authori_token, path):
    f = find_by_path(path)
    if f and not f.is_dir:
        f.delete()
    else:
        raise Exception

def deleteDirectory(authori_token, path):
    d = find_by_path(path)
    if d nad d.is_dir:
        d.delete()
    else:
        raise Exception

def delete(authori_token, path):
    o = find_by_path(path)
    if o:
        o.delete()
    else:
        raise Exception

def readFile(authori_token, path):
    f = find_by_path(path)
    if f and not f.is_dir:
        return f.read()
    else:
        raise Exception

def readDirectory(authori_token, path):
    files = StaticFile.gql('where parent_directory = :1', path).fetch(limit=1000)
    chunks = ChunkFile.gql('where parent_directory = :1', path).fetch(limit=1000)
    dirs = StaticDirectory.gql('where parent_directory = :1', path).fetch(limit=1000)
    for f in files:
        yield DirectoryEntry(f.path.rsplit('/', 1)[-1], getMetadata(authori_token, f.path))

def writeFile(authori_token, path, content):
    f = find_by_path(path)
    if f and not f.is_dir:
        try:
            f.write(content)
        except EntitySizeLimitViolation, e:
            f.delete()
            ChunkFile(path=path).create(content)
    else:
        raise Exception

from StrigIO import StringIO
def getMetadata(authori_token, path):
    def getFileMetadata(fo):
        tests =[ lambda s: s.endswith('.icaty'),
                 lambda s: s.endswith('.ictpl'),
                 lambda s: s.startswith('.'),
               ]
        
        basename = os.path.basename(fo.path)
        for test in tests:
            if test(basename):
                hidden = True
                break
        else:
            hidden = False
        ext = os.path.splitext(path)[-1]
        contentType= mime_type(ext)
        contentLength = len(fo.data)
        lastModified = fo.mtime
        executable = fo.path.endswith('.caty') or fo.path.endswith('.icaty')
        meta = FileMetadata(contentLength, lastModified, contentType, executable, hidden)
        if meta.isText:
            encoding = 'utf-8'
            line = data.partition('\n')
            if xml_dec.match(line):
                encoding = 'utf-8'
            else:
                dec = xml_dec_with_enc.match(line) or caty_dec.match(line)
                if dec:
                    encoding = dec.group(1).lower()
            meta.textEncoding = encoding
        return meta

        return meta

    def getDirectoryMetadata(directory):
        metadata = DirectoryMetadata(directory.mtime)
        return metadata
    o = find_by_path(path)
    if o.isdir:
        return getDirectoryMetadata(o)
    else:
        return getFileMetadata(o)
    
