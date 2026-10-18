import os
import sqlite3
import traceback
from atexit import register

from .config_manager import Config
from .constant import ARCAEA_LOG_DATBASE_VERSION, Constant
from .error import ArcError, InputError
from .util import parse_version


class Connect:
    # Database connection class, context manager
    logger = None

    def __init__(
        self,
        file_path: str = Constant.SQLITE_DATABASE_PATH,
        in_memory: bool = False,
        logger=None,
        begin_mode=None
    ) -> None:
        """
            Database connection, defaults to connecting to arcaea_database.db
            Accepts: file path
            Returns: sqlite3 connection operation object
        """
        self.file_path = file_path
        self.in_memory: bool = in_memory
        self.begin_mode = begin_mode
        if logger is not None:
            self.logger = logger

        self.conn: sqlite3.Connection = None
        self.c: sqlite3.Cursor = None

    def __enter__(self) -> sqlite3.Cursor:
        if self.in_memory:
            self.conn = sqlite3.connect(
                'file:arc_tmp?mode=memory&cache=shared', uri=True, timeout=10)
        else:
            self.conn = sqlite3.connect(self.file_path, timeout=10)
        self.c = self.conn.cursor()
        if self.begin_mode is not None:
            self.c.execute(f'begin {self.begin_mode}')
        return self.c

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            if exc_type is not None:
                # On any exception, discard the changes made in this block.
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            # Always release the connection, even if commit/rollback failed.
            try:
                self.conn.close()
            except Exception:
                pass

        if exc_type is None or issubclass(exc_type, ArcError):
            # Commit succeeded, or let ArcError propagate so the caller can
            # turn it into a response.
            return False

        # Unexpected errors are logged and then re-raised instead of being
        # silently swallowed, so real bugs are not hidden behind a generic
        # error response. Returning False lets the exception propagate.
        if self.logger is not None:
            self.logger.error(
                ''.join(traceback.format_exception(exc_type, exc_val, exc_tb)))
        return False


class Query:
    '''Query parameter class'''

    def __init__(self, query_able: list = None, fuzzy_query_able: list = None, sort_able: list = None) -> None:
        self.query_able: list = query_able  # None means no restriction
        self.fuzzy_query_able: list = fuzzy_query_able  # None means no restriction
        self.sort_able: list = sort_able

        self.__limit: int = -1
        self.__offset: int = 0

        # {'name': 'admin'} or {'name': ['admin', 'user']}
        self.__query: dict = {}
        self.__fuzzy_query: dict = {}  # {'name': 'dmi'}

        # [{'column': 'user_id', 'order': 'ASC'}, ...]
        self.__sort: list = []

    @property
    def limit(self) -> int:
        return self.__limit

    @limit.setter
    def limit(self, limit: int) -> None:
        if not isinstance(limit, int):
            raise InputError(api_error_code=-101)
        self.__limit = limit

    @property
    def offset(self) -> int:
        return self.__offset

    @offset.setter
    def offset(self, offset: int) -> None:
        if not isinstance(offset, int):
            raise InputError(api_error_code=-101)
        self.__offset = offset

    @property
    def query(self) -> dict:
        return self.__query

    @query.setter
    def query(self, query: dict) -> None:
        self.__query = {}
        self.query_append(query)

    def query_append(self, query: dict) -> None:
        if not isinstance(query, dict):
            raise InputError(api_error_code=-101)
        if self.query_able is not None and query and not set(query).issubset(set(self.query_able)):
            raise InputError(api_error_code=-102)
        if not self.__query:
            self.__query = query
        else:
            self.__query.update(query)

    @property
    def fuzzy_query(self) -> dict:
        return self.__fuzzy_query

    @fuzzy_query.setter
    def fuzzy_query(self, fuzzy_query: dict) -> None:
        self.__fuzzy_query = {}
        self.fuzzy_query_append(fuzzy_query)

    def fuzzy_query_append(self, fuzzy_query: dict) -> None:
        if not isinstance(fuzzy_query, dict):
            raise InputError(api_error_code=-101)
        if self.fuzzy_query_able is not None and fuzzy_query and not set(fuzzy_query).issubset(set(self.fuzzy_query_able)):
            raise InputError(api_error_code=-102)
        if not self.__fuzzy_query:
            self.__fuzzy_query = fuzzy_query
        else:
            self.__fuzzy_query.update(fuzzy_query)

    @property
    def sort(self) -> list:
        return self.__sort

    @sort.setter
    def sort(self, sort: list) -> None:
        if not isinstance(sort, list):
            raise InputError(api_error_code=-101)
        if self.sort_able is not None and sort:
            for x in sort:
                if not isinstance(x, dict):
                    raise InputError(api_error_code=-101)
                if 'column' not in x or x['column'] not in self.sort_able:
                    raise InputError(api_error_code=-103)
                if 'order' not in x:
                    x['order'] = 'ASC'
                else:
                    if x['order'] not in ['ASC', 'DESC']:
                        raise InputError(api_error_code=-104)
        self.__sort = sort

    def set_value(self, limit=-1, offset=0, query=None, fuzzy_query=None, sort=None) -> None:
        self.limit = limit
        self.offset = offset
        self.query = query if query is not None else {}
        self.fuzzy_query = fuzzy_query if fuzzy_query is not None else {}
        self.sort = sort if sort is not None else []

    def from_dict(self, d: dict) -> 'Query':
        self.set_value(d.get('limit', -1), d.get('offset', 0),
                       d.get('query', {}), d.get('fuzzy_query', {}), d.get('sort', []))
        return self

    def from_args(self, query: dict, limit: int = -1, offset: int = 0, sort: list = None, fuzzy_query: dict = None) -> 'Query':
        self.set_value(limit, offset, query, fuzzy_query, sort)
        return self


