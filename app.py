import hashlib
import json
import joblib
import pandas as pd
import streamlit as st
import altair as alt
from hotel.data import ROOT, load_history
from hotel.store import STATUSES, read, save, save_batch, collections, load_batch
from hotel.ingest import score_file
from hotel.scenario import csv_bytes
from hotel.manual_ui import render as render_manual
from hotel.records_ui import render as render_records

st.set_page_config(page_title='Otel Risk Asistanı',page_icon='🏨',layout='wide')
st.markdown('''<style>
.block-container{padding-top:3rem;padding-bottom:3rem;max-width:1400px}
h1, h2, h3{letter-spacing:-0.5px;font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
[data-testid="stMetric"]{
    background:linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border:1px solid #e2e8f0;
    padding:22px;
    border-radius:14px;
    box-shadow:0 2px 8px rgba(0,0,0,0.03);
    transition:all 0.2s ease-in-out;
}
[data-testid="stMetric"]:hover{
    box-shadow:0 4px 14px rgba(0,0,0,0.07);
    border-color:#cbd5e1;
}
[data-testid="stSidebar"]{
    background-color:#f8fafc;
    border-right:1px solid #e2e8f0;
}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
    border:none;
    border-radius:10px;
    font-weight:600;
    box-shadow:0 2px 6px rgba(13,148,136,0.25);
    transition:all 0.2s;
}
.stButton>button[kind="primary"]:hover{
    background:linear-gradient(135deg, #0f766e 0%, #115e59 100%);
    box-shadow:0 4px 12px rgba(13,148,136,0.35);
}
@media(max-width:1100px){
    [data-testid="stHorizontalBlock"]{flex-wrap:wrap}
    [data-testid="stColumn"]{min-width:240px;flex:1 1 240px}
    [data-testid="stMetricValue"]{font-size:1.8rem}
}
</style>''',unsafe_allow_html=True)

@st.cache_resource
def resources(version):
    model_path=ROOT/'artifacts/model.joblib'
    if hashlib.sha256(model_path.read_bytes()).hexdigest()!=version:
        raise ValueError('Model dosyasının bütünlük kontrolü başarısız. Yeniden eğitim gerekli.')
    return joblib.load(model_path),json.loads((ROOT/'artifacts/report.json').read_text())

@st.cache_data
def history():
    return load_history()[0]

@st.cache_data
def demo_predictions(version):
    return pd.read_csv(ROOT/'artifacts/test_predictions.csv',parse_dates=['arrival_date','decision_date'])

if not all((ROOT/'artifacts'/name).exists() for name in ['report.json','model.joblib','model.sha256','test_predictions.csv']):
    st.info('İlk model hazırlanmalı. Terminalde .venv/bin/python train.py komutunu çalıştırın.')
    st.stop()
model_id=(ROOT/'artifacts/model.sha256').read_text().strip()
try:
    bundle,report=resources(model_id)
except (ValueError,OSError) as exc:
    st.error('Model açılamadı: '+str(exc)); st.stop()
st.sidebar.title('Otel Risk Asistanı')
st.sidebar.caption('Rezervasyonları anla. Takibi planla.')
page=st.sidebar.radio('Çalışma alanı',['Genel bakış','Bir rezervasyon dene','Rezervasyon takibi','Dosya yükle','Kayıtlar ve sonuçlar','Model ve veri','Kullanım rehberi'])
st.sidebar.divider()
st.sidebar.caption('Yerel proje · v1.0\n\n2015–2017 açık verisiyle hazırlanmıştır. Gerçek otel için pilot doğrulaması gerekir.')

if page=='Bir rezervasyon dene':
    render_manual(bundle,report,model_id)
    st.stop()
if page=='Kayıtlar ve sonuçlar':
    render_records()
    st.stop()
if page=='Kullanım rehberi':
    st.title('Nereden başlayayım?')
    st.markdown((ROOT/'KULLANIM.md').read_text())
    st.stop()

