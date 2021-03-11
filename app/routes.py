from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, redirect, url_for, flash, request
from flask_apscheduler import scheduler
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash
from werkzeug.urls import url_parse
from app import app, cursor, conn
from app.forms import LoginForm, RegistrationForm
from app.models import User, Item
import random
import bisect


scheduler = BackgroundScheduler()
scheduler.start()
users_dic_work = {}
users_dic_explore = {}
rare_list = [1, 2, 3, 4, 5]
MAX_ITEM = 5


@scheduler.scheduled_job('interval', seconds=2)
def flag():
    global users_dic_work
    global users_dic_explore
    for key in users_dic_work:
        users_dic_work[key] = 1
    for key in users_dic_explore:
        users_dic_explore[key] = 1
    print("reset")


def weight_choice(weight):
    weight_sum = []
    sum = 0
    for a in weight:
        sum += a
        weight_sum.append(sum)
    t = random.randint(0, sum - 1)
    return bisect.bisect_right(weight_sum, t)


def weight_count(luck):
    weight = []
    for i in range(5):
        if luck >= 10:
            luck = luck - 10
            weight.append(10)
        elif 0 < luck < 10:
            weight.append(luck)
            luck = 0
        else:
            weight.append(luck)
    return weight


def is_full():
    min = {"_id": "0", "value": 100000}
    cursor.execute("select items.id, items.name, items.type, items.value, items.rare\
                        from items, users, storage\
                        where items.id=storage.item_id and users.id=storage.user_id and users.id=%s" % current_user.id)
    res = cursor.fetchall()
    items = []
    for i in res:
        item = Item(i)
        items.append(item)
    if len(items) >= MAX_ITEM:
        for item in items:
            if item.value < min["value"]:
                min["_id"] = item.id
                min["value"] = item.value
        cursor.execute("DELETE FROM storage WHERE item_id=%s AND user_id = %s " % (min['_id'], current_user.id))
        cursor.execute("INSERT INTO explore VALUES (%s)" % min['_id'])
        conn.commit()
        return True
    else:
        return False


@app.route('/')
@app.route('/index')
@login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    users_dic_work[current_user.id] = 0
    users_dic_explore[current_user.id] = 0
    if current_user.weapon_id is not None:
        cursor.execute("SELECT * FROM items where id =" + str(current_user.weapon_id))
        res = cursor.fetchone()
        weapon = Item(res)
    else:
        weapon = None
    cursor.execute("select items.id, items.name, items.type, items.value, items.rare\
                    from items, users, armors\
                    where items.id=armors.armor_id and users.id=armors.user_id and users.id=%s" % current_user.id)
    res = cursor.fetchall()
    defense = 0
    if len(res) == 0:
        armors = None
    else:
        armors = []
        for i in res:
            armor = Item(i)
            defense = defense + armor.value
            armors.append(armor)
    return render_template("index.html", title='Home Page', weapon=weapon, armors=armors, defense=defense)


@app.route('/login', methods=['GET', 'POST'])
def login():
    global users_dic_work
    global users_dic_explore
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        username = "'" + form.username.data + "'"
        cursor.execute("SELECT * FROM users WHERE username = " + username)
        res = cursor.fetchone()
        if res is None:
            flash('Invalid username')
            return redirect(url_for('login'))
        user = User(res)
        if not user.check_password(form.password.data):
            flash('Invalid password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        users_dic_work[current_user.id] = 0
        users_dic_explore[current_user.id] = 0
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    global users_dic_work, users_dic_explore
    del users_dic_work[current_user.id]
    del users_dic_explore[current_user.id]
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data)
        cursor.execute("insert into items (name, type,value,rare) values ('长剑','weapon',3,1) RETURNING id")
        weapon_id = cursor.fetchone()[0]
        conn.commit()
        cursor.execute("insert into items (name, type,value,rare) values ('骑士铠甲','armor',3,1) RETURNING id")
        armor_id = cursor.fetchone()[0]
        conn.commit()
        sql = "INSERT INTO users(username,password_hash,gold,weapon_id)VALUES(%s,%s,%s,%s) RETURNING id" % (
            "'" + form.username.data + "'", "'" + password_hash + "'", 0, weapon_id)
        cursor.execute(sql)
        user_id = cursor.fetchone()[0]
        conn.commit()
        cursor.execute("insert into armors (user_id,armor_id) values (%s,%s)" % (user_id, armor_id))
        conn.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/equipment/<oid>')
