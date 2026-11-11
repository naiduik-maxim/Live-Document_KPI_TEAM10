"""Small SQL scenarios for all 13 tables, without Django or module tags."""

import psycopg
import pytest


def test_change_email(db):
    db.execute("UPDATE core_user SET email='olena@example.test' WHERE id=1")
    row = db.execute("SELECT email FROM core_user WHERE id=1").fetchone()
    assert row == ("olena@example.test",)


def test_hide_template(db):
    db.execute("UPDATE core_template SET is_active=FALSE WHERE id=1")
    row = db.execute("SELECT is_active FROM core_template WHERE id=1").fetchone()
    assert row[0] is False


def test_copy_document_for_another_user(db):
    db.execute(
        "INSERT INTO core_document "
        "(title,template_snapshot,data,status,version,created_at,updated_at,"
        "owner_id,template_id) "
        "SELECT 'Копія для Тараса',template_snapshot,data,'draft',1,NOW(),"
        "NOW(),2,template_id FROM core_document WHERE id=1"
    )
    rows = db.execute(
        "SELECT title FROM core_document WHERE owner_id=2"
    ).fetchall()
    assert rows == [("Копія для Тараса",)]


def test_add_document_comment(db):
    db.execute(
        "INSERT INTO core_documentevent "
        "(document_id,actor_id,from_status,to_status,comment,created_at) "
        "VALUES (1,2,'draft','draft','Уточніть дату',NOW())"
    )
    row = db.execute(
        "SELECT comment,actor_id FROM core_documentevent "
        "WHERE document_id=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row == ("Уточніть дату", 2)


def test_find_comments_by_document_owner(db):
    rows = db.execute(
        "SELECT e.comment FROM core_user u "
        "JOIN core_document d ON d.owner_id=u.id "
        "JOIN core_documentevent e ON e.document_id=d.id "
        "WHERE u.username='olena'"
    ).fetchall()
    assert rows == [("Створено",)]


def test_move_user_to_another_group(db):
    db.execute("INSERT INTO auth_group (id,name) VALUES (10,'A'),(11,'B')")
    db.execute("INSERT INTO core_user_groups (user_id,group_id) VALUES (1,10)")
    db.execute("UPDATE core_user_groups SET group_id=11 WHERE user_id=1")
    rows = db.execute(
        "SELECT g.name FROM auth_group g JOIN core_user_groups ug "
        "ON ug.group_id=g.id WHERE ug.user_id=1"
    ).fetchall()
    assert rows == [("B",)]


def test_grant_group_permission_and_remove_personal_permission(db):
    permission = db.execute(
        "SELECT id FROM auth_permission WHERE codename='view_document'"
    ).fetchone()[0]
    db.execute("INSERT INTO auth_group (id,name) VALUES (10,'Читачі')")
    db.execute(
        "INSERT INTO auth_group_permissions (group_id,permission_id) "
        "VALUES (10,%s)", (permission,),
    )
    db.execute(
        "INSERT INTO core_user_user_permissions (user_id,permission_id) "
        "VALUES (1,%s)", (permission,),
    )
    db.execute("DELETE FROM core_user_user_permissions WHERE user_id=1")
    assert db.execute(
        "SELECT permission_id FROM auth_group_permissions WHERE group_id=10"
    ).fetchall() == [(permission,)]
    assert db.execute(
        "SELECT * FROM core_user_user_permissions WHERE user_id=1"
    ).fetchone() is None


def test_find_content_type_for_document(db):
    rows = db.execute(
        "SELECT model FROM django_content_type "
        "WHERE app_label='core' AND model='document'"
    ).fetchall()
    assert rows == [("document",)]


def test_delete_only_expired_sessions(db):
    db.execute(
        "INSERT INTO django_session (session_key,session_data,expire_date) "
        "VALUES ('old','test',NOW()-INTERVAL '1 day'),"
        "('active','test',NOW()+INTERVAL '1 day')"
    )
    db.execute("DELETE FROM django_session WHERE expire_date < NOW()")
    rows = db.execute("SELECT session_key FROM django_session").fetchall()
    assert rows == [("active",)]


def test_save_admin_comment(db):
    db.execute(
        "INSERT INTO django_admin_log "
        "(action_time,object_id,object_repr,action_flag,change_message,user_id) "
        "VALUES (NOW(),'1','Заява Олени',2,'Змінено заголовок',2)"
    )
    row = db.execute(
        "SELECT change_message FROM django_admin_log WHERE user_id=2"
    ).fetchone()
    assert row == ("Змінено заголовок",)


def test_find_application_migration(db):
    names = db.execute(
        "SELECT name FROM django_migrations WHERE app='core'"
    ).fetchall()
    assert ("0001_initial",) in names


def test_reject_duplicate_username(db):
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute("UPDATE core_user SET username='olena' WHERE id=2")


def test_reject_missing_document_owner(db):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.execute("UPDATE core_document SET owner_id=999 WHERE id=1")


def test_reject_null_document_title(db):
    with pytest.raises(psycopg.errors.NotNullViolation):
        db.execute("UPDATE core_document SET title=NULL WHERE id=1")


def test_rollback_title_change(db):
    db.execute("UPDATE core_document SET title='Помилка' WHERE id=1")
    db.rollback()
    row = db.execute("SELECT title FROM core_document WHERE id=1").fetchone()
    assert row == ("Заява Олени",)
