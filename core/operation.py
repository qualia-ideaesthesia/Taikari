from .bundle import BundleParser
from .constant import Constant
from .download import DownloadList
from .error import NoData
from .save import SaveData
from .score import Potential, Score
from .sql import Connect, Sql
from .user import User, UserInfo
from .world import MapParser


class BaseOperation:
    _name: str = None

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs) -> None:
        return self.run(*args, **kwargs)

    def set_params(self, *args, **kwargs) -> None:
        pass

    def run(self, *args, **kwargs) -> None:
        raise NotImplementedError


class RefreshAllScoreRating(BaseOperation):
    '''
        Refresh the ratings of all scores
        Including score_v2
    '''
    _name = 'refresh_all_score_rating'

    def run(self):
        # For efficiency, avoid using the Song class and minimize object usage
        # But it is still quite slow
        with Connect() as c:
            c.execute(
                '''select song_id, rating_pst, rating_prs, rating_ftr, rating_byn, rating_etr from chart''')
            x = c.fetchall()

            songs = [i[0] for i in x]
            c.execute(
                f'''update best_score set rating=0 where song_id not in ({','.join(['?']*len(songs))})''', songs)

            for i in x:
                for j in range(0, 5):
                    defnum = -10  # anything not in the database is treated as a constant of -10
                    if i[j+1] is not None and i[j+1] > 0:
                        defnum = float(i[j+1]) / 10

                    c.execute('''select user_id, score, shiny_perfect_count, perfect_count, near_count, miss_count, clear_type from best_score where song_id=:a and difficulty=:b''', {
                              'a': i[0], 'b': j})
                    y = c.fetchall()
                    values = []
                    where_values = []
                    for k in y:
                        ptt = Score.calculate_rating(defnum, k[1], k[6])
                        ptt = max(ptt, 0)
                        score_v2 = Score.calculate_score_v2(
                            defnum, k[2], k[3], k[4], k[5])
                        values.append((ptt, score_v2,))
                        where_values.append((k[0], i[0], j))
                    if values:
                        Sql(c).update_many('best_score', ['rating', 'score_v2'], values, [
                            'user_id', 'song_id', 'difficulty'], where_values)

            # Update recent30
            song_defum: 'dict[str, list[int]]' = {}
            for i in x:
                song_defum[i[0]] = []
                for j in range(0, 5):
                    defnum = -10
                    if i[j+1] is not None and i[j+1] > 0:
                        defnum = float(i[j+1]) / 10
                    song_defum[i[0]].append(defnum)

            users = c.execute('''select user_id from user''').fetchall()
            for i in users:
                values = []
                where_values = []
                user_id = i[0]
                c.execute(
                    '''select r_index, song_id, difficulty, score, clear_type from recent30 where user_id = ?''', (user_id,))
                for j in c.fetchall():
                    if j[1] in song_defum:
                        defnum = song_defum[j[1]][j[2]]
                    else:
                        defnum = -10
                    ptt = Score.calculate_rating(defnum, j[3], j[4])
                    ptt = max(ptt, 0)

                    values.append((ptt,))
                    where_values.append((user_id, j[0]))

                if values:
                    Sql(c).update_many('recent30', ['rating'], values, [
                        'user_id', 'r_index'], where_values)


class RefreshUsersScoreRating(BaseOperation):
    '''
        Refresh the PTT of all users
        Including world_rank_score
    '''
    _name = 'refresh_users_score_rating'

    def run(self):
        with Connect() as c:
            x = c.execute('''select user_id from user''').fetchall()
            user_ids = [i[0] for i in x]
            values = []
            for user_id in user_ids:
                user = UserInfo(c, user_id)
                p = Potential(c, user)
                values.append((p.value, user._get_world_rank_score()))

            Sql(c).update_many('user', ['rating_ptt', 'world_rank_score'], values, [
                'user_id'], [(i,) for i in user_ids])


class RefreshSongFileCache(BaseOperation):
    '''
        Refresh the song file cache, including rebuilding the file hash cache, re-traversing the file directory, and re-parsing songlist
        Note that when pre-calculation is disabled in the settings, file hashes are not computed
    '''
    _name = 'refresh_song_file_cache'

    def run(self):
        DownloadList.clear_all_cache()
        DownloadList.initialize_cache()


class RefreshBundleCache(BaseOperation):
    '''
        Refresh the bundle cache
    '''
    _name = 'refresh_content_bundle_cache'

    def run(self):
        BundleParser().re_init()


class RefreshWorldMapCache(BaseOperation):
    '''
        Refresh the map cache
    '''
    _name = 'refresh_world_map_cache'

    def run(self):
        MapParser().re_init()


