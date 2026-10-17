from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'

def test_pages_render():
    at=AppTest.from_file(str(APP),default_timeout=60).run()
    assert not at.exception
    assert len(at.metric)==4
    for page in ['Bir rezervasyon dene','Rezervasyon takibi','Dosya yükle','Kayıtlar ve sonuçlar','Model ve veri','Kullanım rehberi']:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page

def test_empty_active_state():
    at=AppTest.from_file(str(APP),default_timeout=60).run()
    at.sidebar.radio[0].set_value('Rezervasyon takibi').run()
    at.radio[0].set_value('Yüklenen aktif dosya').run()
    assert not at.exception
    assert any('Önce Dosya' in i.value for i in at.info)

def test_save_form_and_reload(tmp_path,monkeypatch):
    import hotel.store as store
    original=store.connect
    monkeypatch.setattr(store,'connect',lambda path=None: original(tmp_path/'ui.sqlite3'))
    at=AppTest.from_file(str(APP),default_timeout=60).run()
    at.sidebar.radio[0].set_value('Rezervasyon takibi').run()
    rid=next(s.value for s in at.selectbox if s.label=='Rezervasyon')
    next(s for s in at.selectbox if s.label=='Durum').set_value('Teyit edildi')
    at.text_area[0].set_value('Test notu')
    next(b for b in at.button if b.label=='Takibi kaydet').click().run()
    assert not at.exception
    assert store.read('demo-v1')[rid]['note']=='Test notu'
    assert store.read('demo-v1')[rid]['status']=='Teyit edildi'
    at.checkbox[0].uncheck().run()
    assert rid in next(s.options for s in at.selectbox if s.label=='Rezervasyon')

def test_manual_predict_change_save_and_restore(tmp_path,monkeypatch):
    import hotel.store as store
    original=store.connect
    monkeypatch.setattr(store,'connect',lambda path=None: original(tmp_path/'manual-ui.sqlite3'))
    at=AppTest.from_file(str(APP),default_timeout=60).run()
    at.sidebar.radio[0].set_value('Bir rezervasyon dene').run()
    at.button(key='manual_predict').click().run()
    assert not at.exception
    assert len(at.metric)==2
    # When beats_constant_brier is True, no constant-rate warning is shown
    import json
    report_data = json.loads((Path(__file__).resolve().parents[1]/'artifacts/report.json').read_text())
    if not report_data.get('beats_constant_brier', True):
        assert any('sabit oran' in w.value for w in at.warning)
    else:
        assert not any('sabit oran' in w.value for w in at.warning)
    risk=at.session_state.manual_result['risk']
    from datetime import timedelta
    old=at.date_input(key='manual_booked').value
    at.date_input(key='manual_booked').set_value(old-timedelta(days=120)).run()
    assert len(at.metric)==0
    assert any('değiştirdin' in x.value for x in at.info)
    at.button(key='manual_predict').click().run()
    assert not at.exception
    assert at.session_state.manual_previous['risk']==risk
    at.button(key='manual_save').click().run()
    assert not at.exception
    assert len(store.load_batch('manual-v1'))==1
    at.sidebar.radio[0].set_value('Kayıtlar ve sonuçlar').run()
    assert not at.exception
    assert any('senin girdiğin denemeler' in x.value for x in at.info)

def test_manual_validation():
    from datetime import timedelta
    at=AppTest.from_file(str(APP),default_timeout=60).run()
    at.sidebar.radio[0].set_value('Bir rezervasyon dene').run()
    arrival=at.date_input(key='manual_arrival').value
    at.date_input(key='manual_departure').set_value(arrival-timedelta(days=1)).run()
    assert at.error
    assert len(at.button)==0

def test_pilot_save_track_and_outcome(tmp_path,monkeypatch):
    import io
    import joblib
    import hotel.store as store
    from hotel.scenario import reservation
    from hotel.ingest import score_file
    from hotel.data import ROOT
    original=store.connect
    monkeypatch.setattr(store,'connect',lambda path=None: original(tmp_path/'pilot-ui.sqlite3'))
    model=joblib.load(ROOT/'artifacts/model.joblib')
    raw=reservation('2026-10-17','2026-10-19','2026-10-01','City Hotel',2,0,0,'BB','Online TA','TA/TO','A','Transient')
    scored=score_file(io.StringIO(raw.to_csv(index=False)),'pilot.csv',model)
    at=AppTest.from_file(str(APP),default_timeout=60).run()
    at.session_state.active_data=scored
    at.session_state.active_namespace='pilot-ui-test'
    at.session_state.active_label='Test tesisi'
    at.sidebar.radio[0].set_value('Dosya yükle').run()
    at.button(key='persist_upload').click().run()
    assert not at.exception
    assert len(store.load_batch('pilot-ui-test'))==1
    at.sidebar.radio[0].set_value('Kayıtlar ve sonuçlar').run()
    assert not at.exception
    next(s for s in at.selectbox if s.label=='Gerçekte ne oldu?').set_value('Gelmedi')
    next(b for b in at.button if b.label=='Gerçekleşen sonucu kaydet').click().run()
    assert not at.exception
    assert store.outcomes('pilot-ui-test').outcome.iloc[0]=='Gelmedi'
    assert any('Henüz iki farklı sonuç' in x.value for x in at.caption)
    at.sidebar.radio[0].set_value('Rezervasyon takibi').run()
    at.radio[0].set_value('Kaydedilmiş rezervasyonlar').run()
    assert not at.exception
    assert at.metric[0].value=='1'
