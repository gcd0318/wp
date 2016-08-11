"""
'post', 'CREATE TABLE `post` (\n  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,\n  `post_date` varchar(45) NOT NULL,\n  `post_num` int(11) NOT NULL DEFAULT \'0\',\n  `last_updated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,\n  PRIMARY KEY (`id`),\n  UNIQUE KEY `idid_UNIQUE` (`id`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8'
"""


import threading, time, datetime, os
import urllib.request
import mysql.connector
from mysql.connector import connection


def cutstr(s, h, t):
    return s[s.find(s):s.rfind(t)]

def gen_datestr(dtstr, delta=0, fmt='%Y/%m/%d'):
    nt = time.strptime(dtstr, fmt)
    return (datetime.date(nt[0],nt[1],nt[2])+datetime.timedelta(delta)).strftime(fmt)


def fetch(params):
    root = params['root']
    start_date = params['start_date']
    delta = 0
    while(True):
        try:
            datestr = gen_datestr(start_date, delta)
            if(not os.path.exists(datestr)):
                os.makedirs(datestr)
            page = urllib.request.urlopen(root+gen_datestr(datestr)).read().decode('utf8')
            fn = datestr+'/page.html'
            f = open(fn, 'w', encoding='utf8')
            print(page, file=f)
            f.close()
            sql = "insert into wp.post (post_date, post_num) values('"+datestr+"', 0)"
            print(sql)
            delta = delta + 1
        except Exception as err:
            print(err)
        finally:
            time.sleep(5)
    

def parse_txt(txt):
    tmp = txt

def db(cnx, sql):
    c = cnx.cursor()
    c.execute(sql)
    conn.commit()
    c.close()

def init():
    start_date = '2005/08/28'
    params = {'start_date': '',\
              'root': 'https://gcd0318.wordpress.com/',\
              'head': '<!-- end header -->',\
              'tail':'<!-- begin footer -->',\
#              'head': '<h3 class="storytitle">',\
#              'tail':'<h3 class="sd-title">Rate this:</h3>',\
              'db':{'dbhost':'localhost',\
                    'dbuser':'root',\
                    'dbpassword':'root',\
                },\
              }
    cnx = connection.MySQLConnection(user=params['db']['dbuser'], password=params['db']['dbpassword'],host=params['db']['dbhost'])
    c = cnx.cursor()
    c.execute('select post_date from wp.post order by post_date desc limit 1')
    sd = c.fetchall()
    if(0 < len(sd)):
        params['start_date'] = sd[0]
    else:
        params['start_date'] = start_date
    c.close()
    cnx.close()
    return params


if('__main__' == __name__):
    params = init()
    print(params)
    start_date = params['start_date']
    root = params['root']
    db = params['db']
    fetch(params)


"""
    ts = []
    t1 = threading.Thread(target=fetch, args=())
    ts.append(t1)
    t2 = threading.Thread(target=gen_txt, args=())
    ts.append(t2)
    t3 = threading.Thread(target=parse, args=())
    ts.append(t3)
    t4 = threading.Thread(target=static, args=())
    ts.append(t4)
    for t in ts:
#        t.setDaemon(True)
        t.start()
"""
