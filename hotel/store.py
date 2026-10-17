import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
import pandas as pd
from .data import ROOT

STATUSES=['Bekliyor','Teyit edildi','Ulaşılamadı','İncelendi']

@contextmanager
def connect(path=None):
    path=path or ROOT/'artifacts'/'tracking.sqlite3'
    db=sqlite3.connect(path,timeout=15)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS tracking (namespace TEXT, reservation_id TEXT, status TEXT, note TEXT, updated_at TEXT, PRIMARY KEY(namespace,reservation_id))')
            db.execute('CREATE TABLE IF NOT EXISTS events (namespace TEXT,reservation_id TEXT,status TEXT,note TEXT,updated_at TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (namespace TEXT, kind TEXT, label TEXT, reservation_id TEXT, snapshot_date TEXT, payload TEXT, model_id TEXT, created_at TEXT, PRIMARY KEY(namespace,reservation_id,snapshot_date))')
            db.execute('CREATE TABLE IF NOT EXISTS outcomes (namespace TEXT,reservation_id TEXT,snapshot_date TEXT,outcome TEXT,outcome_date TEXT,updated_at TEXT,PRIMARY KEY(namespace,reservation_id,snapshot_date))')
            db.execute('CREATE TABLE IF NOT EXISTS outcome_events (namespace TEXT,reservation_id TEXT,snapshot_date TEXT,outcome TEXT,outcome_date TEXT,updated_at TEXT)')
            yield db
    finally:
        db.close()

def save(namespace,rid,status,note,path=None):
    if status not in STATUSES or len(note)>2000:
        raise ValueError('Geçersiz takip kaydı.')
    values=(namespace,str(rid),status,note,datetime.now(timezone.utc).isoformat())
    with connect(path) as db:
        db.execute('INSERT INTO tracking VALUES(?,?,?,?,?) ON CONFLICT(namespace,reservation_id) DO UPDATE SET status=excluded.status,note=excluded.note,updated_at=excluded.updated_at',values)
        db.execute('INSERT INTO events VALUES(?,?,?,?,?)',values)

def read(namespace,path=None):
    with connect(path) as db:
        return {row[0]:{'status':row[1],'note':row[2],'updated_at':row[3]} for row in db.execute('SELECT reservation_id,status,note,updated_at FROM tracking WHERE namespace=?',(namespace,))}

def save_batch(namespace,frame,model_id,kind,label,path=None):
    """Persist only model inputs and score, atomically; never overwrite a prediction."""
    from .data import FEATURES, validate_active
    if kind not in ['manual','pilot'] or not namespace or not label.strip() or len(label)>120:
        raise ValueError('Geçerli bir kayıt türü ve en fazla 120 karakterlik tesis/deneme adı gerekli.')
    validate_active(frame)
    if 'risk' not in frame or not frame.risk.between(0,1).all():
        raise ValueError('Kaydetmeden önce geçerli model tahmini gerekli.')
    fields=list(dict.fromkeys(['reservation_id','arrival_date','snapshot_date','status']+FEATURES+['risk']))
    records=json.loads(frame[fields].to_json(orient='records',date_format='iso'))
    now=datetime.now(timezone.utc).isoformat(); added=0
    with connect(path) as db:
        for row in records:
            rid=str(row['reservation_id']); day=str(row['snapshot_date'])[:10]
            payload=json.dumps(row,sort_keys=True,ensure_ascii=False)
            existing=db.execute('SELECT payload,model_id FROM snapshots WHERE namespace=? AND reservation_id=? AND snapshot_date=?',(namespace,rid,day)).fetchone()
            if existing:
                if existing!=(payload,model_id):
                    raise ValueError(f'{rid}: bu karar günü için farklı bir tahmin zaten saklı. Eski tahminin üzerine yazılmaz; kimliği veya dosyayı kontrol edin.')
                continue
            db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?)',(namespace,kind,label.strip(),rid,day,payload,model_id,now))
            added+=1
    return added

def collections(path=None):
    with connect(path) as db:
        return [dict(zip(['namespace','kind','label','records'],r)) for r in db.execute('SELECT namespace,kind,MAX(label),COUNT(*) FROM snapshots GROUP BY namespace,kind ORDER BY MAX(created_at) DESC')]

def load_batch(namespace,path=None):
    with connect(path) as db:
        rows=db.execute('SELECT payload,model_id,created_at,label FROM snapshots WHERE namespace=? ORDER BY snapshot_date,reservation_id',(namespace,)).fetchall()
    if not rows: return pd.DataFrame()
    frame=pd.DataFrame([dict(json.loads(r[0]),model_id=r[1],saved_at=r[2],record_label=r[3]) for r in rows])
    for field in ['arrival_date','snapshot_date']:
        frame[field]=pd.to_datetime(frame[field])
    frame['decision_date']=frame.snapshot_date
    return frame

OUTCOMES=['Konakladı','Geç iptal','Gelmedi']

def save_outcome(namespace,rid,snapshot_date,outcome,outcome_date,path=None):
    if outcome not in OUTCOMES: raise ValueError('Geçersiz sonuç.')
    day=pd.Timestamp(snapshot_date).date().isoformat()
    event=pd.Timestamp(outcome_date).date()
    with connect(path) as db:
        record=db.execute('SELECT payload,kind FROM snapshots WHERE namespace=? AND reservation_id=? AND snapshot_date=?',(namespace,str(rid),day)).fetchone()
        if not record or record[1]!='pilot': raise ValueError('Sonuç yalnız kaydedilmiş pilot rezervasyonuna eklenebilir.')
        row=json.loads(record[0]); arrival=pd.Timestamp(row['arrival_date']).date()
        if event<arrival or event>datetime.now().date():
            raise ValueError('Sonuç tarihi gelişten önce veya bugünden sonra olamaz.')
        values=(namespace,str(rid),day,outcome,event.isoformat(),datetime.now(timezone.utc).isoformat())
        db.execute('INSERT INTO outcomes VALUES(?,?,?,?,?,?) ON CONFLICT(namespace,reservation_id,snapshot_date) DO UPDATE SET outcome=excluded.outcome,outcome_date=excluded.outcome_date,updated_at=excluded.updated_at',values)
        db.execute('INSERT INTO outcome_events VALUES(?,?,?,?,?,?)',values)

def outcomes(namespace,path=None):
    with connect(path) as db:
        return pd.read_sql_query('SELECT reservation_id,snapshot_date,outcome,outcome_date,updated_at FROM outcomes WHERE namespace=?',db,params=(namespace,))

def event_history(namespace,path=None):
    with connect(path) as db:
        return pd.read_sql_query('SELECT namespace,reservation_id,status,note,updated_at FROM events WHERE namespace=? OR substr(namespace,1,?)=? ORDER BY updated_at DESC',db,params=(namespace,len(namespace)+1,namespace+':'))

def export_collection(namespace,path=None):
    with connect(path) as db:
        result={}
        for table in ['snapshots','tracking','events','outcomes','outcome_events']:
            # Table names are fixed above, never user-supplied identifiers.
            cursor=db.execute(f'SELECT * FROM {table} WHERE namespace=? OR substr(namespace,1,?)=?',(namespace,len(namespace)+1,namespace+':'))
            columns=[d[0] for d in cursor.description]
            result[table]=[dict(zip(columns,r)) for r in cursor.fetchall()]
    return json.dumps({'format_version':1,'exported_at':datetime.now(timezone.utc).isoformat(),'data':result},ensure_ascii=False,indent=2)
