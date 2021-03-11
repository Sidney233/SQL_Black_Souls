from werkzeug.security import check_password_hash

from app import cursor
from app.models import User, Item
id = 1
cursor.execute("insert into items (name, type,value,rare) values ('长剑','weapon',3,1) RETURNING id")
weapon_id = cursor.fetchone()[0]
print(type(weapon_id))