class Sql:
    '''
        Database insert/query/delete/update class
    '''

    def __init__(self, c=None) -> None:
        self.c = c

    @staticmethod
    def get_select_sql(table_name: str, target_column: list = None, query: 'Query' = None):
        '''Build a single-row query SQL statement within one table, return the statement and parameter list'''
        sql_list = []
        if not target_column:
            sql = f'select * from {table_name}'
        else:
            sql = f"select {', '.join(target_column)} from {table_name}"

        if query is None:
            return sql, sql_list

        where_key = []
        for k, v in query.query.items():
            if isinstance(v, list):
                where_key.append(f"{k} in ({','.join(['?'] * len(v))})")
                sql_list.extend(v)
            else:
                where_key.append(f'{k}=?')
                sql_list.append(v)

        for k, v in query.fuzzy_query.items():
            where_key.append(f'{k} like ?')
            sql_list.append(f'%{v}%')

        if where_key:
            sql += ' where '
            sql += ' and '.join(where_key)

        if query.sort:
            sql += ' order by ' + \
                ', '.join([x['column'] + ' ' + x['order'] for x in query.sort])

        if query.limit >= 0:
            sql += ' limit ? offset ?'
            sql_list.append(query.limit)
            sql_list.append(query.offset)

        return sql, sql_list

    @staticmethod
    def get_insert_sql(table_name: str, key: list = None, value_len: int = None, insert_type: str = None) -> str:
        '''Build an insert statement; note that only the SQL statement is returned, insert_type is replace or ignore'''
        if key is None:
            key = []
        insert_type = 'replace' if insert_type in [
            'replace', 'R', 'r', 'REPLACE'] else 'ignore'
        return ('insert into ' if insert_type is None else 'insert or ' + insert_type + ' into ') + table_name + ('(' + ','.join(key) + ')' if key else '') + ' values(' + ','.join(['?'] * (len(key) if value_len is None else value_len)) + ')'

    @staticmethod
    def get_update_sql(table_name: str, d: dict = None, query: 'Query' = None):
        if not d:
            return None
        sql_list = []
        sql = f"update {table_name} set {','.join([f'{k}=?' for k in d.keys()])}"
        sql_list.extend(d.values())

        if query is None:
            return sql, sql_list

        where_key = []
        for k, v in query.query.items():
            if isinstance(v, list):
                where_key.append(f"{k} in ({','.join(['?'] * len(v))})")
                sql_list.extend(v)
            else:
                where_key.append(f'{k}=?')
                sql_list.append(v)

        for k, v in query.fuzzy_query.items():
            where_key.append(f'{k} like ?')
            sql_list.append(f'%{v}%')

        if where_key:
            sql += ' where '
            sql += ' and '.join(where_key)

        return sql, sql_list

    @staticmethod
    def get_update_many_sql(table_name: str, key: list = None, where_key: list = None) -> str:
        '''Build an update statement; the Query class and dict are not used here, note that only the SQL statement is returned'''
        if not key or not where_key:
            return None
        return f"update {table_name} set {','.join([f'{k}=?' for k in key])} where {' and '.join([f'{k}=?' for k in where_key])}"

    @staticmethod
    def get_delete_sql(table_name: str, query: 'Query' = None):
        '''Build a delete statement; only query and fuzzy_query in the query are handled'''
        sql = f'delete from {table_name}'

        if query is None:
            return sql, []

        sql_list = []
        where_key = []
        for k, v in query.query.items():
            if isinstance(v, list):
                where_key.append(f"{k} in ({','.join(['?'] * len(v))})")
                sql_list.extend(v)
            else:
                where_key.append(f'{k}=?')
                sql_list.append(v)

        for k, v in query.fuzzy_query.items():
            where_key.append(f'{k} like ?')
            sql_list.append(f'%{v}%')

        if where_key:
            sql += ' where '
            sql += ' and '.join(where_key)

        return sql, sql_list

    @staticmethod
    def get_count_sql(table_name: str, query: 'Query' = None):
        '''Build a single-row count SQL statement within one table, return the statement and parameter list; only query and fuzzy_query in the query are handled'''
        sql_list = []
        sql = f'select count(*) from {table_name}'
        if query is None:
            return sql, sql_list
        where_key = []
        for k, v in query.query.items():
            if isinstance(v, list):
                where_key.append(f"{k} in ({','.join(['?'] * len(v))})")
                sql_list.extend(v)
            else:
                where_key.append(f'{k}=?')
                sql_list.append(v)
        for k, v in query.fuzzy_query.items():
            where_key.append(f'{k} like ?')
            sql_list.append(f'%{v}%')
        if where_key:
            sql += ' where ' + ' and '.join(where_key)
        return sql, sql_list

    def select(self, table_name: str, target_column: list = None, query: 'Query' = None) -> list:
        '''Execute a single-row select SQL statement within one table, return fetchall data'''
        sql, sql_list = self.get_select_sql(table_name, target_column, query)
        self.c.execute(sql, sql_list)
        return self.c.fetchall()

    def select_exists(self, table_name: str, target_column: list = None, query: 'Query' = None) -> bool:
        '''Execute a single-row select exists SQL statement within one table, return a bool value'''
        sql, sql_list = self.get_select_sql(table_name, target_column, query)
        self.c.execute('select exists(' + sql + ')', sql_list)
        return self.c.fetchone() == (1,)

    def select_count(self, table_name: str, query: 'Query' = None) -> int:
        '''Execute a single-row select count SQL statement within one table, return the count'''
        sql, sql_list = self.get_count_sql(table_name, query)
        self.c.execute(sql, sql_list)
        return self.c.fetchone()[0]

    def insert(self, table_name: str, key: list, value: tuple, insert_type: str = None) -> None:
        '''Insert a single row or overwrite insert; passing [] for key means all columns, insert_type is replace or ignore'''
        self.c.execute(self.get_insert_sql(
            table_name, key, len(value), insert_type), value)

    def insert_many(self, table_name: str, key: list, value_list: list, insert_type: str = None) -> None:
        '''Insert multiple rows or overwrite insert; passing [] for key means all columns, insert_type is replace or ignore'''
        if not value_list:
            return
        self.c.executemany(self.get_insert_sql(
            table_name, key, len(value_list[0]), insert_type), value_list)

    def update(self, table_name: str, d: dict, query: 'Query' = None) -> None:
        '''Execute a single-row update SQL statement within one table'''
        if not d:
            return
        sql, sql_list = self.get_update_sql(table_name, d, query)
        self.c.execute(sql, sql_list)

    def update_many(self, table_name: str, key: list, value_list: list, where_key: list, where_value_list: list) -> None:
        '''Execute multiple update SQL statements within one table; the Query class and dict are not used here, the value list lengths must match, somewhat like insert_many'''
        if not key or not value_list or not where_key or not where_value_list or not len(key) == len(value_list[0]) or not len(where_key) == len(where_value_list[0]) or not len(value_list) == len(where_value_list):
            raise ValueError
        self.c.executemany(self.get_update_many_sql(
            table_name, key, where_key), [x + y for x, y in zip(value_list, where_value_list)])

    def delete(self, table_name: str, query: 'Query' = None) -> None:
        '''Delete; only query and fuzzy_query in the query are handled'''
        sql, sql_list = self.get_delete_sql(table_name, query)
        self.c.execute(sql, sql_list)

    def get_table_info(self, table_name: str):
        '''Get the table structure, return the primary key list and field name list'''
        pk = []
        name = []

        self.c.execute(f'''pragma table_info ("{table_name}")''')  # Cannot be parameterized here
        x = self.c.fetchall()
        if x:
            for i in x:
                name.append(i[1])
                if i[5] != 0:
                    pk.append(i[1])

        return pk, name