class SaveUpdateScore(BaseOperation):
    '''
        Update scores from the cloud save, overwriting existing ones
        When a user parameter is provided, only that user's scores are updated; otherwise all users' scores are updated
    '''
    _name = 'save_update_score'

    def __init__(self, user=None):
        self.user = user

    def set_params(self, user_id: int = None, *args, **kwargs):
        if user_id is not None:
            self.user = User()
            self.user.user_id = int(user_id)

    def run(self, user=None):
        '''
        parameter:
            `user` - an instance of the `User` class or a subclass
        '''
        if user is not None:
            self.user = user
        if self.user is not None and self.user.user_id is not None:
            self._one_user_update()
        else:
            self._all_update()

    def _one_user_update(self):
        with Connect() as c:
            save = SaveData(c)
            save.select_scores(self.user)

            clear_state = {f'{i["song_id"]}{i["difficulty"]}': i['clear_type']
                           for i in save.clearlamps_data}

            song_id_1 = [i['song_id'] for i in save.scores_data]
            song_id_2 = [i['song_id'] for i in save.clearlamps_data]
            song_id = list(set(song_id_1 + song_id_2))

            c.execute(
                f'''select song_id, rating_pst, rating_prs, rating_ftr, rating_byn, rating_etr from chart where song_id in ({','.join(['?']*len(song_id))})''', song_id)
            x = c.fetchall()
            song_chart_const = {i[0]: [i[1], i[2], i[3], i[4], i[5]]
                                for i in x}  # chart const * 10

            new_scores = []
            for i in save.scores_data:
                rating = 0
                score_v2 = 0
                clear_type = clear_state.get(
                    f'{i["song_id"]}{i["difficulty"]}', 0)
                if i['song_id'] in song_chart_const:
                    defnum = song_chart_const[i['song_id']
                                              ][i['difficulty']] / 10
                    rating = Score.calculate_rating(
                        defnum, i['score'], clear_type)
                    rating = max(rating, 0)

                    score_v2 = Score.calculate_score_v2(
                        defnum, i['shiny_perfect_count'], i['perfect_count'], i['near_count'], i['miss_count'])

                new_scores.append((self.user.user_id, i['song_id'], i['difficulty'], i['score'], i['shiny_perfect_count'], i['perfect_count'],
                                   i['near_count'], i['miss_count'], i['health'], i['modifier'], i['time_played'], clear_type, clear_type, rating, score_v2))

            c.executemany(
                '''insert or replace into best_score values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', new_scores)

    def _all_update(self):
        with Connect() as c:
            c.execute(
                '''select song_id, rating_pst, rating_prs, rating_ftr, rating_byn, rating_etr from chart''')
            song_chart_const = {i[0]: [i[1], i[2], i[3], i[4], i[5]]
                                for i in c.fetchall()}  # chart const * 10
            c.execute('''select user_id from user_save''')
            for y in c.fetchall():
                user = User()
                user.user_id = y[0]
                save = SaveData(c)
                save.select_scores(user)

                clear_state = {f'{i["song_id"]}{i["difficulty"]}': i['clear_type']
                               for i in save.clearlamps_data}

                new_scores = []
                for i in save.scores_data:
                    rating = 0
                    score_v2 = 0
                    clear_type = clear_state.get(
                        f'{i["song_id"]}{i["difficulty"]}', 0)
                    if i['song_id'] in song_chart_const:
                        defnum = song_chart_const[i['song_id']
                                                  ][i['difficulty']] / 10
                        rating = Score.calculate_rating(
                            defnum, i['score'], clear_type)
                        rating = max(rating, 0)

                        score_v2 = Score.calculate_score_v2(
                            defnum, i['shiny_perfect_count'], i['perfect_count'], i['near_count'], i['miss_count'])

                    new_scores.append((user.user_id, i['song_id'], i['difficulty'], i['score'], i['shiny_perfect_count'], i['perfect_count'],
                                       i['near_count'], i['miss_count'], i['health'], i['modifier'], i['time_played'], clear_type, clear_type, rating, score_v2))

                c.executemany(
                    '''insert or replace into best_score values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', new_scores)


class UnlockUserItem(BaseOperation):
    '''
        Unlock/lock all of a user's items
        When a user parameter is provided, only that user's items are updated; otherwise all users' items are updated
    '''
    _name = 'unlock_user_item'

    ALLOW_TYPES = ['single', 'pack', 'world_song',
                   'course_banner', 'world_unlock', 'online_banner']

    def __init__(self, user=None, method: str = 'unlock', item_types: list = ['single', 'pack']):
        self.user = user
        self.set_params(method=method, item_types=item_types)

    def set_params(self, user_id: int = None, method: str = 'unlock', item_types: list = ['single', 'pack'], *args, **kwargs):
        if user_id is not None:
            self.user = User()
            self.user.user_id = int(user_id)
        if method in ['unlock', 'lock']:
            self.method = method
        if isinstance(item_types, list) and all(i in self.ALLOW_TYPES for i in item_types):
            self.item_types = item_types

    def run(self):
        if self.user is not None and self.user.user_id is not None:
            if self.method == 'unlock':
                self._one_user_insert()
            else:
                self._one_user_delete()
        else:
            if self.method == 'unlock':
                self._all_insert()
            else:
                self._all_delete()

    def _one_user_insert(self):
        with Connect() as c:
            c.execute(
                '''select exists(select * from user where user_id = ?)''', (self.user.user_id,))
            if not c.fetchone()[0]:
                raise NoData(
                    f'No such user: `{self.user.user_id}`', api_error_code=-110)
            c.execute(
                f'''select item_id, type from item where type in ({','.join(['?'] * len(self.item_types))})''', self.item_types)
            sql_list = [(self.user.user_id, i[0], i[1])
                        for i in c.fetchall()]
            c.executemany(
                '''insert or ignore into user_item values (?, ?, ?, 1)''', sql_list)

    def _all_insert(self):
        with Connect() as c:
            c.execute('''select user_id from user''')
            x = c.fetchall()
            c.execute(
                f'''select item_id, type from item where type in ({','.join(['?'] * len(self.item_types))})''', self.item_types)
            y = c.fetchall()
            sql_list = [(i[0], j[0], j[1])
                        for i in x for j in y]
            c.executemany(
                '''insert or ignore into user_item values (?, ?, ?, 1)''', sql_list)

    def _one_user_delete(self):
        with Connect() as c:
            c.execute(
                f'''delete from user_item where user_id = ? and type in ({','.join(['?'] * len(self.item_types))})''', (self.user.user_id, *self.item_types))

    def _all_delete(self):
        with Connect() as c:
            c.execute(
                f'''delete from user_item where type in ({','.join(['?'] * len(self.item_types))})''', self.item_types)


def _delete_one_table(c, table_name, user_id):
    c.execute(
        f'''insert into db_deleted.{table_name} select * from {table_name} where user_id = ?''', (user_id,))
    c.execute(f'''delete from {table_name} where user_id = ?''', (user_id,))


class DeleteUserScore(BaseOperation):
    '''
        Delete a single user's scores, excluding recent data
    '''
    _name = 'delete_user_score'

    def __init__(self, user=None):
        self.user = user

    def set_params(self, user_id: int = None, *args, **kwargs):
        if user_id is not None:
            self.user = User()
            self.user.user_id = int(user_id)
        return self

    def run(self):
        assert self.user is not None
        with Connect() as c:
            c.execute('''attach database ? as db_deleted''',
                      (Constant.SQLITE_DATABASE_DELETED_PATH,))
            _delete_one_table(c, 'best_score', self.user.user_id)
            _delete_one_table(c, 'recent30', self.user.user_id)


class DeleteOneUser(BaseOperation):
    '''
        Delete a single user
    '''
    _name = 'delete_one_user'

    TABLES = ['best_score', 'recent30', 'user_char', 'user_char_full', 'user_course', 'user_item',
              'user_present', 'user_redeem', 'user_role', 'user_save', 'user_world', 'user',
              'user_mission', 'user_kvdata']

    def __init__(self, user=None):
        self.user = user

    def set_params(self, user_id: int = None, *args, **kwargs):
        if user_id is not None:
            self.user = User()
            self.user.user_id = int(user_id)
        return self

    def run(self):
        assert self.user is not None
        with Connect() as c:
            c.execute('''attach database ? as db_deleted''',
                      (Constant.SQLITE_DATABASE_DELETED_PATH,))

            self._clear_login(c)
            self._data_save(c)

    def _data_save(self, c):
        c.execute(
            f'''insert into db_deleted.friend select * from friend where user_id_me = ? or user_id_other = ?''', (self.user.user_id, self.user.user_id))
        c.execute(f'''delete from friend where user_id_me = ? or user_id_other = ?''',
                  (self.user.user_id, self.user.user_id))

        [_delete_one_table(c, x, self.user.user_id) for x in self.TABLES]

    def _clear_login(self, c):
        c.execute('''delete from login where user_id = ?''',
                  (self.user.user_id,))
        c.execute('''delete from api_login where user_id = ?''',
                  (self.user.user_id,))