if page=='Genel bakış':
    st.caption('GEÇMİŞ REZERVASYON ANALİZİ')
    st.title('Rezervasyonların büyük resmi')
    st.write('İptaller hangi dönemlerde ve kanallarda yoğunlaşıyor?')
    d=history()
    a,b=st.columns([1,2])
    h=a.selectbox('Otel türü',['Tümü','City Hotel','Resort Hotel'])
    date_range=b.date_input('Geliş tarihi aralığı',value=(d.arrival_date.min().date(),d.arrival_date.max().date()),min_value=d.arrival_date.min().date(),max_value=d.arrival_date.max().date())
    if h!='Tümü': d=d[d.hotel.eq(h)]
    if len(date_range)==2: d=d[d.arrival_date.between(pd.Timestamp(date_range[0]),pd.Timestamp(date_range[1]))]
    if d.empty: st.info('Bu aralıkta rezervasyon yok.'); st.stop()
    a,b,c,e=st.columns(4)
    a.metric('Rezervasyon',f'{len(d):,}')
    b.metric('İptal / gelmeme',f'%{100*d.is_canceled.mean():.1f}')
    c.metric('Tamamlanan konaklama',f'{int(d.is_canceled.eq(0).sum()):,}')
    e.metric('Ortalama ön rezervasyon',f'{d.lead_time.mean():.0f} gün')
    st.caption('Burada bütün geçmiş rezervasyonlar bulunur. Modelin hedeflediği geç iptal ve gelmeme grubu daha dardır.')
    left,right=st.columns([1.5,1])
    monthly=d.groupby(d.arrival_date.dt.to_period('M')).agg(Rezervasyon=('is_canceled','size'),İptal_oranı=('is_canceled','mean')).reset_index()
    monthly['Ay']=monthly.arrival_date.astype(str)
    with left:
        st.subheader('Aylık iptal ve gelmeme oranı')
        st.altair_chart(alt.Chart(monthly).mark_line(point=True,color='#147d70').encode(x=alt.X('Ay:N',sort=None),y=alt.Y('İptal_oranı:Q',axis=alt.Axis(format='%'),title='Oran'),tooltip=['Ay','Rezervasyon',alt.Tooltip('İptal_oranı:Q',format='.1%')]),width='stretch')
    with right:
        st.subheader('Rezervasyon kanalları')
        channel=d.groupby('market_segment').is_canceled.agg(['size','mean']).reset_index().rename(columns={'market_segment':'Kanal','size':'Rezervasyon','mean':'İptal oranı'})
        st.dataframe(channel,hide_index=True,width='stretch',column_config={'İptal oranı':st.column_config.NumberColumn(format='percent')})
    st.subheader('Bu bilgiyi nasıl kullanırız?')
    st.write('Geçmiş oranlar, hangi rezervasyonları daha dikkatli inceleyeceğimizi düşünmemize yardımcı olur. Bir kanalda yüksek oran görülmesi, o kanalın iptale neden olduğunu göstermez.')

