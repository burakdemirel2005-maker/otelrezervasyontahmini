"""Create a consistent SQLite backup without stopping the app."""
from datetime import datetime
import sqlite3
from hotel.data import ROOT

def backup():
    source=ROOT/'artifacts/tracking.sqlite3'
    if not source.exists():
        raise SystemExit('Henüz bir yerel kayıt veritabanı yok.')
    directory=ROOT/'backups'; directory.mkdir(exist_ok=True)
    target=directory/('otel-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
    with sqlite3.connect(f'file:{source}?mode=ro',uri=True) as src:
        with sqlite3.connect(target) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Yedek bütünlük kontrolü başarısız.')
    print(target)
    return target

if __name__=='__main__': backup()
