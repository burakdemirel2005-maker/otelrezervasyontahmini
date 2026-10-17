from datetime import date,timedelta
import pandas as pd
import streamlit as st
from .scenario import label,reservation,fingerprint,csv_bytes,FIELDS
from .ingest import score_frame
from .store import save_batch

def render(bundle,report,model_id):
    if st.session_state.get('manual_result',{}).get('model_id',model_id)!=model_id:
        st.session_state.pop('manual_result',None)
        st.session_state.pop('manual_previous',None)
    st.caption('SORULARI YANITLA · MODELİ KENDİN DENE')
    st.title('Bir rezervasyon deneyelim')
    st.write('Aşağıdaki soruları cevapla. Eğitilmiş model, bu rezervasyonun gelecekte iptal edilme olasılığını tahmin etsin.')
    st.info('Bu ekran, rezervasyonun oluşturulduğu andaki bilgileri kullanarak müşterinin ileride rezervasyonunu iptal etme olasılığını hesaplar. Girilen denemeler modeli yeniden eğitmez.')
    st.subheader('1. Ne zaman konaklayacak?')
    a,b,c=st.columns(3)
    arrival=a.date_input('Misafir hangi gün giriş yapacak?',value=date.today()+timedelta(days=1),key='manual_arrival')
    departure=b.date_input('Hangi gün çıkış yapacak?',value=date.today()+timedelta(days=3),key='manual_departure')
    booked=c.date_input('Rezervasyonu hangi gün yaptı?',value=date.today()-timedelta(days=29),key='manual_booked')
    st.subheader('2. Kimler ve nerede kalacak?')
    a,b=st.columns(2)
    hotel=a.selectbox('Otelin türü ne?',list({'City Hotel':0,'Resort Hotel':0}),format_func=lambda x:label('hotel',x),key='manual_hotel')
    room=b.selectbox('Rezervasyondaki oda kodu ne?',bundle['categories']['reserved_room_type'],help='A–H kaynak verideki anonim oda kodlarıdır. A standart, B lüks gibi bir anlamı doğrulanmamıştır. Denemek için bir kod seçebilirsin.',key='manual_room')
    a,b,c=st.columns(3)
    adults=a.number_input('Kaç yetişkin?',min_value=0,max_value=50,value=2,step=1,key='manual_adults')
    children=b.number_input('Kaç çocuk?',min_value=0,max_value=20,value=0,step=1,key='manual_children')
    babies=c.number_input('Kaç bebek?',min_value=0,max_value=10,value=0,step=1,key='manual_babies')
    st.subheader('3. Rezervasyon nasıl yapılmış?')
    a,b=st.columns(2)
    def choose(container,question,field,default):
        options=bundle['categories'][field]
        return container.selectbox(question,options,index=options.index(default),format_func=lambda x:label(field,x),key='manual_'+field)
    meal=choose(a,'Yemek planı hangisi?','meal','BB')
    segment=choose(b,'Rezervasyon hangi müşteri grubundan geldi?','market_segment','Online TA')
    a,b=st.columns(2)
    channel=choose(a,'Hangi satış kanalıyla otele ulaştı?','distribution_channel','TA/TO')
    customer=choose(b,'Müşterinin rezervasyon türü ne?','customer_type','Transient')
    try:
        frame=reservation(arrival,departure,booked,hotel,adults,children,babies,meal,segment,channel,room,customer)
        if adults+children+babies==0: raise ValueError('En az bir misafir girmelisin.')
    except ValueError as exc:
        st.error(str(exc)); return
    st.caption(f'Oluşturulma anı: {booked:%d.%m.%Y} · {(departure-arrival).days} gece · {(arrival-booked).days} gün önceden rezervasyon. Hafta sonu gecesi: {int(frame.stays_in_weekend_nights.iloc[0])}.')
    current=fingerprint(frame)
    if st.button('Tahmini hesapla',type='primary',key='manual_predict'):
        scored=score_frame(frame,bundle)
        previous=st.session_state.get('manual_result')
        if previous and previous['fingerprint']!=current:
            st.session_state.manual_previous=previous
        st.session_state.manual_result={'fingerprint':current,'frame':scored,'risk':float(scored.risk.iloc[0]),'model_id':model_id}
    result=st.session_state.get('manual_result')
    if not result: st.caption('Cevapların hazırsa “Tahmini hesapla” düğmesine bas.'); return
    if result['fingerprint']!=current:
        st.info('Cevaplarını değiştirdin. Yeni sonucu görmek için Tahmini hesapla düğmesine bas.'); return
    risk=result['risk']; st.divider(); st.subheader('Modelin cevabı')
    st.caption('Tahmini üreten model: '+bundle['selected']+' · Ayrı dönemde olasılık kalibrasyonu uygulanmış model.')
    a,b=st.columns(2)
    a.metric('İptal olasılığı tahmini',f'%{risk*100:.2f}')
    b.metric('Test dönemindeki genel iptal oranı',f'%{report["selected_calibrated_test"]["event_rate"]*100:.2f}')
    
    # Karar Destek Sistemi (DSS) - Risk Seviyesi ve Aksiyon Önerisi
    if risk < 0.25:
        st.success('🟢 **Düşük Risk Grubu:** Özel bir teyit işlemi gerekmez. Standart rezervasyon prosedürü uygulanabilir.')
    elif risk < 0.50:
        st.warning('🟡 **Orta Risk Grubu:** Giriş tarihine 3–5 gün kala misafire otomatik hatırlatma e-postası veya SMS ile teyit gönderilmesi önerilir.')
    else:
        st.error('🔴 **Yüksek Risk Grubu (Aksiyon Gerekli):** Kredi kartından ön provizyon talep edilmesi veya telefonla doğrudan iletişim kurularak rezervasyonun teyit edilmesi önerilir.')

    if not report.get('beats_constant_brier', True):
        st.warning('Bu modelin olasılık hatası testte sabit oran yöntemini geçemedi. Sonucu denemek ve öncelik sıralamasını incelemek için kullan; kesin iptal kararı olarak yorumlama.')
    previous=st.session_state.get('manual_previous')
    if previous:
        delta=100*(risk-previous['risk'])
        st.subheader('Önceki denemene göre ne değişti?')
        st.write(f'Önceki tahmin: **%{previous["risk"]*100:.2f}**. Yeni tahmin: **%{risk*100:.2f}**. Fark: **{delta:+.2f} yüzde puan**.')
        changes=[]
        for field in ['hotel','arrival_date','lead_time','stays_in_weekend_nights','stays_in_week_nights','adults','children','babies','meal','market_segment','distribution_channel','reserved_room_type','customer_type']:
            old=previous['frame'][field].iloc[0]; new=result['frame'][field].iloc[0]
            if old!=new: changes.append({'Soru':FIELDS[field],'Önce':str(label(field,old)),'Şimdi':str(label(field,new))})
        st.dataframe(pd.DataFrame(changes),hide_index=True,width='stretch')
        st.caption('Bu, modelin farklı girdilere verdiği cevapların karşılaştırmasıdır; değişikliğin gerçek hayatta iptale neden olduğunu kanıtlamaz.')
    with st.expander('Bilgisayara hangi değerler gitti?'):
        st.dataframe(result['frame'][bundle['features']],hide_index=True,width='stretch')
        st.caption('Misafirin adı, telefon numarası veya iptal sonucu sorulmaz. Aynı cevaplar aynı model sürümünde aynı sonucu verir.')
    name=st.text_input('Bu denemeye bir isim ver',value='İlk denemem',max_chars=100,key='manual_name')
    if st.button('Denemeyi kaydet',key='manual_save'):
        saved=result['frame'].copy(); saved['reservation_id']='ELLE-'+current[:12]
        try:
            count=save_batch('manual-v1',saved,model_id,'manual',name)
            st.success('Deneme kaydedildi. Kayıtlar ve sonuçlar bölümünde görebilirsin.' if count else 'Bu deneme zaten kayıtlı; tekrar eklenmedi.')
        except ValueError as exc: st.error(str(exc))
    st.download_button('Deneme sonucunu indir',csv_bytes(result['frame']),'rezervasyon-denemesi.csv','text/csv')
