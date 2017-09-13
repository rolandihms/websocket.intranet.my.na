import MySQLdb
import time
import threading

def dbconnection():
    #return MySQLdb.connect(host="mysql16706-intranet.cloudhosting.rsaweb.co.za", user='root', passwd='XILlpt02567', use_unicode=True)
    return MySQLdb.connect(host="127.0.0.1", user='root', passwd='', use_unicode=True)

class DBPoller(object):
    db = dbconnection()
    def __init__(self, interval=3, callback=lambda x: x):
        
        self.interval = interval # in secods

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()
        self.thread = thread
        self.callback = callback
        
    def stop(self):
        self.thread.stop()

    def run(self):
        """
        thread main function, detect updates periodically
        change detection techniques:
        
        1. keep hash of values for each busid, detect if that changes
        2. create trigger on important table in db
        
        
        test: insert into messages(bus_id,user_id,nameFrom,emailFrom,emailTo,emailCC,emailBCC,subject,body,status,opened,flag,date_sent) values(4359, 1, 'Mo',  'mohamed@amaksoud.com', 'christian@intouch.com.na', '','', 'another deal 4', 'deal 1', 'inbox', 'N', 'N', NOW())
        
        """
        
        db = dbconnection()
        
        messageshash = {}
        postshash = {}
        usershash = {}
        groupshash = {}
        eventshash = {}
        # TODO persist hashes in a json file
        while True:
            
            for i in range(3):
                cur = db.cursor()
                try: cur.execute('SELECT bus_id FROM intranet.messages limit 1')
                except: 
                    db = dbconnection()
                    continue
                break


            
            notifications = {}
            
            cur.execute('SELECT bus_id, sha1(GROUP_CONCAT(msg_id,status,opened,flag)) FROM intranet.messages GROUP BY bus_id')
            for busid, h in cur:
                if not busid in messageshash: messageshash[busid] = ''
                if not busid in notifications: notifications[busid] = []
                #print '* comparing hashes `%s` == `%s`' %(messageshash[busid], h)
                
                if not h == messageshash[busid]:
                    print '* messages changed for bus_id `%s`' %(busid)
                    notifications[busid].append('messages')
                
                messageshash[busid] = h
            db.commit()
            
            
            cur.execute('SELECT bus_id, sha1(GROUP_CONCAT(post_id,active)) FROM intranet.posts GROUP BY bus_id')
            for busid, h in cur:
                if not busid in postshash: postshash[busid] = ''
                if not busid in notifications: notifications[busid] = []
                #print '* comparing hashes `%s` == `%s`' %(messageshash[busid], h)
                
                if not h == postshash[busid]: notifications[busid].append('posts')
                
                postshash[busid] = h
            db.commit()
            
            cur.execute('SELECT bus_id, sha1(GROUP_CONCAT(user_id,active,online)) FROM intranet.users GROUP BY bus_id')
            for busid, h in cur:
                if not busid in usershash: usershash[busid] = ''
                if not busid in notifications: notifications[busid] = []
                #print '* comparing hashes `%s` == `%s`' %(messageshash[busid], h)
                
                if not h == usershash[busid]: notifications[busid].append('users')
                
                usershash[busid] = h
            db.commit()
            
            cur.execute('SELECT bus_id, sha1(GROUP_CONCAT(group_id,user_id,title,active)) FROM intranet.groups GROUP BY bus_id')
            for busid, h in cur:
                if not busid in groupshash: groupshash[busid] = ''
                if not busid in notifications: notifications[busid] = []
                #print '* comparing hashes `%s` == `%s`' %(messageshash[busid], h)
                
                if not h == groupshash[busid]: notifications[busid].append('groups')
                
                groupshash[busid] = h
            db.commit()
            
            cur.execute('SELECT bus_id, sha1(GROUP_CONCAT(event_id,startdate,enddate,starttime,endtime,allday,url,type,flag,status)) FROM intranet.events GROUP BY bus_id')
            for busid, h in cur:
                if not busid in eventshash: eventshash[busid] = ''
                if not busid in notifications: notifications[busid] = []
                #print '* comparing hashes `%s` == `%s`' %(messageshash[busid], h)
                
                if not h == eventshash[busid]: notifications[busid].append('events')
                
                eventshash[busid] = h
            db.commit()
            
            self.callback (notifications )

            time.sleep(self.interval)
    
    @classmethod
    def fetchdata(cls, query, params=None):

        for i in range(3):
            cur = cls.db.cursor()
            try: cur.execute('SELECT bus_id FROM intranet.messages limit 1')
            except:
                cls.db = dbconnection()
                continue
            break

        if params is None:
            cur.execute(query)
        else:
            cur.execute(query, params)
        
        results = list(cur)
        cls.db.commit()
        return results
    
        

