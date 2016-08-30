"""
CREATE TABLE `post_record` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `post_date` varchar(45) NOT NULL,
  `post_num` int(11) DEFAULT '-1',
  `last_updated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

"""

import threading, time, datetime, os
from html.parser import HTMLParser

class WPHTMLParser(HTMLParser):
    def __init__(self, fp):
        HTMLParser.__init__(self)
        self.tags = []
        self.outs = []
        self.fp = fp
        self.pn = 0
        self.data = ''
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self.tags.append(tag)
        out = False
        if('h3' == tag):
            out = (('class', 'storytitle') in attrs)
            if(out):
                self.pn = self.pn + 1
                f = open(self.fp + '/' + str(self.pn) + '.txt', 'w')
                f.close()
        if('a' == tag):
            out = (('rel', 'bookmark') in attrs) or (('rel', 'category tag') in attrs)
        if('div' == tag):
            out = (('class', 'storycontent') in attrs) or (('class', 'meta') in attrs) or (('class', 'bvMsg') in attrs) or (0 == len(attrs))
        if('p' == tag):
            out = self.outs[-1]
        self.outs.append(out)

    def out2file(self):
        if(0 < self.pn):
            f = open(self.fp + '/' + str(self.pn) + '.txt', 'a')
            if(0 < len(self.data)):
                if((0 < len(self.outs)) and (self.outs[-1])):
                    if(self.tags[-1] in ('a', 'div', 'p')):
                        f.write(self.data + '\n')
            f.close()

    def handle_endtag(self, tag):
        if((tag == self.tags[-1]) and (0 < len(self.outs))):
            if(self.outs[-1]):
                self.out2file()
            self.tags.pop()
            self.outs.pop()


    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if(self.outs[-1])and (tag in ('br')):
            self.out2file()

    def handle_data(self, data):
        self.data = data.strip()


def cutstr(s, h, t):
    return s[s.find(h):s.rfind(t)]

def gen_datestr(dtstr, delta=0, fmt='%Y/%m/%d'):
    nt = time.strptime(dtstr, fmt)
    return (datetime.date(nt[0],nt[1],nt[2])+datetime.timedelta(delta)).strftime(fmt)

def get_page(root, datestr):
    import urllib.request, urllib.error
    post_num = -1
    e = None
    try:
        page = urllib.request.urlopen(root+gen_datestr(datestr), timeout=60).read().decode('utf8')
        fn = datestr+'/page.html'
        if(not os.path.exists(datestr)):
            os.makedirs(datestr)
        f = open(fn, 'w', encoding='utf8')
        f.write(page)
        f.close()
    except Exception as err:
        e = str(err)
        if(urllib.error.HTTPError == type(err))and(404 == err.code):
            post_num = 0
    return post_num, e

def fetch(params):
    start_date = params['post']['start_date']
    delta = 0
    while(True):
        datestr = gen_datestr(start_date, delta)
        if(datetime.datetime.now().strftime('%Y/%m/%d') >= datestr):
            post_num, e = get_page(params['post']['root'], datestr)
            if(e):
                db(params['db'], "insert into post_record (post_date, post_num, status) values ('" + datestr + "', " + str(post_num) + ", '" + e + "');")
            else:
                db(params['db'], "insert into post_record (post_date) values ('" + datestr + "');")
            delta = delta + 1
        time.sleep(5)
    

def gen_txt(params):
# https://docs.python.org/3/library/html.parser.html
    while(True):
        posts = db(params['db'], 'select post_date, status from post_record where post_num = -1')
        if(0 == len(posts)):
            time.sleep(60)
        else:
            for ps in posts:
                post_date = ps[0]
                status = ps[1]
                if(status):
                    post_num, e = get_page(params['post']['root'], post_date)
                    if(e):
                        db(params['db'], "update post_record set status = '" + e + "', post_num =" + str(post_num) + " where post_date = '" + post_date + "';")
                    else:
                        db(params['db'], "update post_record set status = NULL, post_num =" + str(post_num) + " where post_date = '" + post_date + "';")
                else:
                    f = open(post_date+'/page.html', 'r')
                    page = f.read()
                    f.close()
                    wphp = WPHTMLParser(post_date)
                    wphp.feed(cutstr(page, params['page']['head'], params['page']['tail']))
                    wphp.close()
                    db(params['db'], "update post_record set post_num = " + str(len(page.split(params['page']['title']))-1) + " where post_date = '" + post_date + "';")
                time.sleep(5)

def ins(d, s):
    if(s in d):
        d[s] = d[s] + 1
    else:
        d[s] = 1

def parse(fn):
    import re
    zp = re.compile('[\u4e00-\u9fa5]+')
    f = open(fn)
    ls = f.readlines()
    f.close()
    csl = []
    for l in ls:
        l = l.strip()
        while(0 < len(l)):
            sub = ''
            m = zp.search(l)
            if(m):
                sub = m.group(0)
                csl.append(sub)
                l = l.replace(sub, '')
            else:
                l = l[1:]
    csd = {}
    for cs in csl:
        for i in range(len(cs)):
            j = 0
            while(j < len(cs) - i):
                ins(csd, cs[j:j + i + 1])
                j = j + 1
    for cs in csd:
        print(cs, csd[cs])

def parse_txt(p):
    for root,dirs,files in os.walk(p):
        for fn in files:
            if(fn.endswith('.txt')):
                parse(root + os.sep + fn)

def db(dbp, sql):
    print(sql)
    import mysql.connector
    from mysql.connector import connection
    sql = sql.strip()
    res = None
    cnx = connection.MySQLConnection(user=dbp['dbuser'], password=dbp['dbpassword'],host=dbp['dbhost'],database=dbp['database'])
    c = cnx.cursor()
    c.execute(sql)
    if(sql.startswith('select')):
        res = c.fetchall()
    cnx.commit()
    c.close()
    return res

def init():
    start_date = '2005/08/28'
    params = {'post':{'start_date': '',\
                      'root': 'https://gcd0318.wordpress.com/',\
                    },\
              'page':{'head': '<!-- end header -->',\
                      'tail':'<!-- begin footer -->',\
                      'title': '<h3 class="storytitle">',\
                      'meta': '<div class="meta">',\
                      'content':'<div class="storycontent">',\
                    },\
              'db':{'dbhost':'192.168.1.18',\
                    'dbuser':'wp',\
                    'dbpassword':'wp',\
#              'db':{'dbhost':'localhost',\
#                    'dbuser':'root',\
#                    'dbpassword':'root',\
                    'database':'wp',\
                },\
              }
    sd = db(params['db'], 'select post_date from post_record order by post_date desc limit 1')
    if(0 < len(sd)):
        params['post']['start_date'] = sd[0][0]
        db(params['db'], "delete from post_record where post_date = '" + params['post']['start_date'] + "';")
    else:
        params['post']['start_date'] = start_date
    return params


if('__main__' == __name__):
    params = init()

    ts = []
#    t1 = threading.Thread(target=fetch, args=(params,))
#    ts.append(t1)
#    t2 = threading.Thread(target=gen_txt, args=(params,))
#    ts.append(t2)
    t3 = threading.Thread(target=parse_txt, args=('.',))
    ts.append(t3)
#    t4 = threading.Thread(target=static, args=())
#    ts.append(t4)
    for t in ts:
#        t.setDaemon(True)
        t.start()
