from datetime import date
import pandas as pd
import streamlit as st
from .store import collections,load_batch,outcomes,save_outcome,OUTCOMES,event_history,export_collection
from .scenario import csv_bytes
from .model import metrics

def render():
    st.caption('KAYITLAR · TAKİP · GERÇEKLEŞEN SONUÇLAR')
    st.title('Denemelerin ve pilot kayıtların')
    available=collections()
    if not available:
        st.info('Henüz saklanan rezervasyon yok. Bir rezervasyon dene bölümünde denemeni veya Dosya yükle bölümünde puanladığın dosyayı kaydet.'); return
    options={c['namespace']:('Elle girilen denemeler' if c['kind']=='manual' else c['label']) for c in available}
    namespace=st.selectbox('Hangi kayıtları açalım?',list(options),format_func=lambda x:options[x])
    kind=next(c['kind'] for c in available if c['namespace']==namespace)
    frame=load_batch(namespace)
    if kind=='manual': st.info('Bunlar senin girdiğin denemeler. Gerçek otel başarısı hesaplamasına alınmaz.')
    else: st.caption('Kaydedilen tahminler sabittir. Sonuç eklemek veya takip notu değiştirmek modeli yeniden eğitmez.')
    view=frame[['record_label','reservation_id','arrival_date','snapshot_date','hotel','risk','model_id','saved_at']].rename(columns={'record_label':'İsim','reservation_id':'Rezervasyon','arrival_date':'Geliş','snapshot_date':'Karar günü','hotel':'Otel türü','risk':'Tahmin','model_id':'Model sürümü','saved_at':'Kayıt zamanı'})
    st.dataframe(view,hide_index=True,width='stretch',column_config={'Tahmin':st.column_config.NumberColumn(format='percent')})
    st.download_button('Kayıtları CSV indir',csv_bytes(view),'kayitlar.csv','text/csv')
    st.download_button('Kayıt ve takip geçmişini JSON indir',export_collection(namespace),'yerel-kayit-yedegi.json','application/json')
    if kind=='manual': return
    st.subheader('Misafir gerçekten geldi mi?')
    st.write('Geliş günü geldikten sonra gerçekleşen sonucu ekle. “Teyit edildi” bir iletişim durumudur; burada gerçek konaklama sonucunu kaydediyoruz.')
    eligible=frame[frame.arrival_date.dt.date<=date.today()].copy()
    obs=outcomes(namespace)
    if eligible.empty:
        st.info('Bu rezervasyonların geliş günü henüz gelmedi. Sonuçları o gün veya sonrasında girebilirsin.')
    else:
        eligible['key']=eligible.reservation_id+' / '+eligible.snapshot_date.dt.strftime('%Y-%m-%d')
        key=st.selectbox('Sonucu girilecek rezervasyon',eligible.key.tolist())
        row=eligible[eligible.key.eq(key)].iloc[0]
        old=obs[(obs.reservation_id==row.reservation_id)&(obs.snapshot_date==row.snapshot_date.date().isoformat())]
        default_outcome=old.outcome.iloc[0] if not old.empty else OUTCOMES[0]
        default_date=pd.Timestamp(old.outcome_date.iloc[0]).date() if not old.empty else row.arrival_date.date()
        with st.form('outcome-'+key):
            outcome=st.selectbox('Gerçekte ne oldu?',OUTCOMES,index=OUTCOMES.index(default_outcome))
            event_date=st.date_input('Sonucun gerçekleştiği gün',value=default_date,min_value=row.arrival_date.date(),max_value=date.today())
            if st.form_submit_button('Gerçekleşen sonucu kaydet',type='primary'):
                try:
                    save_outcome(namespace,row.reservation_id,row.snapshot_date,outcome,event_date)
                    st.rerun()
                except ValueError as exc: st.error(str(exc))
    st.subheader('Bu kayıtlarda tahminler nasıl gidiyor?')
    if obs.empty:
        st.info('Henüz gerçekleşen sonuç girilmedi. Tahmin doğruluğu şu anda hesaplanamaz.')
    else:
        merged=frame.assign(snapshot_date=frame.snapshot_date.dt.strftime('%Y-%m-%d')).merge(obs,on=['reservation_id','snapshot_date'],how='left',validate='one_to_one')
        known=merged[merged.outcome.notna()].copy()
        a,b,c=st.columns(3)
        a.metric('Kaydedilmiş rezervasyon',len(merged)); b.metric('Sonucu bilinen',len(known)); c.metric('Sonucu eksik',int(merged.outcome.isna().sum()))
        st.caption('Yalnız sonucu girilen kayıtlar değerlendirilir. Eksik sonuçlar yanlılığa yol açabilir. Kullanıcının sonradan girdiği bu kayıtlar bağımsız veya ileriye dönük başarı kanıtı değildir.')
        # Never combine scores from different model versions in a single metric.
        model_ids=known.model_id.unique().tolist()
        version=st.selectbox('Değerlendirilecek model sürümü',model_ids,format_func=lambda s:s[:12])
        subset=known[known.model_id.eq(version)]
        y=subset.outcome.isin(['Geç iptal','Gelmedi']).astype(int)
        measured=metrics(y,subset.risk)
        a,b,c=st.columns(3)
        a.metric('Gerçek olay oranı',f'%{100*y.mean():.2f}'); b.metric('Ortalama tahmin',f'%{100*subset.risk.mean():.2f}'); c.metric('Brier hatası',f'{measured["brier"]:.4f}')
        if y.nunique()==2: st.write(f'ROC-AUC: {measured["roc_auc"]:.3f} · AP: {measured["average_precision"]:.3f} · {len(subset)} sonucu bilinen kayıt.')
        else: st.caption('Henüz iki farklı sonuç sınıfı yok; sıralama başarısı gösterilmiyor.')
        st.dataframe(known[['reservation_id','snapshot_date','risk','outcome','outcome_date']],hide_index=True,width='stretch')
        st.download_button('Sonuçları indir',csv_bytes(known),'pilot-sonuclari.csv','text/csv')
    with st.expander('Takip işlemleri geçmişi'):
        st.dataframe(event_history(namespace),hide_index=True,width='stretch')
