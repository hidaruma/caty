from caty.command import *
import re
ent_headline = re.compile(r'(^\*[0-9]+\*)')
ent_tags = re.compile(r'(^\[[^\]]+?\])')

class EntriesFromDay(Command):
    def execute(self, day):
        r = []
        for ent in process_day(day):
            if ent is None:
                continue
            ent[u'dayTitle'] = day['title']
            ent[u'dayDate'] = day['date']
            r.append(ent)
        return r

def process_day(day):
    lines = iter(day[u'body'].strip().split('\n'))
    buff = []
    for line in lines:
        if ent_headline.match(line):
            if buff:
                yield process_ent(buff)
                buff = []
        buff.append(line)
    if buff:
        yield process_ent(buff)

def process_ent(buff):
    ent = {u'tags': []}
    headline = buff.pop(0)
    if not ent_headline.match(headline): #leading text
        return None
    _, ts, rest = ent_headline.split(headline)
    ent[u'id'] = int(ts.strip('*'))
    ent[u'created'] = ent[u'id']
    while ent_tags.match(rest):
        _, tag, rest = ent_tags.split(rest)
        ent[u'tags'].append(tag[1:-1])
    ent[u'title'] = rest
    ent[u'content'] = u'\n'.join(buff)
    return ent


