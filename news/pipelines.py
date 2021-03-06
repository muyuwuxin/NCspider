# -*- coding:utf-8 -*-

# Define your item pipelines here
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from os import path
import logging
import sys
from scrapy import signals
import MySQLdb.cursors
from scrapy.exceptions import DropItem
from twisted.enterprise import adbapi
from spiders import StringProcessor as SP

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%a, %d %b %Y %H:%M:%S',
    filename='scrapy.log',
    filemode='w')


#================sina===============
class NewsPipeline(object):
    def __init__(self,dbpool):
        self.dbpool = dbpool
        #---------create database-------------
        self.dbpool.runQuery("""CREATE TABLE IF NOT EXISTS news_opin_tencent_comment (
                                                  id int(11) NOT NULL AUTO_INCREMENT,
                                                  news_id varchar(200) DEFAULT NULL,
                                                  comments_id varchar(200) DEFAULT NULL,
                                                  username varchar(200) DEFAULT NULL,
                                                  comment longtext,
                                                  put_time datetime DEFAULT NULL,
                                                  sex varchar(10) DEFAULT NULL,
                                                  reply_id varchar(200) DEFAULT NULL,
                                                  agree_count int(11) DEFAULT NULL,
                                                  PRIMARY KEY (id)
                                                ) ENGINE=InnoDB AUTO_INCREMENT=12936 DEFAULT CHARSET=utf8;""")

        self.dbpool.runQuery( """CREATE TABLE IF NOT EXISTS news_opin_tencent_article (
                                                  id int(11) NOT NULL AUTO_INCREMENT,
                                                  news_id varchar(100) DEFAULT NULL,
                                                  parent_name varchar(200) DEFAULT NULL,
                                                  news_url varchar(200) DEFAULT NULL,
                                                  title varchar(200) DEFAULT NULL,
                                                  abstract varchar(200) DEFAULT NULL,
                                                  source varchar(50) DEFAULT NULL,
                                                  put_time datetime DEFAULT NULL,
                                                  content longtext,
                                                  comments_id varchar(100) DEFAULT NULL,
                                                  comments_url varchar(200) DEFAULT NULL,
                                                  comments_number int(11) NOT NULL,
                                                  PRIMARY KEY (id)
                                                ) ENGINE=InnoDB AUTO_INCREMENT=1599 DEFAULT CHARSET=utf8;""")

        self.dbpool.runQuery("""CREATE TABLE IF NOT EXISTS news_opin_sohu_article (
                                                  news_id varchar(150) NOT NULL,
                                                  title varchar(300) DEFAULT NULL,
                                                  put_time datetime DEFAULT NULL,
                                                  comments_number int(11) DEFAULT NULL,
                                                  content longtext,
                                                  news_url varchar(200) DEFAULT NULL,
                                                  PRIMARY KEY (news_id)
                                                ) ENGINE=InnoDB DEFAULT CHARSET=utf8;""")

        self.dbpool.runQuery("""CREATE TABLE IF NOT EXISTS news_opin_sohu_comment (
                                                  id int(11) NOT NULL AUTO_INCREMENT,
                                                  comments_id varchar(200) DEFAULT NULL,
                                                  author varchar(50) DEFAULT NULL,
                                                  datetime datetime DEFAULT NULL,
                                                  comment longtext,
                                                  news_id varchar(150) NOT NULL,
                                                  PRIMARY KEY (id),
                                                  KEY news_opin_soh_news_id_2789b31a_fk_news_opin_sohu_article_news_id (news_id),
                                                  CONSTRAINT news_opin_soh_news_id_2789b31a_fk_news_opin_sohu_article_news_id FOREIGN KEY (news_id) REFERENCES news_opin_sohu_article (news_id)
                                                ) ENGINE=InnoDB AUTO_INCREMENT=3834 DEFAULT CHARSET=utf8;""")

        self.dbpool.runQuery("""CREATE TABLE IF NOT EXISTS news_opin_sina_article (
                                                  id int(11) NOT NULL AUTO_INCREMENT,
                                                  news_id varchar(200) DEFAULT NULL,
                                                  title varchar(200) DEFAULT NULL,
                                                  news_url varchar(200) DEFAULT NULL,
                                                  source varchar(50) DEFAULT NULL,
                                                  category varchar(50) DEFAULT NULL,
                                                  put_time datetime DEFAULT NULL,
                                                  content longtext,
                                                  comments_url varchar(250) DEFAULT NULL,
                                                  comments_number int(11) DEFAULT NULL,
                                                  PRIMARY KEY (id)
                                                ) ENGINE=InnoDB AUTO_INCREMENT=1158 DEFAULT CHARSET=utf8;""")

        self.dbpool.runQuery("""CREATE TABLE IF NOT EXISTS news_opin_sina_comment (
                                                  id int(11) NOT NULL AUTO_INCREMENT,
                                                  news_id varchar(200) DEFAULT NULL,
                                                  m_id varchar(200) NOT NULL,
                                                  username varchar(100) DEFAULT NULL,
                                                  comment longtext,
                                                  put_time datetime DEFAULT NULL,
                                                  parent_id varchar(200) DEFAULT NULL,
                                                  agree_count int(11) DEFAULT NULL,
                                                  against_count int(11) DEFAULT NULL,
                                                  PRIMARY KEY (id),
                                                  UNIQUE KEY m_id (m_id)
                                                ) ENGINE=InnoDB AUTO_INCREMENT=2326 DEFAULT CHARSET=utf8;""")

        
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        kw = dict(
            host=settings.get('MYSQL_HOST',' localhost'),
            port=settings.get('MYSQL_PORT', 3306),
            user=settings.get('MYSQL_USER', 'root'),
            db=settings.get('MYSQL_DB', 'test'),
            passwd=settings.get('MYSQL_PASSWD'),
            charset='utf8',
            use_unicode=True,
        )
        dbpool = adbapi.ConnectionPool ('MySQLdb', **kw)
        return cls (dbpool)
    
    def process_item(self, item, spider):
        if spider.name=="sina":
            d = self.dbpool.runInteraction(self._sina_do_execute, item, spider)
            d.addErrback(self._handle_error, item, spider)
            d.addBoth(lambda _: item)
            return d
        elif spider.name=="tencent":
            d = self.dbpool.runInteraction(self._tencent_do_execute, item, spider)
            d.addErrback(self._handle_error, item, spider)
            d.addBoth(lambda _: item)
            return d
        elif spider.name=="sohu":
            d = self.dbpool.runInteraction(self._sohu_do_execute, item, spider)
            d.addErrback(self._handle_error, item, spider)
            d.addBoth(lambda _: item)
            return d
    
    def _sina_do_execute(self, conn, item, spider):
        """
        conn.runQuery() <--> cursor.execute(), return cursor.fetchall();
        conn.execute(), then result = conn.fetchall()
        """
        if item.get("flag")=="cmt number":
            try:
                conn.execute(
                            "update news_opin_sina_article set comments_number=%s where news_id=%s",
                            (item["comments_number"],item['news_ID'])
                     )
            except Exception as e:
                logging.error("Comment number analyse error:" + str(e))
                    
        elif item.get('flag')=='simplenews':
            try:
                if conn.execute("select 1 from news_opin_sina_article where news_url =%s",(item['newsUrl'],)):
                    conn.execute(
                                "update news_opin_sina_article set title=%s, source=%s, category=%s, put_time=%s where news_url=%s",
                                (item['title'] , item['source'],  item['category'],  item['put_time'],item['newsUrl'])
                         )
                else:
                    conn.execute(
                                "insert into news_opin_sina_article (news_url,title,source,category,put_time)  values (%s, %s,%s, %s,%s)",
                                (item['newsUrl'] , item['title'] , item['source'],  item['category'],  item['put_time'])
                         )
            except Exception as ex :    
                logging.error("Simplenews process error:"+str(ex))
        elif item.get('flag')=="news_body":
            try:
                    if not item['news_body']:
                        try:
                            conn.execute(
                                        "update news_opin_sina_article set content=%s, news_id=%s, comments_url=%s where news_url =%s",
                                        ('',item['news_ID'],item['comment_url'],item['newsUrl'])
                                 )
                        except :
                            conn.execute(
                                        "update  news_opin_sina_article set content=%s, news_id=%s, comments_url=%s where news_url =%s",
                                        ('', item['news_ID'],'', item['newsUrl'])
                                 )

                    else:
                        conn.execute(
                                        "update news_opin_sina_article set content=%s, news_id=%s, comments_url=%s where news_url =%s",
                                        (item['news_body'], item['news_ID'],item['comment_url'], item['newsUrl'])
                                 )

            except Exception as ex :    
                logging.error("News article process error:"+str(ex))

        elif item.get("flag")=='comment':
            try:
                query = conn.execute("select m_id from news_opin_sina_comment where m_id=%s", (item["mid"]), )
                if not query:
                    conn.execute(
                             "insert into  news_opin_sina_comment (news_id,  m_id,  username,  comment,  put_time,  parent_id,  agree_count,  against_count)  values (%s, %s,%s, %s,%s, %s,%s, %s)",
                             (  
                                item["newsid"],   item["mid"],  item["nick"],
                                item["content"],  item["time"],item['parent'],
                                item["agree"],item["against"],
                            ))
            except Exception as ex: 
                pass#logging.info("Comment process info:"+str(ex)+'\n'+item['mid'])



    def _tencent_do_execute(self, conn, item, spider):
        if item['flag'] == 'article':
            if conn.execute("select 1 from news_opin_tencent_article where news_id=%s", (item['news_id'],)):
                if  item.get('content') == '':
                    try:
                        if item.get('title','') !='':
                            conn.execute(
                                  """update news_opin_tencent_article set news_url=%s, title=%s, abstract=%s, source=%s, parent_name=%s,  
                                  put_time=%s,
                                  comments_id=%s, comments_url=%s  where news_id=%s""",
                                  (
                                      item.get('url',''), item.get('title',''), item['abstract'], item['source'], item['parent_name'],
                                      item['time'], item['comments_id'], item['comments_url'], item['news_id']
                                  )
                              )
                        else:
                            conn.execute(
                            """update news_opin_tencent_article set comments_number=%s where news_id=%s""",
                            (item['comments_number'], item['news_id'])
                            )
                                               
                    except Exception as e:
                        logging.error("tencent article Exception:"+str(e))

                else:
                    conn.execute(
                        """update news_opin_tencent_article set content=%s where news_id=%s""",
                        (item['content'], item['news_id'])
                    )
            else:
                conn.execute(
                        """insert into news_opin_tencent_article (news_id, comments_number)
                        values (%s, %s)""",
                        (
                            item['news_id'], item['comments_number']
                        )
                )
        elif item['flag'] == 'comment':
            if conn.execute("select 1 from news_opin_tencent_comment where reply_id=%s", (item['reply_id'], )):
                conn.execute(
                        """update news_opin_tencent_comment set agree_count=%s where reply_id=%s""",
                        (item['agree_count'], item['reply_id'])
                )
            else:
                conn.execute(
                        """insert into news_opin_tencent_comment (news_id, comments_id, put_time, comment, username, sex,
                        reply_id, agree_count) values (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            item['news_id'], item['comments_id'], item['datetime'], SP.filter_emoji(item['comment']),
                            item['username'], item['sex'], item['reply_id'], item['agree_count']
                        )
                )


    def _sohu_do_execute(self, conn, item, spider):
        """
        conn.runQuery() <--> cursor.execute(), return cursor.fetchall();
        conn.execute(), then result = conn.fetchall()
        """
        if item['flag'] == 'article':
            if conn.execute("select 1 from  news_opin_sohu_article where news_id=%s", (item['news_id'])):
                if not item['content']:
                    try:
                        conn.execute(
                            """update news_opin_sohu_article set title=%s, put_time=%s, comments_number=%s, news_url=%s
                           where news_id=%s""",
                            (
                                 item['title'], item['time'], item['comments_number'],item['news_id'],item['news_url']
                            )
                        )
                    except Exception as e:
                        logging.error(str(e))
                else:
                    conn.execute(
                        """update news_opin_sohu_article set content=%s where news_id=%s""",
                        (item['content'], item['news_id'])
                    )
            else:
                try:
                        conn.execute(
                                """insert into news_opin_sohu_article (news_id,comments_number,title,put_time,content,news_url)
                                values (%s,%s,%s,%s,%s,%s)""",
                                (
                                    item['news_id'],item['comments_number'],item['title'],item['time'],'',item['news_url'])
                        )
                except Exception as e:
                        logging.error("insert article exception "+str(e))
                        conn.execute(
                        """insert into news_opin_sohu_article (news_id,comments_number)
                        values (%s,%s)""",
                        (
                            item['news_id'],item['comments_number'])
                )
        elif item['flag'] == 'comment':
            
              conn.execute(
                        """insert into  news_opin_sohu_comment (news_id, comments_id, datetime, comment, author) values (%s, %s, %s, %s, %s)""",
                        (
                            item['news_id'], item['comments_id'], item['datetime'], item['comment'],
                            item['author']
                        )
                )


    def _handle_error(self, failure, item, spider):
        logging.error(failure)
