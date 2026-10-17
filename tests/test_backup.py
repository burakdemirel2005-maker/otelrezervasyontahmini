import sqlite3
import yedekle

def test_backup_is_consistent(tmp_path,monkeypatch):
    monkeypatch.setattr(yedekle,'ROOT',tmp_path)
    (tmp_path/'artifacts').mkdir()
    with sqlite3.connect(tmp_path/'artifacts/tracking.sqlite3') as db:
        db.execute('CREATE TABLE example (id INTEGER)')
        db.execute('INSERT INTO example VALUES(1)')
    target=yedekle.backup()
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT id FROM example').fetchone()==(1,)
