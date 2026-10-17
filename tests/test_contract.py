import numpy as np
import pandas as pd
import pytest
from hotel.data import load_history,temporal_split,FEATURES,FORBIDDEN,validate_active
from hotel.model import queue_metrics
from hotel.store import save,read

@pytest.fixture(scope='module')
def history():
    return load_history()

def active_row():
    return pd.DataFrame([dict(reservation_id='001',arrival_date='2026-10-19',snapshot_date='2026-10-18',status='active',hotel='City Hotel',lead_time=10,stays_in_weekend_nights=0,stays_in_week_nights=2,adults=2,children=0,babies=0,meal='BB',market_segment='Online TA',distribution_channel='TA/TO',reserved_room_type='A',customer_type='Transient')])

def test_no_outcome_features():
    assert not set(FEATURES)&set(FORBIDDEN)

def test_cohort_and_dates(history):
    raw,cohort,audit=history
    assert len(raw)==119390
    assert not cohort.reservation_id.duplicated().any()
    splits=temporal_split(cohort)
    for before,after in zip(['train','validation','calibration'],['validation','calibration','test']):
        assert splits[before].arrival_date.max()<splits[after].arrival_date.min()
        assert splits[before].outcome_date.max()<splits[after].arrival_date.min()
        assert set(splits[before].reservation_id).isdisjoint(splits[after].reservation_id)

def test_active_valid():
    d=validate_active(active_row())
    assert d.reservation_id.iloc[0]=='001'
    assert d.arrival_month.iloc[0]==10

@pytest.mark.parametrize('column,value',[('lead_time',0),('lead_time',np.inf),('adults',-1),('adults',1.5),('snapshot_date','2026-10-17'),('status','canceled'),('reservation_id',''),('meal',''),('hotel','My Hotel')])
def test_bad_upload_rejected(column,value):
    d=active_row(); d[column]=value
    with pytest.raises(ValueError): validate_active(d)

def test_duplicate_ids_rejected():
    d=pd.concat([active_row(),active_row()])
    with pytest.raises(ValueError): validate_active(d)

def test_whitespace_ids_and_mixed_hotels_rejected():
    d=pd.concat([active_row(),active_row()],ignore_index=True)
    d.loc[1,'reservation_id']=' 001 '
    with pytest.raises(ValueError): validate_active(d)
    d.loc[1,'reservation_id']='002'; d.loc[1,'hotel']='Resort Hotel'
    with pytest.raises(ValueError,match='tesis türü'): validate_active(d)

def test_outcome_upload_rejected():
    d=active_row(); d['is_canceled']=1
    with pytest.raises(ValueError): validate_active(d)

def test_queue_daily_capacity_and_ties():
    d=pd.DataFrame({'hotel':['A']*3+['B']*2,'decision_date':['2017-01-01']*5,'reservation_id':['3','2','1','4','5'],'is_canceled':[1,0,0,1,0]})
    result=queue_metrics(d,np.ones(5),1)
    assert result['reviewed']==2
    assert result['found_events']==1
    assert result['random_expected_events']==pytest.approx(1/3+1/2)

def test_tracking_persists_and_isolates(tmp_path):
    db=tmp_path/'test.sqlite3'
    save('demo','1','Teyit edildi','ilk not',db)
    save('pilot','1','Ulaşılamadı','başka tesis',db)
    save('demo','1','İncelendi','son not',db)
    assert read('demo',db)['1']['note']=='son not'
    assert read('pilot',db)['1']['status']=='Ulaşılamadı'
    with pytest.raises(ValueError): save('demo','1','yanlış','',db)

def test_csv_ingestion_and_scoring():
    import io
    import joblib
    from hotel.data import ROOT
    from hotel.ingest import score_file
    bundle=joblib.load(ROOT/'artifacts/model.joblib')
    d=score_file(io.StringIO(active_row().to_csv(index=False)),'test.csv',bundle)
    assert d.reservation_id.iloc[0]=='001'
    assert d.risk.between(0,1).all()
    wrong=active_row(); wrong['meal']='UNKNOWN-MEAL'
    with pytest.raises(ValueError,match='kodlar'):
        score_file(io.StringIO(wrong.to_csv(index=False)),'test.csv',bundle)

def test_excel_ingestion_and_scoring(tmp_path):
    import joblib
    from openpyxl import Workbook
    from hotel.data import ROOT
    from hotel.ingest import score_file
    # Minimal disposable test fixture, not a delivered spreadsheet artifact.
    frame=active_row(); wb=Workbook(); ws=wb.active
    ws.append(frame.columns.tolist()); ws.append(frame.iloc[0].tolist())
    path=tmp_path/'test.xlsx'; wb.save(path)
    bundle=joblib.load(ROOT/'artifacts/model.joblib')
    with path.open('rb') as file: d=score_file(file,path.name,bundle)
    assert d.reservation_id.iloc[0]=='001'
    assert d.risk.between(0,1).all()

def test_saved_model_reproduces_test_predictions(history):
    import joblib
    from hotel.data import ROOT
    bundle=joblib.load(ROOT/'artifacts/model.joblib')
    frame=temporal_split(history[1])['test'].sample(100,random_state=7)
    stored=pd.read_csv(ROOT/'artifacts/test_predictions.csv').set_index('reservation_id')
    actual=bundle['model'].predict_proba(frame[FEATURES])[:,1]
    np.testing.assert_allclose(actual,stored.loc[frame.reservation_id,'risk'],atol=1e-12)