elif page=='Rezervasyon takibi':
    st.caption('GÜNLÜK ÇALIŞMA LİSTESİ')
    st.title('Önce hangi rezervasyona bakalım?')
    mode=st.radio('Veri kaynağı',['Tarihsel gösterim','Yüklenen aktif dosya','Kaydedilmiş rezervasyonlar'],horizontal=True)
    if mode=='Tarihsel gösterim':
        d=demo_predictions(model_id); namespace='demo-v1'
        st.info('Tarihsel gösterim: gerçek güncel rezervasyon değildir. Skorlar eğitimde kullanılmayan 2017 test döneminden gelir.')
    elif mode=='Yüklenen aktif dosya':
        if 'active_data' not in st.session_state:
            st.info('Önce Dosya yükle bölümünde aktif rezervasyon dosyanı ekle.'); st.stop()
        d=st.session_state.active_data.copy(); namespace=st.session_state.active_namespace
        st.warning('Pilot skoru: bu otelde başarı ve olasılık doğruluğu henüz ölçülmedi. Kayıtlar yüklenen dosyanın anlık görüntüsüdür.')
    else:
        saved=collections()
        if not saved: st.info('Önce bir deneme veya pilot dosyası kaydet.'); st.stop()
        names={x['namespace']:('Elle girilen denemeler' if x['kind']=='manual' else x['label']) for x in saved}
        namespace=st.selectbox('Kayıt grubu',list(names),format_func=lambda x:names[x])
        d=load_batch(namespace)
        st.info('Saklanan tahminler gösteriliyor. Elle girilmiş denemeler gerçek rezervasyon değildir.')
    if not report['beats_constant_brier']:
        st.caption('Olasılık hatası testte sabit oran modelini geçemedi. Bu sürümde sıralamayı inceleme desteği olarak kullanın; tahmini sayılarla kapasite taahhüdü vermeyin.')
    a,b,c=st.columns(3)
    h=a.selectbox('Otel türü',sorted(d.hotel.unique()))
    d=d[d.hotel.eq(h)]
    dates=sorted(d.decision_date.dt.date.unique())
    day=b.selectbox('Takip günü',dates,index=len(dates)-1)
    if mode!='Tarihsel gösterim': namespace=namespace+':'+day.isoformat()
    k=c.selectbox('Günlük inceleme kapasitesi',[10,20,30,50],index=1)
    d=d[d.decision_date.dt.date.eq(day)].sort_values(['risk','reservation_id'],ascending=[False,True]).copy()
    states=read(namespace)
    d['Takip durumu']=[states.get(str(i),{}).get('status','Bekliyor') for i in d.reservation_id]
    d['Not']=[states.get(str(i),{}).get('note','') for i in d.reservation_id]
    a,b,c=st.columns(3)
    a.metric('Yarın gelecek rezervasyon',len(d))
    b.metric('İncelenmemiş',int(d['Takip durumu'].eq('Bekliyor').sum()))
    c.metric('Tahmini geç iptal / gelmeme',f'{d.risk.sum():.1f}')
    st.caption('Son sayı olasılıkların toplamıdır; kesin iptal sayısı veya oda doluluğu değildir.')
    only=st.checkbox('Yalnızca bekleyen kayıtları göster',value=True)
    queue=d[d['Takip durumu'].eq('Bekliyor')].head(k) if only else d.head(k)
    display=queue[['reservation_id','arrival_date','market_segment','reserved_room_type','lead_time','risk','Takip durumu','Not']].rename(columns={'reservation_id':'Rezervasyon','arrival_date':'Geliş','market_segment':'Kanal','reserved_room_type':'Oda tipi','lead_time':'Ön rezervasyon (gün)','risk':'Geç iptal / gelmeme olasılığı'})
    st.dataframe(display,hide_index=True,width='stretch',column_config={'Geç iptal / gelmeme olasılığı':st.column_config.ProgressColumn(format='percent',min_value=0,max_value=1),'Geliş':st.column_config.DateColumn(format='DD.MM.YYYY')})
    st.download_button('Çalışma listesini indir',csv_bytes(display),'takip-listesi.csv','text/csv')
    if queue.empty: st.success('Bu filtrede bekleyen kayıt yok.'); st.stop()
    st.subheader('Takip kaydı ekle')
    rid=st.selectbox('Rezervasyon',queue.reservation_id.tolist())
    current=states.get(str(rid),{})
    with st.form('tracking-'+str(rid)):
        status=st.selectbox('Durum',STATUSES,index=STATUSES.index(current.get('status','Bekliyor')))
        note=st.text_area('Not',value=current.get('note',''),max_chars=2000,placeholder='Örneğin: geliş saati telefonla teyit edildi.')
        if st.form_submit_button('Takibi kaydet',type='primary'):
            save(namespace,rid,status,note); st.rerun()
    if mode=='Tarihsel gösterim':
        with st.expander('Geçmişte gerçekte ne olmuş?'):
            actual=d.loc[d.reservation_id.eq(rid),'is_canceled'].iloc[0]
            st.write('Geç iptal veya gelmeme gerçekleşmiş.' if actual else 'Konaklama tamamlanmış.')
            st.caption('Bu sonuç sıralama veya tahmin girdisi olarak kullanılmaz.')

