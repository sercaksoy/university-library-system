import psycopg2
from psycopg2 import sql

from classes.Card import Card
from datetime import datetime
from classes.Stock import Stock
from classes.User import User

""""select distinct e.kategori, e.tur, e.isim, e.olusturucu, e.id, " \
            "e.geldigi_tarih, e.hangi_raf, e.kutuphanede_mi, o.reserve_mi from " \
            "envanter e, odunc o where o.reserve_mi=false and e.kutuphanede_mi=true" \
            "and e.id={id}".format(id=item_id_)"""

try:
    connection = psycopg2.connect(user="postgres",
                                  password="dbyagmur99",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="kutuphane")
    cursor = connection.cursor()


except (Exception, psycopg2.Error) as error:
    print("Error while fetching data from PostgreSQL", error)


def get_all_stock():
    query = "select * from envanter"
    cursor.execute(query)
    # print("Selecting rows from mobile table using cursor.fetchall")
    records = cursor.fetchall()
    stock_list = []
    for row in records:
        s = Stock(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        stock_list.append(s)
    return stock_list


def get_user(user_id):
    query = "select * from kullanicilar where id::int={barcode_no}".format(barcode_no=user_id)
    cursor.execute(query)
    user = cursor.fetchone()
    return User(user[0], user[1], user[2], user[3], user[4], user[5], user[6], user[7])


def get_user_card(user_id):
    query = "select * from kart where sahip_id::int={barcode_no}".format(barcode_no=int(user_id))
    cursor.execute(query)
    card = cursor.fetchone()
    return Card(card[0], card[1], card[2], card[3])


def control_get_operation(user):
    role = user.category
    query = "select tasima_hakki from sinirlar where kategori={user_role}".format(user_role=repr(role))
    cursor.execute(query)
    limit = cursor.fetchone()
    if (role == 'Öğrenci') and user.owned_item == limit:
        return False
    elif (role == 'Öğretim Görevlisi') and user.owned_item == limit:
        return False
    elif (role == 'Memur') and user.owned_item == limit:
        return False
    else:
        return True


def control_get_book(user, item):
    role = user.category
    book_cat = item.category
    book_type = item.kind
    if role != 'Öğretim Görevlisi' and book_cat == 'Kitap' and book_type == 'Ders':
        return False
    else:
        return True


def can_borrow_item(item):
    item_id_ = item.item_id
    query = "select * from " \
            "envanter where kutuphanede_mi=TRUE " \
            "and id::int={id}".format(id=item_id_)
    cursor.execute(query)
    result = cursor.fetchone()
    query = "select * from rezerve where materyal_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    result1 = cursor.fetchone()
    if result is not None and result1 is None:
        return "available"
    else:
        query = "select * from odunc where reserve_mi=FALSE " \
                "and obje_id::int={id}".format(id=item_id_)
        cursor.execute(query)
        result = cursor.fetchone()
        if result is not None:
            return "reserve"
    return "false"


def have_expired_item(user):
    user_id = user.user_id
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%d')
    cursor.execute(sql.SQL("select * from {} where alan_id=%s and teslim_tarihi<%s;").format(sql.Identifier('odunc')), [
        str(user_id),
        formatted_date
    ])
    result = cursor.fetchall()
    item_list = []
    for row in result:
        item_list.append(row)
    return len(item_list) != 0


def get_expired_items(user):
    user_id = user.user_id
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%d')
    cursor.execute(
        sql.SQL("select count(obje_id) from {} where alan_id=%s and teslim_tarihi<%s;").format(sql.Identifier('odunc')),
        [
            str(user_id),
            formatted_date
        ])
    result = cursor.fetchone()
    return result


def borrow_item(user, item_id):
    item_id_ = item_id
    user_id = user.user_id
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%d')
    cursor.execute(sql.SQL("INSERT INTO {} VALUES (%s, %s, %s);").format(sql.Identifier('odunc')), [
        user_id,
        item_id_,
        formatted_date
    ])
    connection.commit()


def reserve_item(user, item):
    item_id_ = item.item_id
    user_id = user.user_id
    reserve_user = find_owner_reserve(item)
    query = "insert into rezerve values ({item_id}, {owner_id}, {goes_to})".format(item_id=item_id_,
                                                                                   owner_id=reserve_user.user_id,
                                                                                   goes_to=user_id)
    cursor.execute(query)
    connection.commit()


def card_operation(amount, increase, card_id):
    op = ''
    if increase is True:
        op = '+'
    else:
        op = '-'
    query = "update kart set bakiye=bakiye{op}{amount} where id::int={id}".format(op=op,
                                                                                  amount=amount,
                                                                                  id=card_id)
    cursor.execute(query)
    connection.commit()


def is_balance_enough(card_id, amount):
    query = "select bakiye from kart where id::int={card_id}".format(card_id=card_id)
    cursor.execute(query)
    result = cursor.fetchone()
    balance = int(result[0])
    return balance > amount


def is_item_reserved(item_id):
    item_id_ = item_id
    query = "select reserve_mi from odunc where obje_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    result = cursor.fetchone()
    print(type(result[0]))
    return result[0]


# itemi rezerve eden kullanıcıyı bulmak için
def find_email_reserve(item_id):
    item_id_ = item_id
    query = "select kime_gidecek_id from rezerve where materyal_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    result = cursor.fetchone()
    receiver_id = str(result[0])
    query = "select email from kullanicilar where id::int={id}".format(id=receiver_id)
    cursor.execute(query)
    result1 = cursor.fetchone()
    return str(result1[0])


def find_owner_reserve(item):
    item_id_ = item.item_id
    query = "select alan_id from odunc where obje_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    result = cursor.fetchone()
    reserve_user = get_user(result[0])
    return reserve_user


def get_belonging_items(user):
    user_id = user.user_id
    query = "select e.id, e.isim, o.teslim_tarihi, o.reserve_mi from odunc o, envanter e where o.obje_id in " \
            "(select obje_id from odunc where alan_id::int={id}) and e.id=o.obje_id".format(id=user_id)
    cursor.execute(query)
    result = cursor.fetchall()
    item_list = []
    for row in result:
        item_list.append(row)
    return item_list


def get_reserved_items(user):
    user_id = user.user_id
    query = "select e.id, e.isim, r.kac_gun_kaldi, r.rezerve_bitecek_tarih from rezerve r, envanter e " \
            "where r.kime_gidecek_id::int={id} and r.materyal_id=e.id".format(id=user_id)
    cursor.execute(query)
    result = cursor.fetchall()
    item_list = []
    for row in result:
        item_list.append(row)
    return item_list


def remove_from_belonging(item_id):
    item_id_ = item_id
    query = "delete from odunc where obje_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    connection.commit()


def remove_from_reserve(item_id):
    item_id_ = item_id
    query = "delete from rezerve where materyal_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    connection.commit()


def is_still_borrowed(item_id):
    item_id_ = item_id
    query = "select * from rezerve where kac_gun_kaldi is not null and " \
            "materyal_id::int={id}".format(id=int(item_id_))
    cursor.execute(query)
    result = cursor.fetchone()
    return result is None


def have_debt(item_id):
    item_id_ = item_id
    query = "select * from borclar where materyal_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    result = cursor.fetchone()
    return result is not None


def delete_from_debts(item_id):
    item_id_ = item_id
    query = "delete from borclar where materyal_id::int={id}".format(id=item_id_)
    cursor.execute(query)
    connection.commit()


def get_debt_items(user):
    user_id = user.user_id
    query = "select distinct b.materyal_id, e.isim, b.tutar from borclar b, " \
            "envanter e, odunc o where b.borclu_id::int={id} and b.materyal_id=e.id " \
            "and o.alan_id=b.borclu_id".format(id=user_id)
    cursor.execute(query)
    result = cursor.fetchall()
    item_list = []
    for row in result:
        item_list.append(row)
    return item_list


def update_debts():
    query = "select * from borclar"
    cursor.execute(query)
    result = cursor.fetchall()
    debt_list = []
    for row in result:
        debt_list.append(row)
    for item in debt_list:
        item_id = item[1] # materyal id
        query = "select * from odunc where obje_id::int={item_id}".format(item_id=item_id)
        cursor.execute(query)
        result1 = cursor.fetchone()
        if result1 is not None:  # odunc tablosunda yoksa atla
            diff = 0 - int((result1[3] - datetime.date(datetime.now())).days)
            query = "update borclar set tutar={diff} where materyal_id::int={id}".format(diff=diff, id=item_id)
            cursor.execute(query)
            connection.commit()


def update_reserves():
    query = "select teslim_edildi_tarih, materyal_id from rezerve where kac_gun_kaldi is not null"
    cursor.execute(query)
    result = cursor.fetchall()
    reserve_list = []
    for row in result:
        reserve_list.append(row)
    for item in reserve_list:
        date = item[0]
        item_id_ = item[1]
        left_day = 5 - int((datetime.date(datetime.now()) - date).days)
        if left_day <= 0:
            query = "delete from rezerve where materyal_id::int={id}".format(id=item_id_)
            cursor.execute(query)
        else:
            query = "update rezerve set kac_gun_kaldi={left_day} where materyal_id::int={id}" \
                .format(left_day=left_day, id=item_id_)
            cursor.execute(query)
        connection.commit()


"""finally:
    # closing database connection.
    if connection:
        cursor.close()
        connection.close()
        print("PostgreSQL connection is closed")"""
