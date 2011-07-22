# -*- coding: utf-8 -*-
# gdjxlib.py

from xml.sax.xmlreader import handler, XMLReader, AttributesImpl

DEBUG = False

JSONStringType = unicode
JSONObjectType = dict
JSONArrayType = list

def make_parser():
    return GdjxXMLReader()

def parse(source, handler, errorHandler=handler.ErrorHandler()):
    parser = make_parser()
    parser.setContentHandler(handler)
    parser.setErrorHandler(errorHandler)
    parser.parse(source)

class GdjxXMLReader(XMLReader):
    u"""XMLReader for GDJX (Google GData style JSON-encoded XML)
    http://code.google.com/intl/ja/apis/gdata/docs/json.html に従うJSONデータから
    SAXイベントを発生させるXMLReader実装。次のコールバックにだけ対応：
    
    * startDocument()
    * endDocument()
    * startElement(tagName, attributes)
    * endElement(tagName)
    * characters(text) """

    def fatal(self, message):
        self._err_handler.fatalError(SaxParseException(message))

    def parse(self, source):
        if not isinstance(source, JSONObjectType):
            fatal("bad source")
            return

        docElms = []
        for k, v in source.iteritems():
            if isinstance(v, JSONObjectType):
                docElms.append((k, v))
        if len(docElms) == 0:
            self.fatal("document elemet not exist")
        if len(docElms) != 1:
            self.fatal("document elemet is not unique")

        self._cont_handler.startDocument()
        tagName = docElms[0][0]
        jsonObj = docElms[0][1]
        self.parseElement(tagName, jsonObj)
        self._cont_handler.endDocument()

    def parseElement(self, tagName, jsonObj):
        tagName = tagName.replace(u'$', u':')
        if DEBUG: print "tagName=" + tagName + "\ntype of jsonObj=" + unicode(type(jsonObj))
        attrs = {}
        text = None
        elements = []
        elementSeqs = [] 
        for k, v in jsonObj.iteritems():
            if k == u'$t':
                text = v
            elif isinstance(v, JSONStringType):
                attrName = k.replace(u'$', u':')
                attrs[attrName] = v
            elif isinstance(v, JSONObjectType):
                elements.append((k, v))
            elif isinstance(v, JSONArrayType):
                elementSeqs.append((k, v))
            else:
                self.fatal("bad property")
                return

        self._cont_handler.startElement(tagName, AttributesImpl(attrs))
        if text:
            if not isinstance(text, JSONStringType):
                self.fatal("text is not unicode (JSON string)")
                return
            else:
                self._cont_handler.characters(text)
        # mixed contentのチェック
        if text and (elements or elementSeqs):
            self.fatal("mixed content is not allowed")
            return

        for n, obj in elements:
            self.parseElement(n, obj)
        for n, lis in elementSeqs:
            for obj in lis:
                self.parseElement(n, obj)

        self._cont_handler.endElement(tagName)


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

    import petitxml
    
    generator = petitxml.StringXMLGenerator()
    parse(gdata, generator, generator)
    print generator.get_result()