elif page=='Dosya yükle':
    st.caption('PİLOT VERİ GİRİŞİ')
    st.title('Aktif rezervasyonlarını getir')
    st.write('Tek bir tesisin, gün sonunda hâlâ aktif olan ve ertesi gün gelecek rezervasyonlarını yükle. CSV veya Excel kabul edilir.')
    st.info('Alanlar mevcut eğitim verisinin kodlarıyla eşleşmelidir. Bu sürüm PMS entegrasyonu ve yeni bir otelde doğrulanmış tahmin sunmaz.')
    template=pd.DataFrame([{'reservation_id':'ORNEK-001','arrival_date':'2026-10-19','snapshot_date':'2026-10-18','status':'active','hotel':'City Hotel','lead_time':30,'stays_in_weekend_nights':0,'stays_in_week_nights':2,'adults':2,'children':0,'babies':0,'meal':'BB','market_segment':'Online TA','distribution_channel':'TA/TO','reserved_room_type':'A','customer_type':'Transient'}])
    st.download_button('Örnek CSV şablonunu indir',csv_bytes(template),'aktif-rezervasyon-sablonu.csv','text/csv')
    with st.expander('Alanları nasıl doldurmalıyım?'):
        st.write('reservation_id: tesis içinde değişmeyen benzersiz kimlik. snapshot_date: dosyanın alındığı gün. arrival_date: ertesi gün. status: active. lead_time: rezervasyonun oluşturulması ile geliş arasındaki toplam gün. hotel: tesis türü (City Hotel veya Resort Hotel).')
        st.json(bundle['categories'])
    property_id=st.text_input('Tesis kodu',placeholder='Örneğin: ankara-merkez-01',help='Aynı tesiste her yüklemede aynı kodu kullan. Takip kayıtları bu kod ve rezervasyon kimliğine bağlıdır.')
    uploaded=st.file_uploader('Rezervasyon dosyası',type=['csv','xlsx'])
    attested=st.checkbox('Dosya, belirtilen gün sonundaki aktif rezervasyonları içeriyor; alanlar o anda biliniyordu.')
    if st.button('Dosyayı denetle ve puanla',type='primary',disabled=not(uploaded and property_id.strip() and attested)):
        try:
            d=score_file(uploaded,uploaded.name,bundle)
            st.session_state.active_data=d
            st.session_state.active_namespace='pilot-'+hashlib.sha256(property_id.strip().encode()).hexdigest()[:20]
            st.session_state.active_label=property_id.strip()
            st.session_state.active_model_id=model_id
            st.success(f'{len(d)} rezervasyon puanlandı. Rezervasyon takibi → Yüklenen aktif dosya bölümüne geçebilirsin.')
        except Exception as exc:
            # Do not leave an older snapshot looking like the failed new upload.
            st.session_state.pop('active_data',None); st.session_state.pop('active_namespace',None)
            st.error('Dosya işlenemedi: '+str(exc))
    if 'active_data' in st.session_state:
        st.subheader('Puanlanan dosya')
        current=st.session_state.active_data
        st.caption(f'Tesis: {st.session_state.active_label} · {len(current)} rezervasyon · Karar günü: {current.snapshot_date.iloc[0]:%d.%m.%Y}')
        st.dataframe(current[['reservation_id','arrival_date','hotel','risk']].head(30),hide_index=True,width='stretch')
        st.download_button('Puanlanan dosyayı indir',csv_bytes(current),'puanlanan-rezervasyonlar.csv','text/csv')
        if st.button('Bu rezervasyonları yerelde sakla',key='persist_upload'):
            try:
                count=save_batch(st.session_state.active_namespace,current,st.session_state.get('active_model_id',model_id),'pilot',st.session_state.active_label)
                st.success(f'{count} yeni kayıt saklandı. Kayıtlar ve sonuçlar bölümünden tekrar açabilir ve gerçekleşen sonuçları girebilirsin.')
            except ValueError as exc: st.error(str(exc))
        st.caption('Yalnız model girdileri, rezervasyon kimliği ve tahmin saklanır. Aynı karar günündeki eski bir tahminin üzerine yazılmaz.')

