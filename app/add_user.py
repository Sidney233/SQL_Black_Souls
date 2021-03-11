from app import cursor
from app.models import User

username = "h"
password_hash = '1'

sql = "UPDATE users SET weapon_id = %s WHERE id=%s" % (1, 1)

print(sql)