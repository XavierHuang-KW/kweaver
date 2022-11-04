from db_conn.tests.test_mysql.base import (PyMySQLTestCase, using_mysql, using_mysql_pool)
import pymysql.cursors

import datetime
import warnings


class TestDictCursor(PyMySQLTestCase):
    bob = {"name": "bob", "age": 21, "DOB": datetime.datetime(1990, 2, 6, 23, 4, 56)}
    jim = {"name": "jim", "age": 56, "DOB": datetime.datetime(1955, 5, 9, 13, 12, 45)}
    fred = {"name": "fred", "age": 100, "DOB": datetime.datetime(1911, 9, 12, 1, 1, 1)}

    cursor_type = pymysql.cursors.DictCursor

    @using_mysql()
    def setUp(self, db):
        super(TestDictCursor, self).setUp()

        self.conn = conn = db.connection
        c = db.cursor

        print("test------------------------test")
        # create a table ane some data to query
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            c.execute("drop table if exists dictcursor")
            # include in filterwarnings since for unbuffered dict cursor warning for lack of table
            # will only be propagated at start of next execute() call
            c.execute(
                """CREATE TABLE dictcursor (name char(20), age int , DOB datetime)"""
            )
        data = [
            ("bob", 21, "1990-02-06 23:04:56"),
            ("jim", 56, "1955-05-09 13:12:45"),
            ("fred", 100, "1911-09-12 01:01:01"),
        ]
        c.executemany("insert into dictcursor values (%s,%s,%s)", data)

    @using_mysql
    def tearDown(self, db):
        c = db.cursor
        c.execute("drop table dictcursor")
        super(TestDictCursor, self).tearDown()

    def _ensure_cursor_expired(self, cursor):
        pass

    @using_mysql()
    def test_DictCursor(self, db):
        bob, jim, fred = self.bob.copy(), self.jim.copy(), self.fred.copy()
        # all assert test compare to the structure as would come out from MySQLdb

        c = db.connection.cursor(pymysql.cursors.DictCursor)
        # try an update which should return no rows
        c.execute("update dictcursor set age=20 where name='bob'")
        bob["age"] = 20
        # pull back the single row dict for bob and check
        c.execute("SELECT * from dictcursor where name='bob'")
        r = c.fetchone()
        self.assertEqual(bob, r, "fetchone via DictCursor failed")
        self._ensure_cursor_expired(c)

        # same again, but via fetchall => tuple)
        c.execute("SELECT * from dictcursor where name='bob'")
        r = c.fetchall()
        self.assertEqual(
            [bob], r, "fetch a 1 row result via fetchall failed via DictCursor"
        )
        # same test again but iterate over the
        c.execute("SELECT * from dictcursor where name='bob'")
        for r in c:
            self.assertEqual(
                bob, r, "fetch a 1 row result via iteration failed via DictCursor"
            )
        # get all 3 row via fetchall
        c.execute("SELECT * from dictcursor")
        r = c.fetchall()
        self.assertEqual([bob, jim, fred], r, "fetchall failed via DictCursor")
        # same test again but do a list comprehension
        c.execute("SELECT * from dictcursor")
        r = list(c)
        self.assertEqual([bob, jim, fred], r, "DictCursor should be iterable")
        # get all 2 row via fetchmany
        c.execute("SELECT * from dictcursor")
        r = c.fetchmany(2)
        self.assertEqual([bob, jim], r, "fetchmany failed via DictCursor")
        self._ensure_cursor_expired(c)


    @using_mysql()
    def test_custom_dict(self,db):
        class MyDict(dict):
            pass

        class MyDictCursor(self.cursor_type):
            dict_type = MyDict

        keys = ["name", "age", "DOB"]
        bob = MyDict([(k, self.bob[k]) for k in keys])
        jim = MyDict([(k, self.jim[k]) for k in keys])
        fred = MyDict([(k, self.fred[k]) for k in keys])

        cur = db.connection.cursor(MyDictCursor)
        cur.execute("SELECT * FROM dictcursor WHERE name='bob'")
        r = cur.fetchone()
        self.assertEqual(bob, r, "fetchone() returns MyDictCursor")
        self._ensure_cursor_expired(cur)

        cur.execute("SELECT * FROM dictcursor")
        r = cur.fetchall()
        self.assertEqual([bob, jim, fred], r, "fetchall failed via MyDictCursor")

        cur.execute("SELECT * FROM dictcursor")
        r = list(cur)
        self.assertEqual([bob, jim, fred], r, "list failed via MyDictCursor")

        cur.execute("SELECT * FROM dictcursor")
        r = cur.fetchmany(2)
        self.assertEqual([bob, jim], r, "list failed via MyDictCursor")
        self._ensure_cursor_expired(cur)



if __name__ == "__main__":
    import unittest

    unittest.main()