"""Package a reproducible local project, excluding private runtime records."""
import hashlib
import json
import zipfile
from hotel.data import ROOT

def build():
    allowed=['app.py','train.py','rapor.py','paketle.py','yedekle.py','Baslat.command','requirements.txt','README.md','KULLANIM.md','SONUCLAR.md','TESLIM.md','.gitignore','.streamlit/config.toml',
        'data/hotel_bookings.csv','artifacts/report.json','artifacts/model.joblib','artifacts/model.sha256','artifacts/test_predictions.csv','artifacts/test-results.txt','artifacts/deney-raporu.html','artifacts/elle-deneme.png']
    files=[ROOT/name for name in allowed]
    files+=sorted((ROOT/'hotel').glob('*.py'))+sorted((ROOT/'tests').glob('*.py'))
    missing=[str(p.relative_to(ROOT)) for p in files if not p.is_file()]
    if missing: raise RuntimeError('Paket eksikleri: '+', '.join(missing))
    path=ROOT/'Otel-Risk-Asistani-v1.zip'
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p,'Otel-Risk-Asistani/'+str(p.relative_to(ROOT)))
        z.writestr('Otel-Risk-Asistani/MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert not any('.sqlite3' in name or '/.venv/' in name or '/backups/' in name for name in z.namelist())
    print(f'{path} ({path.stat().st_size:,} bayt; {len(files)} dosya + manifest)')
    return path

if __name__=='__main__': build()
