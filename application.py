"""
Concept:
This service sends database updates to the connected clients.
implemented as a socketio server based on Tornado

"""
import traceback

import json
import datetime
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

from dbpoller import DBPoller



# column definitions per table
COLUMNPERTABLE = {
    'messages': "msg_id,bus_id,user_id,nameFrom,emailFrom,emailTo,emailCC,emailBCC,subject,body,status,opened,flag,date_sent".split(','),
    'groups': "group_id,bus_id,user_id,title,description,listing_date,slug,active".split(','),
    'users': "user_id,client_id,bus_id,title,fname,sname,gender,email,tel,cell,dob,region,avatar,last_login,active,status,online,session_id".split(','),
    'posts': "post_id,bus_id,user_id,title,heading,post_body,listing_date,feature_img,metaD,metaT,slug,tags,active,comments,broadcast,status".split(','),
    'post_comments': "post_comment_id,post_id,bus_id,user_id,comment_body".split(','),
    'events': "event_id,bus_id,user_id,board_id,type,title,description,startdate,enddate,starttime,endtime,allday,url,flag,status".split(',')
}


class Account:
    def __init__(self, userid=None, busid=None, email=None):
        self.userid = userid
        self.busid = busid
        self.email = email


class WSHandler(tornado.websocket.WebSocketHandler):
    clients = {}
    
    def check_origin(self, origin):
        return True
    
    
    def open(self):
        print 'new connection'
        WSHandler.clients[self] = Account()

    def on_message(self, message):
        #print 'message received %s' % message
        try: message = json.loads(message)
        except: 
            self.write_message('{"status": "error json"}')
            return
        
        if message['op'] == 'auth':
            # fields: userid, busid
            # TODO check some token
            try:
                
                WSHandler.clients[self].userid = int(message['userid'])
                WSHandler.clients[self].busid  = int(message['busid'])
                WSHandler.clients[self].email  = message['email']
            except:
                print 'auth error', message
                self.write_message('{"status": "error validation"}')
                return
            self.write_message('{"op": "auth", "status": "OK"}')
        
        if message['op'] == 'sendmessage':
            # fields: subject, body, to
            try:
                subject, body, to = message['subject'], message['body'], message['to']
                to = to.split(',')
            except:
                self.write_message('{"op": "sendmessage", "status": "error validation"}')
                return
            
            account = WSHandler.clients[self]
            if account.userid is None:
                self.write_message('{"op": "sendmessage", "status": "error unauthenticated"}')
                return
            
            # TODO replace groups by their members
            To = []
            for e in to:
                if not e.endswith('@business.group'):
                    To.append(e)
                    continue
                
                # replce group by its member emails
                gid = e[:-15]
                print 'replacing group %s by its members' %gid
                data = DBPoller.fetchdata("SELECT u.email FROM intranet.users u JOIN intranet.group_users g on (u.user_id = g.user_id) WHERE g.group_id='%s'" %gid)
                
                To += [r[0] for r in data]
                
            to = To
            
            # get user ids for all recipients
            data = DBPoller.fetchdata("SELECT email, user_id FROM intranet.users WHERE email IN ('%s')" %("','".join(to)))
            if not len(data) == len(to):
                self.write_message('{"op": "sendmessage", "status": "error unknown-recipient(s)"}')
                return
                
            for email, user_id in data:
                #print 'inserting into intranet.messages', (account.busid, int(user_id), subject, body, account.email, account.email)
                DBPoller.fetchdata("INSERT INTO intranet.messages(bus_id, user_id, subject, body, nameFrom, emailFrom, emailCC, emailBCC, emailTo, status) VALUES (%s, %s, %s, %s, %s, %s, '', '', %s, 'inbox')", (account.busid, int(user_id), subject, body, account.email, account.email, email) )
            self.write_message('{"status": "OK", "op": "sendmessage"}')
            

        if message['op'] == 'sendpostcomment':
            # fields: post_id, body
            try:
                post_id, body = message['post_id'], message['body']
            except:
                self.write_message('{"op": "sendpostcomment", "status": "error validation"}')
                return
            
            account = WSHandler.clients[self]
            if account.userid is None:
                self.write_message('{"op": "sendpostcomment", "status": "error unauthenticated"}')
                return
            
            # insert the comment
            DBPoller.fetchdata("INSERT INTO intranet.post_comments (post_id,user_id,bus_id,comment_body) VALUES (%s, %s, %s, %s)"
                , (post_id, account.userid, account.busid, body) )
            
            self.write_message('{"status": "OK", "op": "sendpostcomment"}')
            

        if message['op'] == 'markopened':
            # fields: table, ids
            try:
                table, ids = message['table'], message['ids']
                assert(table in ('messages', 'posts'))
                ids = [str(n) for n in ids]
            except:
                self.write_message('{"op": "markopened", "status": "error validation"}')
                return
            
            account = WSHandler.clients[self]
            if account.userid is None:
                self.write_message('{"op": "sendpostcomment", "status": "error unauthenticated"}')
                return
            
            if table == 'messages':
                DBPoller.fetchdata("UPDATE intranet.messages SET opened='Y' WHERE msg_id IN (%s) AND (user_id=%d OR emailFrom='%s')" %(",".join(ids), account.userid, account.email))
                
            if table == 'posts':
                DBPoller.fetchdata("UPDATE intranet.post_user_opened SET opened='Y' WHERE post_id IN (%s) AND user_id=%d" %(",".join(ids), account.userid))
            
            self.write_message('{"status": "OK", "op": "markopened", "table": "%s"}' %(table) )


        if message['op'] == 'sync':
            # fields: table, cachedids
            try:
                table, cachedids = message['table'], message['cachedids']
            except:
                self.write_message('{"status": "error validation"}')
                return
            
            account = WSHandler.clients[self]
            if account.userid is None:
                self.write_message('{"status": "error unauthenticated"}')
                return
            
            
            try:
                query = 'SELECT %s FROM intranet.%s WHERE bus_id=%d ' \
                    %(",".join(COLUMNPERTABLE[table]), table, account.busid)
                
                if table in ('messages'):
                    query += 'AND (user_id=%d OR emailFrom="%s")' %(account.userid, account.email)
                
                #print query
                data = DBPoller.fetchdata(query)
                # remove sensivitve data
                #if table =='users': data = [r[0:-3]+('', r[-2], '') for r in data]
                #if table =='posts': data = [r[0:-2]+('', r[-1]) for r in data]
                
                # augment tables
                if table == 'events':
                    # grab board name
                    print 'SELECT board_id, board FROM event_boardrooms WHERE board_id in (%s)' %(','.join([str(rec[3]) for rec in data]) )
                    boards = DBPoller.fetchdata('SELECT board_id, boardroom FROM intranet.event_boardrooms WHERE board_id in (%s)' %(','.join(set([str(rec[3]) for rec in data])) ) )
                    boards = dict(boards)
                    print 'boards', boards
                    data_ = []
                    for rec in data:
                        rec = list(rec)
                        try: rec[3] = boards[rec[3]]
                        except: pass
                        data_.append(tuple(rec))
                    data = data_
            except:
                print traceback.format_exc()
                self.write_message('{"status": "error db"}')
                return
            
            # convert problematic types for json into strings
            def convtojsontype(values):
                ret = []
                for v in values:
                    
                    if type(v) in (datetime.datetime, datetime.date): ret.append(v.isoformat())
                    elif type(v) in (datetime.timedelta,): ret.append(v.seconds)
                    #elif type(v) in (str,): ret.append(v.encode('utf-8'))
                    else: ret.append(v)
                    #try: json.dumps(ret[-1], ensure_ascii=False)
                    #except: print 'error encoding ', type(ret[-1]), ret[-1]
                return ret
                    
            data = [convtojsontype(row) for row in data]
            
            #print cachedids, data
            
            # conventionally, the first value in each row is the row id
            data = dict([(row[0], row) for row in data])
            dbids = set(data.keys())
            cachedids = set(cachedids)
            result = {
                'status': 'OK',
                'op': 'sync',
                'table': message['table'],
                'add': [data[Id] for Id in dbids - cachedids  ],
                'delete': list(cachedids - dbids)
                }
            
            self.write_message(json.dumps(result, ensure_ascii=False))
        

    def on_close(self):
        print 'connection closed'
        del WSHandler.clients[self]

    @classmethod
    def notifyclients(cls, notifications):
        #print "Writing to clients"
        for client, account in cls.clients.items():
            
            if not account.busid in notifications: continue
            if len(notifications[account.busid]) == 0: continue
            
            
            print "* sending notifications to client with bus id=%d" %(account.busid), notifications[account.busid]
            
            client.write_message({'op': 'refresh', 'tables': notifications[account.busid]})


application = tornado.web.Application([
    (r'/ws', WSHandler)
])


dbpollerthread = DBPoller(5, WSHandler.notifyclients)

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    #tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=10), WSHandler.write_to_clients)
    tornado.ioloop.IOLoop.instance().start()



