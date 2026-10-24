from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'hotel_bookings.csv'
MONTHS = dict(zip(['January','February','March','April','May','June','July','August','September','October','November','December'], range(1,13)))
NUM = ['lead_time','arrival_month','arrival_weekday','stays_in_weekend_nights','stays_in_week_nights','adults','children','babies',
       'is_repeated_guest','previous_cancellations','previous_bookings_not_canceled','booking_changes','days_in_waiting_list',
       'adr','required_car_parking_spaces','total_of_special_requests','room_mismatch','total_nights','total_guests','prev_cancel_ratio']
CAT = ['hotel','meal','market_segment','distribution_channel','reserved_room_type','assigned_room_type','deposit_type','customer_type','country','agent']
FEATURES = NUM + CAT
CORE_NUM = ['lead_time','arrival_month','arrival_weekday','stays_in_weekend_nights','stays_in_week_nights','adults','children','babies']
CORE_CAT = ['hotel','meal','market_segment','distribution_channel','reserved_room_type','customer_type']
FORBIDDEN = ['is_canceled','reservation_status','reservation_status_date']

def _enrich_features(d):
    defaults_num = {
        'is_repeated_guest': 0,
        'previous_cancellations': 0,
        'previous_bookings_not_canceled': 0,
        'booking_changes': 0,
        'days_in_waiting_list': 0,
        'adr': 100.0,
        'required_car_parking_spaces': 0,
        'total_of_special_requests': 0,
    }
    for col, val in defaults_num.items():
        if col not in d:
            d[col] = val
        else:
            d[col] = pd.to_numeric(d[col], errors='coerce').fillna(val)
    if 'assigned_room_type' not in d:
        d['assigned_room_type'] = d['reserved_room_type']
    else:
        d['assigned_room_type'] = d['assigned_room_type'].fillna(d['reserved_room_type']).astype(str)
    if 'deposit_type' not in d:
        d['deposit_type'] = 'No Deposit'
    else:
        d['deposit_type'] = d['deposit_type'].fillna('No Deposit').astype(str)
    if 'country' not in d:
        d['country'] = 'PRT'
    else:
        d['country'] = d['country'].fillna('Unknown').astype(str)
    if 'agent' not in d:
        d['agent'] = '9.0'
    else:
        d['agent'] = d['agent'].fillna('Unknown').astype(str)
    d['room_mismatch'] = (d['reserved_room_type'].astype(str) != d['assigned_room_type'].astype(str)).astype(int)
    d['total_nights'] = d['stays_in_weekend_nights'] + d['stays_in_week_nights']
    d['total_guests'] = d['adults'].fillna(0) + d['children'].fillna(0) + d['babies'].fillna(0)
    d['prev_cancel_ratio'] = d['previous_cancellations'] / (d['previous_cancellations'] + d['previous_bookings_not_canceled'] + 1.0)
    return d

def load_history(path=SOURCE):
    raw = pd.read_csv(path)
    required = set(CORE_NUM + CORE_CAT + ['is_canceled','reservation_status','reservation_status_date','arrival_date_year','arrival_date_month','arrival_date_day_of_month']) - {'arrival_month','arrival_weekday'}
    missing = required - set(raw)
    if missing:
        raise ValueError('Eksik sütunlar: ' + ', '.join(sorted(missing)))
    d = raw.copy()
    d['arrival_date'] = pd.to_datetime(dict(year=d.arrival_date_year, month=d.arrival_date_month.map(MONTHS), day=d.arrival_date_day_of_month), errors='coerce')
    d['outcome_date'] = pd.to_datetime(d.reservation_status_date, errors='coerce')
    d['decision_date'] = d.arrival_date - np.timedelta64(1,'D')
    d['booking_date'] = d.arrival_date - pd.to_timedelta(d.lead_time, unit='D')
    d['arrival_month'] = d.arrival_date.dt.month
    d['arrival_weekday'] = d.arrival_date.dt.dayofweek
    d['reservation_id'] = ['DEMO-' + str(i+1).zfill(6) for i in range(len(d))]
    d = _enrich_features(d)
    valid = (d.arrival_date.notna() & d.outcome_date.notna() & d.is_canceled.isin([0,1])
        & (d.adults.fillna(0)+d.children.fillna(0)+d.babies.fillna(0)>0)
        & (d.stays_in_weekend_nights+d.stays_in_week_nights>0)
        & d.lead_time.ge(0))
    for c in ['adults','children','babies','stays_in_weekend_nights','stays_in_week_nights']:
        valid &= d[c].isna() | d[c].ge(0)
    consistent = ((d.is_canceled.eq(0) & d.reservation_status.eq('Check-Out') & d.outcome_date.ge(d.arrival_date))
                  | (d.is_canceled.eq(1) & d.reservation_status.isin(['Canceled','No-Show'])))
    valid &= consistent
    audit = {'rows':len(raw),'columns':len(raw.columns),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
             'exact_duplicate_rows':int(raw.duplicated().sum()), 'missing':raw.isna().sum().to_dict(),
             'excluded_invalid':int((~valid).sum()),'cancellation_rate':float(raw.is_canceled.mean()),
             'arrival_start':str(d.arrival_date.min().date()),'arrival_end':str(d.arrival_date.max().date())}
    clean = d.loc[valid].copy()
    cohort = clean.copy()
    audit.update(eligible_rows=len(cohort), excluded_not_active=0, late_event_rate=float(cohort.is_canceled.mean()))
    return d, cohort, audit

