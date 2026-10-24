"""Generate a standalone, readable report from executed metrics; no training."""
from html import escape
import json
from hotel.data import ROOT

def table(rows,headers):
    return '<table><thead><tr>'+''.join('<th>'+escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'

def build():
    r=json.loads((ROOT/'artifacts/report.json').read_text())
    rows=[]
    for name,entry in r['candidates'].items():
        t=entry['test']; rows.append([name,f"{entry['validation']['average_precision']:.4f}",f"%{100*t.get('accuracy',0):.2f}",f"{t['average_precision']:.4f}",f"{t['roc_auc']:.3f}",f"{t['brier']:.6f}"])
    t=r['selected_calibrated_test']
    rows.append([r['selected']+' (Tam Geçmiş)','Ayrı dönem',f"%{100*t.get('accuracy',0):.2f}",f"{t['average_precision']:.4f}",f"{t['roc_auc']:.3f}",f"{t['brier']:.6f}"])
    if 'academic_benchmark' in r:
        ab=r['academic_benchmark']
        rows.append([r['selected']+' (Akademik Standart Split)','Stratified %20',f"%{100*ab.get('accuracy',0):.2f}",f"{ab['average_precision']:.4f}",f"{ab['roc_auc']:.3f}",f"{ab['brier']:.6f}"])
    content='<h1>Otel Rezervasyon Risk ve Takip Asistanı</h1><p>Çalıştırılmış deney raporu · Yerel akademik sürüm 2.0</p>'
    content+='<h2>Araştırma sorusu</h2><p>Gelişten bir gün önce gün sonunda hâlâ aktif olan rezervasyonlardan hangilerinde daha sonra iptal veya no-show gerçekleşir? Otelin sınırlı inceleme kapasitesini bu sıralamaya göre kullanmasını değerlendiriyoruz.</p>'
    content+='<h2>Zaman ayrımı</h2>'+table([[k,v['rows'],v['events'],v['start'],v['end']] for k,v in r['splits'].items()],['Bölüm','Kayıt','Olay','Başlangıç','Bitiş'])
    content+='<p>Eğitim, doğrulama ve kalibrasyon etiketlerinin bir sonraki dönemden önce bilinmesi şarttır. Model seçimi test setine bakmadan doğrulama AP değerine göre yapılır.</p>'
    content+='<h2>Karşılaştırma</h2>'+table(rows,['Model','Doğrulama AP','Test Doğruluk','Test AP','Test AUC','Test Brier'])
    content+='<p>AP ve AUC yüksek, Brier düşük olduğunda daha iyidir. Brier yalnız kalibrasyonu değil ayrıştırmayı da yansıtır. Modelin test Brier hatası sabit genel oran referansını '+('geçmiştir.' if r['beats_constant_brier'] else 'geçememiştir. Bu sınırlama ürün ekranlarında gösterilir.')+'</p>'
    content+='<h2>Günlük inceleme kapasitesi</h2>'+table([[q['capacity_per_hotel_day'],q['reviewed'],q['found_events'],f"{q['random_expected_events']:.1f}",f"{q['lift_over_random']:.2f}"] for q in r['daily_queue']],['Otel/gün kapasite','İncelenen','Bulunan olay','Rastgele beklenti','Oran'])
    content+='<p>Sayılar tüm test döneminin toplamıdır. Listede bulmak, iletişim kurarak iptali önlemek anlamına gelmez.</p>'
    content+='<h2>Kalibrasyon grupları</h2>'+table([[f"{c['predicted']:.2%}",f"{c['actual']:.2%}",c['count']] for c in r['calibration']],['Ortalama tahmin','Gerçek olay oranı','Kayıt'])
    content+='<h2>Sınırlar ve duyarlılık</h2><p>İki Portekiz oteli, 2015–2017. Snapshot değişkenlerinin her birinin zaman damgası doğrulanamaz. Tekrarlanan satırlar gerçek grup rezervasyonları olabilir; ana deneyde korunur. Tekilleştirilmiş testte AP '+f"{r['unique_record_sensitivity']['average_precision']:.4f}"+', AUC '+f"{r['unique_record_sensitivity']['roc_auc']:.3f}"+'. Gün bloklarıyla 200 bootstrap AP %95 aralığı '+str([round(x,4) for x in r['ap_day_bootstrap_95']])+'. Bu aralık yeni otelde genelleme belirsizliğini kapsamaz.</p>'
    content+='<h2>Tekrar üretme</h2><p>Python 3.12 ortamında requirements.txt bağımlılıklarını kurun. python train.py modeli ve ölçümleri, python rapor.py bu raporu üretir. python -m pytest -q kontrolleri çalıştırır. Test sonrası yeni model seçilmemiştir.</p><p>Veri SHA-256: <code>'+escape(r['audit']['sha256'])+'</code></p>'
    content+='<h2>Kaynak</h2><p>Antonio, Almeida ve Nunes (2019), Hotel Booking Demand datasets, Data in Brief 22, 41–49. CC BY 4.0. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/">Makale</a> · <a href="https://github.com/rfordatascience/tidytuesday/tree/master/data/2020/2020-02-11">Birleştirilmiş veri</a>.</p>'
    html='<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Otel ML deney raporu</title><style>body{font:16px/1.65 system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#183142}h1,h2{color:#116d63}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border:1px solid #d5e0e5;text-align:left}th{background:#edf5f2}code{overflow-wrap:anywhere}@media print{body{margin:0}tr{break-inside:avoid}h2{break-after:avoid}}</style><body>'+content+'</body></html>'
    path=ROOT/'artifacts/deney-raporu.html'; path.write_text(html)
    print(path); return path

if __name__=='__main__': build()