def equipment(oid):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("SELECT * FROM items WHERE id=%s" % oid)
    res = cursor.fetchone()
    item = Item(res)
    equiped = 0
    cursor.execute("SELECT * FROM market WHERE item_id=%s" % oid)
    res = cursor.fetchone()
    if res:
        on_sale = 1
    else:
        on_sale = 0
    if item.type == 'weapon':
        type = '武器'
        pattern = '攻击力'
        if oid == str(current_user.weapon_id):
            equiped = 1
    else:
        type = '盔甲'
        pattern = '防御力'
        cursor.execute("SELECT * FROM users, armors\
                        WHERE id=user_id AND id=%s AND armor_id=%s" % (current_user.id, oid))
        res = cursor.fetchone()
        if res is not None:
            equiped = 1
    return render_template('equipment.html', item=item, type=type, equiped=equiped, pattern=pattern, on_sale=on_sale)


@app.route('/storage')
def storage():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    items = []
    cursor.execute("select items.id, items.name, items.type, items.value, items.rare\
                    from items, users, storage\
                    where items.id=storage.item_id and users.id=storage.user_id and users.id=%s" % current_user.id)
    res = cursor.fetchall()
    for i in res:
        item = Item(i)
        items.append(item)
    return render_template('storage.html', items=items)


@app.route('/equip_weapon/<oid>')
def equip_weapon(oid):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    prev_weapon_id = current_user.weapon_id
    cursor.execute("UPDATE users SET weapon_id = %s WHERE id=%s" % (oid, current_user.id))
    cursor.execute("DELETE FROM storage WHERE item_id=%s AND user_id=%s" % (oid, current_user.id))
    if prev_weapon_id:
        cursor.execute("INSERT INTO storage (user_id,item_id) VALUES (%s,%s)" % (current_user.id, prev_weapon_id))
    conn.commit()
    return redirect(url_for('index'))


@app.route('/unequip_weapon')
def unequip_weapon():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    prev_weapon_id = current_user.weapon_id
    cursor.execute("UPDATE users SET weapon_id = NULL WHERE id=%s" % current_user.id)
    cursor.execute("INSERT INTO storage (user_id,item_id) VALUES (%s,%s)" % (current_user.id, prev_weapon_id))
    is_full()
    conn.commit()
    return redirect(url_for('index'))


@app.route('/equip_armor/<oid>')
def equip_armor(oid):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("select *\
                    from users, armors\
                    where users.id=armors.user_id and users.id=%s" % current_user.id)
    res = cursor.fetchall()
    if len(res) >= 2:
        flash("护甲已满，请卸下再装备")
    else:
        cursor.execute("insert into armors (user_id,armor_id) values (%s,%s)" % (current_user.id, oid))
        cursor.execute("DELETE FROM storage WHERE item_id=%s AND user_id=%s" % (oid, current_user.id))
        conn.commit()
    return redirect(url_for('index'))


@app.route('/unequip_armor/<oid>')
def unequip_armor(oid):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("DELETE FROM armors WHERE armor_id=%s AND user_id=%s" % (oid, current_user.id))
    cursor.execute("INSERT INTO storage (user_id,item_id) VALUES (%s,%s)" % (current_user.id, oid))
    is_full()
    conn.commit()
    return redirect(url_for('index'))