def temporal_split(d):
    # Split by arrival_date with strict label maturity before the next split begins.
    return {
        'train':d.loc[(d.arrival_date < '2016-07-01') & (d.outcome_date < '2016-07-01')].copy(),
        'validation':d.loc[d.arrival_date.between('2016-07-01','2016-09-30') & (d.outcome_date < '2016-10-01')].copy(),
        'calibration':d.loc[d.arrival_date.between('2016-10-01','2016-12-31') & (d.outcome_date < '2017-01-01')].copy(),
        'test':d.loc[d.arrival_date >= '2017-01-01'].copy(),
    }

def validate_active(raw):
    """Strict single-hotel active day-before snapshot contract, no outcome columns."""
    required = set(CORE_NUM + CORE_CAT + ['reservation_id','arrival_date','snapshot_date','status']) - {'arrival_month','arrival_weekday'}
    missing = required - set(raw)
    if missing:
        raise ValueError('Eksik sütunlar: ' + ', '.join(sorted(missing)))
    if set(FORBIDDEN) & set(raw):
        raise ValueError('Aktif dosyada sonuç/sonradan oluşan sütunlar bulunamaz: ' + ', '.join(sorted(set(FORBIDDEN)&set(raw))))
    if raw.empty or len(raw)>100000:
        raise ValueError('Dosya 1–100.000 rezervasyon içermeli.')
    d = raw.copy()
    if d.reservation_id.isna().any():
        raise ValueError('Rezervasyon kimlikleri dolu ve benzersiz olmalı.')
    d['reservation_id'] = d.reservation_id.astype(str).str.strip()
    if d.reservation_id.eq('').any() or d.reservation_id.duplicated().any() or d.reservation_id.str.len().gt(120).any():
        raise ValueError('Rezervasyon kimlikleri dolu ve benzersiz olmalı.')
    d['reservation_id'] = d.reservation_id.astype(str)
    for c in ['arrival_date','snapshot_date']:
        d[c] = pd.to_datetime(d[c], errors='coerce')
        if d[c].isna().any() or not d[c].eq(d[c].dt.normalize()).all():
            raise ValueError(c + ': YYYY-MM-DD biçiminde geçerli günler gerekli.')
    if d.snapshot_date.nunique()!=1 or not (d.arrival_date-d.snapshot_date).eq(np.timedelta64(1,'D')).all():
        raise ValueError('Tek bir snapshot_date ve bu tarihten bir gün sonraki gelişler gerekli.')
    if not d.status.eq('active').all():
        raise ValueError('Yalnızca status=active rezervasyonlar kabul edilir.')
    for c in CORE_NUM:
        if c in ['arrival_month','arrival_weekday']:
            continue
        d[c] = pd.to_numeric(d[c], errors='coerce')
        if d[c].isna().any() or not np.isfinite(d[c]).all() or d[c].lt(0).any() or d[c].mod(1).ne(0).any():
            raise ValueError(c + ': eksiksiz, negatif olmayan tam sayılar gerekli.')
    if d.lead_time.lt(1).any() or (d.adults+d.children+d.babies).le(0).any() or (d.stays_in_weekend_nights+d.stays_in_week_nights).le(0).any():
        raise ValueError('En az bir gün önceden yapılmış, misafir ve gece sayısı pozitif rezervasyonlar gerekli.')
    for c in CORE_CAT:
        if d[c].isna().any() or d[c].astype(str).str.strip().eq('').any():
            raise ValueError(c + ': boş değer bulunamaz.')
    if not d.hotel.isin(['City Hotel','Resort Hotel']).all():
        raise ValueError('hotel alanı City Hotel veya Resort Hotel olmalı; tesis adını bu alana yazmayın.')
    if d.hotel.nunique()!=1:
        raise ValueError('Her dosyada yalnız bir tesis türü bulunmalı.')
    d['arrival_month'] = d.arrival_date.dt.month
    d['arrival_weekday'] = d.arrival_date.dt.dayofweek
    d['decision_date'] = d.snapshot_date
    d = _enrich_features(d)
    return d
