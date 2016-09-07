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


def cutstr(s, h, t=None):
    res = s[s.find(h):]
    if(t):
        res = res[:s.rfind(t)]
    return res

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
                    re_fetch(params, post_date)
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

def re_fetch(params, post_date):
    e = None
    post_num, e = get_page(params['post']['root'], post_date)
    if(e):
        db(params['db'], "update post_record set status = '" + e + "', post_num =" + str(post_num) + " where post_date = '" + post_date + "';")
    else:
        db(params['db'], "update post_record set status = NULL, post_num =" + str(post_num) + " where post_date = '" + post_date + "';")


def parse(fn):
    import re
    zp = re.compile('[\u4e00-\u9fa5]+')
    f = open(fn)
    ls = f.readlines()
    f.close()
    csl = []
    title = ls[0].strip()
    category = ls[1].strip()
    post_time = cutstr(ls[2], '@')[1:].strip()
    length = 0
    ls = ls[3:] + ls[:1]
    for l in ls:
        l = l.strip()
        length = length + len(l)
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
    return title, category, post_time, length, csd

def parse_txt(params, p):
    for root,dirs,files in os.walk(p):
        for fn in files:
            post_date = root[1:]
            if(fn.endswith('.txt')):
                post_order = fn[:-4]
                title, category, post_time, length, csd = parse(root + os.sep + fn)
                print(title, category, post_time, root, length, fn[:-4], csd)
                posts = db(params['db'], "select * from post where post_date ='" + post_date + "' and post_order = " + str(post_order) + ";" )
                if(0 == len(posts)):
                    db(params['db'], "insert into post (title, category, length, post_date, post_time, post_order) values ('" +\
                       title + "','" + category + "'," + str(length) + ",'" + post_date + "','" + post_time + "'," + str(post_order)+");")
                for cs in csd:
                    post_id = db(params['db'], "select id from post where post_date = '" + post_date + "' and post_order = " + post_order + ";")[0][0]
                    word = db(params['db'], "select id from word where text = '" + cs + "';")
                    if(0 == len(word)):
                        db(params['db'], "insert into word (text) values ('" + cs + "');")
                        word = db(params['db'], "select id from word where text = '" + cs + "';")
                    word_id = word[0][0]
                    xref = db(params['db'], 'select word_count from word_post where word_id = ' + str(word_id) + ' and post_id = ' + str(post_id) +';')
                    if(0 == len(xref)):
                        db(params['db'], 'insert into word_post (word_id, post_id, word_count) values (' + str(word_id) + ',' + str(post_id) + ',0);')
                    print(post_id, word_id)
                    db(params['db'], 'update word_post set word_count = word_count+' + str(csd[cs]) + ' where word_id = ' + str(word_id) + ' and post_id = ' + str(post_id) +';')

def static_post(params):
    posts = db(params['db'], "select id, post_date, post_num, status from wp.post_record where post_num >0 or status not like '%404%'")
    if(0 == len(posts)):
        time.sleep(60)
    else:
        for ps in posts:
            post_id = ps[0]
            post_date = ps[1]
            post_num = ps[2]
            status = ps[3]
            if(status):
                re_fetch(params, post_date)
            else:
                pass




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
#    t_fetch = threading.Thread(target=fetch, args=(params,))
#    ts.append(t_fetch)
#    t_gen_txt = threading.Thread(target=gen_txt, args=(params,))
#    ts.append(t_gen_txt)
    t_parse_txt = threading.Thread(target=parse_txt, args=(params, '.',))
    ts.append(t_parse_txt)
#    t_static_post = threading.Thread(target=static_post, args=(params,))
#    ts.append(t_static_post)
#    t_static_word = threading.Thread(target=static_word, args=())
#    ts.append(t_static_word)
    for t in ts:
#        t.setDaemon(True)
        t.start()
