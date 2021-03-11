from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import cursor
from flask_login import UserMixin
from app import login


class User(UserMixin):
    id = ""
    username = ""
    password_hash = ""
    weapon_id = None
    gold = 0

    def __init__(self, row):
        self.id = row[0]
        self.username = row[1]
        self.password_hash = row[2]
        self.weapon_id = row[3]
        self.gold = row[4]

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """获取用户ID"""
        return self.id

    @staticmethod
    def get(user_id):
        if not user_id:
            return None
        cursor.execute("SELECT * FROM users WHERE id = "+str(user_id))
        res = cursor.fetchone()
        if res:
            user = User(res)
            return user
        else:
            return None


class Item:
    id = ""
    name = ""
    type = ""
    value = 0
    rare = 0

    def __init__(self, row):
        self.id = row[0]
        self.name = row[1]
        self.type = row[2]
        self.value = row[3]
        self.rare = row[4]


@login.user_loader
def load_user(user_id):
    return User.get(user_id)