class DatabaseMigrator:

    SPECIAL_UPDATE_VERSION = {
        '2.11.3.11': '_version_2_11_3_11',
        '2.11.3.13': '_version_2_11_3_13',
        '2.12.1.15': '_version_2_12_1_15'
    }

    def __init__(self, c1_path: str, c2_path: str) -> None:
        self.c1_path = c1_path
        self.c2_path = c2_path

        self.c1 = None
        self.c2 = None

        self.tables = Constant.DATABASE_MIGRATE_TABLES

    @staticmethod
    def update_one_table(c1, c2, table_name: str) -> bool:
        '''Update a data table from c1 to c2; existing information in c1 stays unchanged, i.e. conflicting information in c2 is overwritten'''
        c1.execute(
            '''select * from sqlite_master where type = 'table' and name = :a''', {'a': table_name})
        c2.execute(
            '''select * from sqlite_master where type = 'table' and name = :a''', {'a': table_name})
        if not c1.fetchone() or not c2.fetchone():
            return False

        sql1 = Sql(c1)
        sql2 = Sql(c2)
        db1_pk, db1_name = sql1.get_table_info(table_name)
        db2_pk, db2_name = sql2.get_table_info(table_name)
        if db1_pk != db2_pk:
            return False

        public_column = list(filter(lambda x: x in db2_name, db1_name))

        sql2.insert_many(table_name, public_column, sql1.select(
            table_name, public_column), insert_type='replace')

        return True

    @staticmethod
    def update_user_char_full(c) -> None:
        '''Update user_char_full with data from the character table'''
        c.execute('''select character_id, max_level, is_uncapped from character''')
        x = c.fetchall()
        c.execute('''select user_id from user''')
        y = c.fetchall()
        c.execute('''delete from user_char_full''')
        for i in x:
            exp = 25000 if i[1] == 30 else 10000
            c.executemany('''insert into user_char_full values(?,?,?,?,?,?,0)''', [
                          (j[0], i[0], i[1], exp, i[2], 0) for j in y])

    def update_database(self) -> None:
        '''
        Add or overwrite data that does not exist in the c1 database onto the c2 database
        For c2, update some tables and update user_char_full with character data
        '''
        with Connect(self.c2_path) as c2:
            with Connect(self.c1_path) as c1:
                self.c1 = c1
                self.c2 = c2
                self.special_update()

                for i in self.tables:
                    self.update_one_table(c1, c2, i)

                if not Constant.UPDATE_WITH_NEW_CHARACTER_DATA:
                    self.update_one_table(c1, c2, 'character')

            self.update_user_char_full(c2)  # Update user_char_full

    def special_update(self):
        old_version = self.c1.execute(
            '''select value from config where id = "version"''').fetchone()
        new_version = self.c2.execute(
            '''select value from config where id = "version"''').fetchone()
        old_version = old_version[0] if old_version else '0.0.0'
        new_version = new_version[0] if new_version else '0.0.0'
        old_version = parse_version(old_version)
        new_version = parse_version(new_version)

        for k, v in self.SPECIAL_UPDATE_VERSION.items():
            if old_version < parse_version(k) <= new_version:
                getattr(self, v)()

    def _version_2_11_3_11(self):
        '''
        Special update for version 2.11.3.11, adjust the recent30 table structure
        The recent30 table changes from (user_id: int PK, rating<index>: real, song_id<index>: text, ...) \
        to (user_id: int PK, r_index: int PK, time_played: int, song_id: text, difficulty: int, score: int, sp, p, n, m, hp, mod, clear_type, rating: real)
        '''

        self.tables = [x for x in self.tables if x != 'recent30']

        x = self.c1.execute('''select * from recent30''')
        sql_list = []
        for i in x:
            user_id = int(i[0])
            for j in range(30):
                rating = i[1 + j * 2]
                rating = float(rating) if rating else 0
                song_id_difficulty: str = i[2 + j * 2]
                if song_id_difficulty:
                    song_id = song_id_difficulty[:-1]
                    difficulty = song_id_difficulty[-1]
                    difficulty = int(difficulty) if difficulty.isdigit() else 0
                else:
                    song_id = ''
                    difficulty = 0

                sql_list.append(
                    (user_id, j, 100-j, song_id, difficulty, rating))

        self.c2.executemany(
            '''insert into recent30(user_id, r_index, time_played, song_id, difficulty, rating) values(?,?,?,?,?,?)''', sql_list)

    def _version_2_11_3_13(self):
        '''
        Special update for version 2.11.3.13, world_rank_score mechanism adjusted, user scores need to be cleared
        '''
        self.c1.execute('''update user set world_rank_score = 0''')

    def _version_2_12_1_15(self):
        '''
        Special update for version 2.12.1.15, PTT mechanism adjusted and needs recalculation, here it is just cleared
        '''
        self.c1.execute('''update user set rating_ptt = 0''')


