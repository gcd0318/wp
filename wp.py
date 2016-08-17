"""
CREATE TABLE `post_record` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `post_date` varchar(45) NOT NULL,
  `post_num` int(11) NOT NULL DEFAULT '0',
  `last_updated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

"""

import threading, time, datetime, os
from html.parser import HTMLParser

class WPHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        print("Encountered a start tag:", tag)
        print("Encountered a start attrs:", attrs)

    def handle_endtag(self, tag):
        print("Encountered an end tag :", tag)

    def handle_data(self, data):
        print("Encountered some data  :", data)

def cutstr(s, h, t):
    return s[s.find(h):s.rfind(t)]

def gen_datestr(dtstr, delta=0, fmt='%Y/%m/%d'):
    nt = time.strptime(dtstr, fmt)
    return (datetime.date(nt[0],nt[1],nt[2])+datetime.timedelta(delta)).strftime(fmt)


def fetch(params):
    import urllib.request, urllib.error
    root = params['root']
    start_date = params['start_date']
    delta = 0
    while(True):
        sqls = []
        post_num = -1
        datestr = gen_datestr(start_date, delta)
        try:
            sqls.append("insert into post_record (post_date, post_num) values('"+datestr+"', " + str(post_num) + ")")
            page = urllib.request.urlopen(root+gen_datestr(datestr)).read().decode('utf8')
            fn = datestr+'/page.html'
            if(not os.path.exists(datestr)):
                os.makedirs(datestr)
            f = open(fn, 'w', encoding='utf8')
            f.write(page)
            f.close()
#            sqls.append("insert into post_record (post_date, post_num) values('"+datestr+"', " + str(post_num) + ")")
        except Exception as err:
            e = str(err)
            if(urllib.error.HTTPError == type(err))and(404 == err.code):
                post_num = 0
                e = '404'
            sqls.append("update post_record set status = '" + e + "', post_num =" + str(post_num) + " where post_date = '" + datestr + "';")
        finally:
            delta = delta + 1
            for sql in sqls:
                print(sql)
                db(params, sql)
            time.sleep(5)
    

def gen_txt(params):
# https://docs.python.org/3/library/html.parser.html
    hp = WPHTMLParser()
    while(True):
        posts = db(params, 'select post_date from post_record where post_num = -1')
        for ps in posts:
            post_date = ps[0]
            f = open(post_date+'/page.html', 'r')
#            ls = f.readlines()
            page = f.read()
            f.close()
            tmp = cutstr(page, params['head'], params['tail'])
            hp.feed(tmp)
#            print(page)
#            print(hp.handle_starttag('a',))
            print('=============================')
            hp.close()


def parse_txt(txt):
    tmp = txt

def db(params, sql):
    import mysql.connector
    from mysql.connector import connection
    sql = sql.strip()
    res = None
    cnx = connection.MySQLConnection(user=params['db']['dbuser'], password=params['db']['dbpassword'],host=params['db']['dbhost'],database=params['db']['database'])
    c = cnx.cursor()
    c.execute(sql)
    if(sql.startswith('select')):
        res = c.fetchall()
    cnx.commit()
    c.close()
    return res

def init():
    start_date = '2005/08/28'
    params = {'start_date': '',\
              'root': 'https://gcd0318.wordpress.com/',\
              'head': '<!-- end header -->',\
              'tail':'<!-- begin footer -->',\
              'title': '<h3 class="storytitle">',\
              'meta': '<div class="meta">',\
              'content':'<div class="storycontent">',\
              'db':{'dbhost':'192.168.1.18',\
                    'dbuser':'wp',\
                    'dbpassword':'wp',\
#              'db':{'dbhost':'localhost',\
#                    'dbuser':'root',\
#                    'dbpassword':'root',\
                    'database':'wp',\
                },\
              }
    sd = db(params, 'select post_date from post_record order by post_date desc limit 1')
    if(0 < len(sd)):
        params['start_date'] = sd[0][0]
    else:
        params['start_date'] = start_date
    return params


if('__main__' == __name__):
    params = init()

    ts = []
#    t1 = threading.Thread(target=fetch, args=(params,))
#    ts.append(t1)
    t2 = threading.Thread(target=gen_txt, args=(params,))
    ts.append(t2)
#    t3 = threading.Thread(target=parse, args=())
#    ts.append(t3)
#    t4 = threading.Thread(target=static, args=())
#    ts.append(t4)
    for t in ts:
#        t.setDaemon(True)
        t.start()