@app.route('/work')
def work():
    global users_dic_work
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if current_user.weapon_id is None:
        flash("未装备武器！")
        return redirect(url_for('index'))
    else:
        if users_dic_work[current_user.id] == 1:
            cursor.execute("SELECT * FROM items WHERE id=%s" % current_user.weapon_id)
            res = cursor.fetchone()
            weapon = Item(res)
            gold = current_user.gold
            cursor.execute("UPDATE users SET gold = %s WHERE id=%s" % (gold+weapon.value, current_user.id))
            conn.commit()
            flash("获得" + str(weapon.value) + "金币！")
            users_dic_work[current_user.id] = 0
            return redirect(url_for('index'))
        else:
            flash("未到出击时间！")
            return redirect(url_for('index'))


@app.route('/explore')
def explore():
    global users_dic_explore
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("select *\
                        from users, armors\
                        where users.id=armors.user_id and users.id=%s" % current_user.id)
    res = cursor.fetchall()
    if len(res) == 0:
        flash("未装备铠甲！")
        return redirect(url_for('index'))
    else:
        if users_dic_explore[current_user.id] == 1:
            defense = 0
            for i in res:
                armor = Item(i)
                defense = defense + armor.value
            rare = rare_list[weight_choice(weight_count(defense))]
            cursor.execute("SELECT id,name,type,value,rare FROM items,explore WHERE id=item_id AND rare=%s" % rare)
            res = cursor.fetchall()
            item = random.choice(res)
            item = Item(item)
            cursor.execute("INSERT INTO storage (user_id,item_id) VALUES (%s,%s)" % (current_user.id, item.id))
            is_full()
            cursor.execute("DELETE FROM explore WHERE item_id=%s" % item.id)
            conn.commit()
            users_dic_explore[current_user.id] = 0
            flash("获得" + item.name + "！")
            return redirect(url_for('index'))
        else:
            flash("未到探索时间！")
            return redirect(url_for('index'))


@app.route('/market')
def market():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("SELECT items.id,name,type,value,rare,prize,username\
                    FROM items,market,users\
                    WHERE items.id = item_id AND users.id = user_id")
    res = cursor.fetchall()
    items = []
    for i in res:
        item = {}
        item['id'] = i[0]
        item['name'] = i[1]
        if i[2] == 'weapon':
            item['type'] = '武器'
        else:
            item['type'] = '盔甲'
        item['value'] = i[3]
        item['rare'] = i[4]
        item['prize'] = i[5]
        item['username'] = i[6]
        items.append(item)
    return render_template('market.html', items=items)


@app.route('/buy/<oid>')
def buy(oid):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("SELECT prize,users.id,name\
                    FROM items,market,users\
                    WHERE items.id = item_id AND users.id = user_id AND items.id=%s" % oid)
    res = cursor.fetchone()
    cursor.execute("SELECT * FROM users WHERE id=%s" % res[1])
    owner = User(cursor.fetchone())
    if res[0] > current_user.gold:
        flash("金币不足！")
        return redirect(url_for('market'))
    gold = current_user.gold - int(res[0])
    owner_gold = owner.gold + int(res[0])
    cursor.execute("DELETE FROM market WHERE item_id=%s" % oid)
    cursor.execute("UPDATE users SET gold = %s WHERE id=%s" % (gold, current_user.id))
    cursor.execute("UPDATE users SET gold = %s WHERE id=%s" % (owner_gold, owner.id))
    cursor.execute("DELETE FROM storage WHERE item_id=%s AND user_id = %s " % (oid, owner.id))
    cursor.execute("INSERT INTO storage (user_id,item_id) VALUES (%s,%s)" % (current_user.id, oid))
    is_full()
    conn.commit()
    flash("成功购买" + res[2] + "！")
    return redirect(url_for('market'))


@app.route("/off/<oid>")
def off(oid):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    cursor.execute("DELETE FROM market WHERE item_id=%s" % oid)
    is_full()
    conn.commit()
    flash("成功下架！")
    return redirect(url_for('index'))


@app.route('/on/<oid>', methods=['GET', 'POST'])
def on(oid):
    if request.method == 'POST':
        prize = request.form['prize']
        cursor.execute("insert into market (user_id,item_id,prize) values (%s,%s,%s)" % (current_user.id, oid, prize))
        conn.commit()
        flash("上架成功！")
        return redirect(url_for('index'))
    else:
        return render_template("on.html")
