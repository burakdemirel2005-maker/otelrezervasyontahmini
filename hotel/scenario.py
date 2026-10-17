"""Human-readable manual input, using the same contract as file ingestion."""
import hashlib
import json
from datetime import timedelta
import pandas as pd

LABELS={
    'hotel':{'City Hotel':'Şehir oteli','Resort Hotel':'Tatil oteli'},
    'meal':{'BB':'Kahvaltı dahil','HB':'Yarım pansiyon','FB':'Tam pansiyon','SC':'Yemek dahil değil','Undefined':'Belirtilmemiş'},
    'market_segment':{'Online TA':'Çevrim içi seyahat acentesi','Offline TA/TO':'Acente / tur operatörü (çevrim dışı)','Direct':'Doğrudan otelden','Corporate':'Kurumsal rezervasyon','Groups':'Grup rezervasyonu','Complementary':'Ücretsiz / ikram konaklama','Aviation':'Havayolu şirketi'},
    'distribution_channel':{'TA/TO':'Acente veya tur operatörü','Direct':'Doğrudan otel','Corporate':'Kurumsal kanal','GDS':'Global dağıtım sistemi (GDS)','Undefined':'Bilinmiyor'},
    'customer_type':{'Transient':'Bireysel, gruba bağlı değil','Transient-Party':'Başka bireysel rezervasyonlarla bağlantılı','Group':'Grubun parçası','Contract':'Sözleşmeli müşteri'},
}
FIELDS={'hotel':'Otel türü','arrival_date':'Giriş günü','lead_time':'Kaç gün önceden rezervasyon',
    'stays_in_weekend_nights':'Hafta sonu gecesi','stays_in_week_nights':'Hafta içi gecesi','adults':'Yetişkin','children':'Çocuk','babies':'Bebek',
    'meal':'Yemek planı','market_segment':'Müşteri grubu','distribution_channel':'Satış kanalı','reserved_room_type':'Oda kodu','customer_type':'Rezervasyon türü'}

def label(field,value):
    return LABELS.get(field,{}).get(value,value)

def reservation(arrival,departure,booked,hotel,adults,children,babies,meal,market_segment,distribution_channel,reserved_room_type,customer_type):
    arrival,departure,booked=[pd.Timestamp(x).normalize() for x in (arrival,departure,booked)]
    nights=(departure-arrival).days
    if not 1<=nights<=365:
        raise ValueError('Çıkış, girişten sonra olmalı. Bu deneme ekranında en fazla 365 gece kabul edilir.')
    lead=(arrival-booked).days
    if not 1<=lead<=1000:
        raise ValueError('Rezervasyon, girişten en az 1 ve en fazla 1.000 gün önce yapılmış olmalı.')
    weekend=int((pd.date_range(arrival,periods=nights).dayofweek>=5).sum())
    return pd.DataFrame([{'reservation_id':'ELLE-DENEME','arrival_date':arrival,'snapshot_date':arrival.date()-timedelta(days=1),
        'status':'active','hotel':hotel,'lead_time':lead,'stays_in_weekend_nights':weekend,'stays_in_week_nights':nights-weekend,
        'adults':adults,'children':children,'babies':babies,'meal':meal,'market_segment':market_segment,
        'distribution_channel':distribution_channel,'reserved_room_type':reserved_room_type,'customer_type':customer_type}])

def fingerprint(frame):
    # A changed answer invalidates the displayed prediction until recalculation.
    records = json.loads(frame.to_json(orient='records', date_format='iso'))
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()

def csv_bytes(frame):
    d=frame.copy()
    for c in d.select_dtypes(include=['object','string']).columns:
        d[c]=d[c].map(lambda v: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v)
    return d.to_csv(index=False).encode('utf-8-sig')