class LogDatabaseMigrator:

    def __init__(self, c1_path: str = Config.SQLITE_LOG_DATABASE_PATH) -> None:
        self.c1_path = c1_path
        # self.c2_path = c2_path
        self.init_folder_path = Config.DATABASE_INIT_PATH
        self.c = None

    @property
    def sql_path(self) -> str:
        return os.path.join(self.init_folder_path, 'log_tables.sql')

    def table_update(self) -> None:
        '''Directly update the database structure'''
        with open(self.sql_path, 'r') as f:
            self.c.executescript(f.read())
        self.c.execute(
            '''insert or replace into cache values("version", :a, -1);''', {'a': ARCAEA_LOG_DATBASE_VERSION})

    def update_database(self) -> None:
        with Connect(self.c1_path) as c:
            self.c = c
            self.table_update()


class MemoryDatabase:
    conn = sqlite3.connect('file:arc_tmp?mode=memory&cache=shared', uri=True)

    def __init__(self):
        self.c = self.conn.cursor()
        self.c.execute('''PRAGMA journal_mode = OFF''')
        self.c.execute('''PRAGMA synchronous = 0''')
        self.c.execute('''create table if not exists download_token(user_id int,
        song_id text,file_name text,token text,time int,primary key(user_id, song_id, file_name));''')
        self.c.execute('''create table if not exists bundle_download_token(token text primary key,
                       file_path text, time int, device_id text);''')
        self.c.execute(
            '''create index if not exists download_token_1 on download_token (song_id, file_name);''')
        self.c.execute('''
            create table if not exists notification(
                user_id int, id int,
                type text, content text,
                sender_user_id int, sender_name text,
                timestamp int,
                primary key(user_id, id)
            )
        ''')
        self.conn.commit()


@register
def atexit():
    MemoryDatabase.conn.close()


class UserKVTable:
    '''User key-value table'''

    def __init__(self, c=None, user_id: int = None, class_name: str = None) -> None:
        self.c = c
        self.user_id = user_id
        self.class_name = class_name

    def get(self, key: str, idx: int = 0):
        '''Get key-value pair'''
        x = self.c.execute(
            '''select value from user_kvdata where user_id = ? and class = ? and key = ? and idx = ?''', (self.user_id, self.class_name, key, idx)).fetchone()
        return x[0] if x else None

    def set(self, key: str, value, idx: int = 0) -> None:
        '''Set key-value pair'''
        self.c.execute('''insert or replace into user_kvdata values(?,?,?,?,?)''',
                       (self.user_id, self.class_name, key, idx, value))

    def __getitem__(self, args):
        if isinstance(args, tuple):
            return self.get(*args)
        else:
            return self.get(args)

    def __setitem__(self, args, value):
        if isinstance(args, tuple):
            self.set(args[0], value, args[1])
        else:
            self.set(args, value)