else:
    st.caption('ÖLÇÜLEBİLİR MAKİNE ÖĞRENMESİ')
    st.title('Model neyi öğreniyor?')
    st.write('Rezervasyon oluşturulduğu anda eldeki bilgileri kullanarak müşterinin ileride rezervasyonunu iptal etme olasılığını tahmin eder.')
    st.info('Bu model, rezervasyon anındaki müşteri grubu, ön süre (lead time), oda türü ve konaklama süresi gibi özelliklerle erken karar desteği sağlar.')
    m=report['selected_calibrated_test']
    a,b,c,d=st.columns(4)
    a.metric('Test rezervasyonu',f'{m["rows"]:,}')
    b.metric('Gerçekleşen olay',m['events'])
    c.metric('Sıralama başarısı (AP)',f'{m["average_precision"]:.3f}')
    d.metric('Olay oranı',f'%{m["event_rate"]*100:.2f}')
    st.write('Seçilen model: **'+report['selected']+'**, ayrı dönemde olasılık kalibrasyonu uygulandı.')
    if not report['beats_constant_brier']:
        st.warning('Seçilen modelin testteki Brier hatası sabit oran modelinden daha iyi değil. Olasılık toplamlarını operasyonel plan için doğrulanmış kabul etmeyin.')
    split=pd.DataFrame(report['splits']).T.rename(columns={'rows':'Rezervasyon','events':'Olay','start':'İlk karar günü','end':'Son karar günü','last_outcome':'Son sonuç tarihi'})
    st.subheader('Önce geçmişten öğren, sonra gelecekte sına')
    st.dataframe(split,width='stretch')
    scores=[]
    for name,entry in report['candidates'].items():
        scores.append({'Model':name,'Doğrulama AP':entry['validation']['average_precision'],'Test AP':entry['test']['average_precision'],'Test ROC-AUC':entry['test']['roc_auc'],'Test Brier':entry['test']['brier']})
    scores.append({'Model':report['selected']+' + kalibrasyon','Doğrulama AP':None,'Test AP':m['average_precision'],'Test ROC-AUC':m['roc_auc'],'Test Brier':m['brier']})
    st.dataframe(pd.DataFrame(scores),hide_index=True,width='stretch')
    st.caption('AP ve ROC-AUC yüksek, Brier düşük olduğunda daha iyidir. Model seçimi yalnız doğrulama döneminde yapıldı. Test sonuçları model seçmek için kullanılmadı.')
    a,b=st.columns(2)
    with a:
        st.subheader('Olasılıklar gerçekle uyuşuyor mu?')
        cal=pd.DataFrame(report['calibration'])
        limit=float(max(cal.predicted.max(),cal.actual.max())*1.1)
        curve=alt.Chart(cal).mark_line(point=True,color='#147d70').encode(x=alt.X('predicted:Q',title='Tahmin',axis=alt.Axis(format='%'),scale=alt.Scale(domain=[0,limit])),y=alt.Y('actual:Q',title='Gerçekleşen oran',axis=alt.Axis(format='%'),scale=alt.Scale(domain=[0,limit])),tooltip=['count',alt.Tooltip('predicted:Q',format='.2%'),alt.Tooltip('actual:Q',format='.2%')])
        ideal=alt.Chart(pd.DataFrame({'predicted':[0,limit],'actual':[0,limit]})).mark_line(color='#8899a3',strokeDash=[5,5]).encode(x='predicted:Q',y='actual:Q')
        st.altair_chart(ideal+curve,width='stretch')
        st.caption('Kesikli çizgide tahmin ile gerçekleşen oran eşittir.')
    with b:
        st.subheader('Günlük inceleme getirisi')
        for q in report['daily_queue']:
            st.write(f'**Otel başına günde en fazla {q["capacity_per_hotel_day"]} kayıt:** {q["reviewed"]:,} incelemede {q["found_events"]} geç iptal / gelmeme; aynı günlük kapasitede rastgele seçim beklentisi {q["random_expected_events"]:.1f}.')
        st.caption('Olayı listede bulmak, iletişim kurarak iptali önlemek anlamına gelmez.')
    with st.expander('Veri kalitesi ve deney ayrıntıları'):
        st.json(report['audit'])
        st.write('Birebir aynı satırlar ana deneyde korundu. Rezervasyon kimliği olmadığından bunların hata mı ayrı grup rezervasyonları mı olduğu bilinmiyor. Tekilleştirilmiş test duyarlılığı:')
        st.json(report['unique_record_sensitivity'])
        st.write('Gün bazlı 200 bootstrap örnekleminde AP %95 aralığı:',report['ap_day_bootstrap_95'])
        st.dataframe(pd.DataFrame(report['permutation_importance']),hide_index=True)
        st.caption('Önem değerleri tahmin ilişkisini gösterir, nedensellik veya misafire özel iptal gerekçesi değildir.')
    st.download_button('Deney raporunu indir',json.dumps(report,ensure_ascii=False,indent=2),'deney-raporu.json','application/json')
    if (ROOT/'artifacts/deney-raporu.html').exists():
        st.download_button('Okunabilir HTML raporunu indir',(ROOT/'artifacts/deney-raporu.html').read_bytes(),'otel-deney-raporu.html','text/html')
    st.markdown('Veri: Antonio, Almeida ve Nunes (2019), [Hotel Booking Demand](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/), CC BY 4.0. [Birleştirilmiş CSV kaynağı](https://github.com/rfordatascience/tidytuesday/tree/master/data/2020/2020-02-11).')
