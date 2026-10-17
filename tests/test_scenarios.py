import io
import json
from datetime import date,timedelta
import joblib
import pandas as pd
import pytest
from hotel.data import ROOT
from hotel.scenario import reservation,fingerprint,csv_bytes
from hotel.ingest import score_frame
from hotel.store import save_batch,load_batch,collections,save_outcome,outcomes,export_collection

def sample(arrival='2026-10-17',departure='2026-10-20',booked='2026-10-01'):
    return reservation(arrival,departure,booked,'City Hotel',2,0,0,'BB','Online TA','TA/TO','A','Transient')

@pytest.fixture(scope='module')
def bundle(): return joblib.load(ROOT/'artifacts/model.joblib')

def test_dates_and_weekend():
    d=sample().iloc[0]
    assert d.lead_time==16
    assert d.stays_in_weekend_nights==2
    assert d.stays_in_week_nights==1
    assert pd.Timestamp(d.snapshot_date)==pd.Timestamp('2026-10-16')

@pytest.mark.parametrize('kwargs',[{'departure':'2026-10-17'},{'departure':'2026-10-16'},{'booked':'2026-10-17'},{'booked':'2026-10-18'}])
def test_bad_dates(kwargs):
    with pytest.raises(ValueError): sample(**kwargs)

def test_manual_real_model_and_stability(bundle):
    d=sample()
    p=score_frame(d,bundle).risk.iloc[0]
    assert p==score_frame(d.copy(),bundle).risk.iloc[0]
    changed=sample(booked='2026-01-01')
    assert fingerprint(d)!=fingerprint(changed)
    assert abs(p-score_frame(changed,bundle).risk.iloc[0])>1e-6

def test_store_idempotent_atomic_and_immutable(tmp_path,bundle):
    path=tmp_path/'db.sqlite3'; d=score_frame(sample(),bundle)
    assert save_batch('a',d,'v1','pilot','Otel A',path)==1
    assert save_batch('a',d,'v1','pilot','Otel A',path)==0
    changed=d.copy(); changed['risk']=.7
    extra=d.copy(); extra['reservation_id']='NEW'
    with pytest.raises(ValueError,match='üzerine'):
        save_batch('a',pd.concat([extra,changed]),'v1','pilot','Otel A',path)
    assert len(load_batch('a',path))==1  # first insert rolls back too
    assert save_batch('b',d,'v1','pilot','Otel B',path)==1
    assert len(collections(path))==2
    assert load_batch('a',path).risk.iloc[0]==pytest.approx(d.risk.iloc[0])

def test_outcomes_keep_prediction_and_isolate_manual(tmp_path,bundle):
    path=tmp_path/'db.sqlite3'; d=score_frame(sample(),bundle)
    save_batch('pilot',d,'v1','pilot','Otel',path)
    save_batch('manual',d,'v1','manual','Deneme',path)
    save_outcome('pilot','ELLE-DENEME','2026-10-16','Geç iptal','2026-10-17',path)
    save_outcome('pilot','ELLE-DENEME','2026-10-16','Konakladı','2026-10-17',path)
    assert outcomes('pilot',path).outcome.iloc[0]=='Konakladı'
    exported=json.loads(export_collection('pilot',path))['data']
    assert len(exported['outcome_events'])==2
    assert len(exported['snapshots'])==1
    assert load_batch('pilot',path).risk.iloc[0]==pytest.approx(d.risk.iloc[0])
    with pytest.raises(ValueError): save_outcome('manual','ELLE-DENEME','2026-10-16','Konakladı','2026-10-17',path)
    with pytest.raises(ValueError): save_outcome('pilot','ELLE-DENEME','2026-10-16','Konakladı','2026-10-15',path)
    with pytest.raises(ValueError): save_outcome('pilot','ELLE-DENEME','2026-10-16','Konakladı',date.today()+timedelta(days=1),path)

def test_export_neutralizes_spreadsheet_formulas():
    d=pd.DataFrame({'note':['=1+1',' @SUM(A1:A2)','normal'],'risk':[.01,.02,.03]})
    read=pd.read_csv(io.BytesIO(csv_bytes(d)))
    assert read.note.iloc[0].startswith("'")
    assert read.note.iloc[1].startswith("'")
    assert read.risk.iloc[0]==.01

def test_fingerprint_consistent_across_column_ordering():
    d = sample()
    d_reversed = d[list(reversed(d.columns))]
    assert fingerprint(d) == fingerprint(d_reversed)

def test_model_joblib_matches_sha256():
    import hashlib
    sha_expected = (ROOT / 'artifacts/model.sha256').read_text().strip()
    sha_actual = hashlib.sha256((ROOT / 'artifacts/model.joblib').read_bytes()).hexdigest()
    assert sha_actual == sha_expected

def test_model_meaningful_probability_spread(bundle):
    # Short lead time + Corporate vs Long lead time + Online TA
    low_risk_booking = reservation('2026-10-20', '2026-10-22', '2026-10-18', 'City Hotel', 1, 0, 0, 'BB', 'Corporate', 'Corporate', 'A', 'Transient')
    high_risk_booking = reservation('2026-10-20', '2026-10-22', '2025-10-20', 'City Hotel', 2, 0, 0, 'BB', 'Online TA', 'TA/TO', 'A', 'Transient')
    p_low = score_frame(low_risk_booking, bundle).risk.iloc[0]
    p_high = score_frame(high_risk_booking, bundle).risk.iloc[0]
    # Check that predictions span a meaningful range rather than being stuck at 2%
    assert p_high > p_low
    assert p_high > 0.40
    assert p_low < 0.35



