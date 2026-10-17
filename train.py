"""Reproduce the fixed chronological experiment: python train.py."""
import json
import hashlib
import platform
import joblib
import sklearn
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.inspection import permutation_importance
from hotel.data import ROOT,SOURCE,FEATURES,load_history,temporal_split
from hotel.model import candidates,metrics,queue_metrics,reliability

def run():
    out=ROOT/'artifacts'; out.mkdir(exist_ok=True)
    raw,cohort,audit=load_history()
    splits=temporal_split(cohort)
    tr,va,ca,te=[splits[k] for k in ['train','validation','calibration','test']]
    results={}; fitted={}
    for name,model in candidates().items():
        print('Eğitiliyor:',name,flush=True)
        model.fit(tr[FEATURES],tr.is_canceled)
        p=model.predict_proba(va[FEATURES])[:,1]
        results[name]={'validation':metrics(va.is_canceled,p)}
        fitted[name]=model
    # Prespecified selection: validation AP, then Brier. Test does not choose model.
    winner=max(results,key=lambda n:(results[n]['validation']['average_precision'],-results[n]['validation']['brier']))
    selected=CalibratedClassifierCV(FrozenEstimator(fitted[winner]),method='sigmoid')
    selected.fit(ca[FEATURES],ca.is_canceled)
    print('Doğrulamada seçilen:',winner,flush=True)
    for name,model in fitted.items():
        results[name]['test']=metrics(te.is_canceled,model.predict_proba(te[FEATURES])[:,1])
    p=selected.predict_proba(te[FEATURES])[:,1]
    test_result=metrics(te.is_canceled,p)
    predictions=te[['reservation_id','hotel','arrival_date','decision_date','market_segment','reserved_room_type','lead_time','adults','children','babies','is_canceled']].copy()
    predictions['risk']=p
    predictions.to_csv(out/'test_predictions.csv',index=False)
    # Exact-record collapse is a sensitivity check, not a claim duplicates are errors.
    unique=~te[list(raw.columns.difference(['arrival_date','outcome_date','decision_date','booking_date','arrival_month','arrival_weekday','reservation_id']))].duplicated()
    pi=permutation_importance(selected,te[FEATURES],te.is_canceled,scoring='average_precision',n_repeats=3,random_state=42,n_jobs=1)
    importance=sorted([{'feature':f,'ap_decrease':float(m),'std':float(s)} for f,m,s in zip(FEATURES,pi.importances_mean,pi.importances_std)],key=lambda x:-x['ap_decrease'])
    # Day-block bootstrap preserves within-day dependence, not unseen-hotel uncertainty.
    rng=np.random.default_rng(42); days=te.decision_date.unique(); draws=[]
    day_indices=[np.flatnonzero(te.decision_date.eq(day).to_numpy()) for day in days]
    for _ in range(200):
        idx=np.concatenate([day_indices[i] for i in rng.integers(0,len(days),len(days))])
        draws.append(metrics(te.is_canceled.to_numpy()[idx],p[idx])['average_precision'])
    report={'audit':audit,'target':'Rezervasyon oluşturulduğu anda müşterinin ileride rezervasyonunu iptal etme olasılığı',
       'prediction_time':'Rezervasyon oluşturulma anı (booking_date)','features':FEATURES,'selection_rule':'Validation average precision, tie: lower Brier; sigmoid calibration on separate 2016 Q4',
       'selected':winner,'versions':{'python':platform.python_version(),'sklearn':sklearn.__version__,'pandas':pd.__version__,'numpy':np.__version__},
       'splits':{k:{'rows':len(v),'events':int(v.is_canceled.sum()),'start':str(v.arrival_date.min().date()),'end':str(v.arrival_date.max().date()),'last_outcome':str(v.outcome_date.max().date())} for k,v in splits.items()},
       'candidates':results,'selected_calibrated_test':test_result,'ap_day_bootstrap_95':np.quantile(draws,[.025,.975]).tolist(),
       'daily_queue':[queue_metrics(te,p,k) for k in [10,20]],'calibration':reliability(te.is_canceled,p),
       'unique_record_sensitivity':metrics(te.is_canceled.loc[unique],p[unique]),'permutation_importance':importance,
       'by_hotel':{h:metrics(te.is_canceled.loc[te.hotel.eq(h)],p[te.hotel.eq(h)]) for h in te.hotel.unique()},
       'limitations':['Retrospective snapshot; field timestamps cannot be fully verified.',
                      'Two Portuguese hotels, 2015–2017. No real hotel prospective validation.',
                      'Exact duplicate rows retained; no booking/group IDs.',
                      'Public snapshot does not measure causal effect of contacting guests.']}
    report['beats_constant_brier']=test_result['brier']<results['Genel oran']['test']['brier']
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    bundle={'model':selected,'features':FEATURES,'source_sha256':audit['sha256'],'selected':winner,
            'categories':{c:sorted(tr[c].dropna().unique().tolist()) for c in ['meal','market_segment','distribution_channel','reserved_room_type','customer_type']}}
    tmp_model=out/'model.joblib.tmp'
    tmp_sha=out/'model.sha256.tmp'
    joblib.dump(bundle,tmp_model)
    digest=hashlib.sha256(tmp_model.read_bytes()).hexdigest()
    tmp_sha.write_text(digest)
    tmp_model.replace(out/'model.joblib')
    tmp_sha.replace(out/'model.sha256')
    print(json.dumps({'selected':winner,'test':test_result,'queue':report['daily_queue']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    run()
