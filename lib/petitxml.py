# -*- coding: utf-8 -*-
# petitxml.py

from xml.sax.handler import ContentHandler, ErrorHandler
from xml.sax.saxutils import quoteattr, escape

class StringXMLGenerator(ContentHandler, ErrorHandler):
    u"""SAX Conntent/Error Handler for generating XML Unicode string
    SAXイベントをハンドルして、XMLデータをUnicode文字列として書き出す。"""
    
    def __init__(self):
        self.buffer = []
        self.result = None

    def _write(self, text):
        self.buffer.append(text)
        

    def startDocument(self):
        self._write(u'<?xml version="1.0" encoding="%s"?>\n' %
                    u"utf-8")

    def endDocument(self):
        self.result = ''.join(self.buffer)
        
    def startElement(self, name, attrs):
        self._write(u'<' + name)
        for (name, value) in attrs.items():
            self._write(u' %s=%s' % (name, quoteattr(value)))
        self._write(u'\n>')

    def endElement(self, name):
        self._write(u'</%s\n>' % name)

    def characters(self, content):
        self._write(escape(content))

    def processingInstruction(self, target, data):
        self._write(u'<?%s %s?>' % (target, data))

    def get_result(self):
        return self.result


    def error(self, exception):
        "Handle a recoverable error."
        self.buffer = []
        raise exception

    def fatalError(self, exception):
        "Handle a non-recoverable error."
        self.buffer = []
        raise exception

    def warning(self, exception):
        "Handle a warning."
        print exception


if __name__ == "__main__":
    
    # see http://code.google.com/intl/ja/apis/gdata/docs/json.html
    gdata = {
        u"version": u"1.0",
        u"encoding": u"UTF-8",
        u"feed": {
            u"xmlns": u"http://www.w3.org/2005/Atom",
            u"xmlns$openSearch": u"http://a9.com/-/spec/opensearchrss/1.0/",
            u"xmlns$gd": u"http://schemas.google.com/g/2005",
            u"xmlns$gCal": u"http://schemas.google.com/gCal/2005",
            u"id": {u"$t": u"..."},
            u"updated": {u"$t": u"2006-11-12T21:25:30.000Z"},
            u"title": {
                u"type": u"text",
                u"$t": u"Google Developer Events"
                },
            u"subtitle": {
                u"type": u"text",
                u"$t": u"""
       The calendar contains information about upcoming developer 
       conferences at which Google will be speaking, along with other 
       developer-related events."""
                },
            u"link": [{
                    u"rel": u"...",
                    u"type": u"application/atom+xml",
                    u"href": u"..."
                    },{
                    u"rel": u"self",
                    u"type": u"application/atom+xml",
                    u"href": u"..."
                    }],
            u"author": [{
                    u"name": {u"$t": u"Google Developer Calendar"},
                    u"email": {u"$t": u"developer-calendar@google.com"}
                    }],
            u"generator":{
                u"version": u"1.0",
                u"uri": u"http://www.google.com/calendar",
                u"$t": u"Google Calendar"
                },
            u"openSearch$startIndex": {u"$t": u"1"},

            u"openSearch$itemsPerPage": {u"$t": u"25"},
            u"gCal$timezone": {u"value": u"America/Los_Angeles"},

            u"entry": [{
                    u"id": {u"$t": u"..."},
                    u"published": {u"$t": u"2006-11-12T21:25:30.000Z"},
                    u"updated": {u"$t": u"2006-11-12T21:25:30.000Z"},
                    u"category": [{
                            u"scheme": u"...",
                            u"term": u"..."
                            }],
                    u"title":{
                        u"type": u"text",
                        u"$t": u"WebmasterWorld PubCon 2006: Google Developer Tools in General"
                        },
                    u"content": {
                        u"type": u"text",
                        u"$t": u"""
          Google is sponsoring at <a href="http://www.pubcon.com/">WebmasterWorld PubCon 2006</a>.
          Come and visit us at the booth or join us for an evening demo
          reception where we will be talking "5 ways to enhance your website
          with Google Code".
          After all,
          it is Vegas, baby! See you soon."""
                        },
                    u"link": [{
                            u"rel": u"alternate",
                            u"type": u"text/html",
                            u"href": u"...",
                            u"title": u"alternate"
                            },{
                            u"rel": u"self",
                            u"type": u"application/atom+xml",
                            u"href": u"..."
                            }],
                    u"author": [{
                            u"name": {u"$t": u"Google Developer Calendar"},
                            u"email": {u"$t": u"developer-calendar@google.com"}
                            }],
                    u"gd$transparency": {u"value": u"http://schemas.google.com/g/2005#event.opaque"},
                    u"gd$eventStatus": {u"value": u"http://schemas.google.com/g/2005#event.confirmed"},
                    u"gd$comments": {u"gd$feedLink": {u"href": u"..."}},
                    u"gCal$sendEventNotifications": {u"value": u"true"},
                    u"gd$when": [{
                            u"startTime": u"2006-11-15",
                            u"endTime": u"2006-11-17",
                            u"gd$reminder": [{u"minutes": u"10"}]
                            }],
                    u"gd$where": [{u"valueString": u"3150 Paradise Road,Las Vegas,NV 89109"}]}
                       ]
            }
    }

    import gdjxlib

    generator = StringXMLGenerator()
    gdjxlib.parse(gdata, generator, generator)
    print generator.get_result()

