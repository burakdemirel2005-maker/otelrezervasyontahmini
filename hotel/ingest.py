import pandas as pd
import zipfile
from .data import validate_active, FEATURES

def score_frame(raw, bundle):
    d=validate_active(raw)
    unknown={c:sorted(set(d[c])-set(vals)) for c,vals in bundle['categories'].items() if set(d[c])-set(vals)}
    if unknown:
        raise ValueError('Eğitimde olmayan kodlar var. Veri eşlemesi gerekli: '+str(unknown))
    d['risk']=bundle['model'].predict_proba(d[FEATURES])[:,1]
    return d

def score_file(file, filename, bundle):
    if filename.lower().endswith('.csv'):
        raw=pd.read_csv(file,dtype={'reservation_id':str},nrows=100001)
    elif filename.lower().endswith('.xlsx'):
        with zipfile.ZipFile(file) as archive:
            if sum(info.file_size for info in archive.infolist())>100*1024*1024:
                raise ValueError('Excel dosyasının açılmış boyutu 100 MB sınırını aşıyor.')
        file.seek(0)
        raw=pd.read_excel(file,dtype={'reservation_id':str},nrows=100001)
    else:
        raise ValueError('Yalnız CSV ve XLSX desteklenir.')
    return score_frame(raw,bundle)
