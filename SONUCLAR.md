# İlk sürümün ölçülen sonuçları

17 Ekim 2026. Çalışan yerel akademik proje v1.0 tamamlandı. Üç öğrenen model ve iki basit referans yöntem gerçek CSV üzerinde çalıştırıldı. Projenin sonraki ticari aşaması gerçek otel pilotudur. Sonraki ürün geliştirmelerinde aynı eğitilmiş model kullanıldı; test sonucuna bakarak model seçimi değiştirilmedi.

| Ölçüm | Sonuç |
|---|---:|
| Eğitim rezervasyonu | 28.645 |
| Doğrulama rezervasyonu | 8.829 |
| Kalibrasyon rezervasyonu | 7.970 |
| Dokunulmamış test rezervasyonu | 23.591 |
| Testte geç iptal / gelmeme | 501 (%2,12) |
| Seçilen yöntem | Rastgele orman + sigmoid kalibrasyon |
| Test ROC-AUC | 0,630 |
| Test AP | 0,03894 |
| Sabit oran AP | 0,02124 |
| Test Brier hatası | 0,021065 |
| Sabit oran Brier hatası | 0,020834 |

Model riskli kayıtları sıralamada sinyal gösteriyor. Olasılık hatasında (Brier, düşük daha iyi) sabit oran referansını geçemiyor. Bu iki sonuç birlikte değerlendirilmelidir. “Yüksek doğrulukla tüm iptalleri biliyoruz” sonucu çıkarılamaz.

Otel başına günde en fazla 10 inceleme ile test döneminde toplam 4.837 kayıt inceleniyor ve 150 olay bulunuyor. Gün/otel bazında aynı kapasitede rastgele inceleme beklentisi 102,8 olay. Yakalama oranı 150/501 = %29,9; incelenenlerde olay oranı %3,10. Bunlar test döneminin toplamlarıdır, bir günün sonucu değildir. Listede olayı bulmak iptali önlemek demek değildir.

Kapasite 20 olduğunda 9.554 incelemede 267 olay; rastgele beklenti 201,9. Kaynakta aynı satırların tekrarı bulunduğu için tekilleştirilmiş test duyarlılığı da hesaplandı: ROC-AUC 0,589, AP 0,03291. Bu düşüş sonuçların veri yapısına duyarlı olduğunu gösterir.

AP için test günleri bazında 200 bootstrap örnekleminden %95 aralık yaklaşık 0,028–0,067. Yeni oteldeki belirsizliği kapsamaz.

## Tamamlanan işlevler

Geçmiş analiz ve filtreler, Türkçe sorularla tek rezervasyon girişi, tarih/gece hesabı, gerçek modelden tahmin, önceki denemeyle karşılaştırma, test döneminden risk sıralaması, günlük liste kapasitesi, SQLite üzerinde kalıcı denemeler ve pilot kayıtları, takip notları, gerçekleşen sonuçlar, düzeltme geçmişi, CSV/Excel sözleşme denetimi ve puanlama, CSV/JSON dışa aktarma, tam SQLite yedekleme, model karşılaştırma, kalibrasyon, veri kalite raporu, HTML deney raporu ve tekrar üretilebilir eğitim komutu.

Gerçek otel verisi alınmadı, PMS entegrasyonu kurulmadı, ödeme/ticari paket hazırlanmadı ve internet yayını yapılmadı. Prototipteki dosya yükleme gerçek bir pilotun veri girişini denemek içindir.

## Doğrulama

`artifacts/test-results.txt` çalıştırılmış testlerin çıktısıdır. Testler zaman sınırlarını, sonuç sütunlarının dışlanmasını, hatalı girdileri, günlük kapasiteyi, farklı tesis kayıtlarının yalıtımını, CSV/Excel ve elle puanlamayı, model kaydetme/yükleme tutarlılığını, yedi ekranın açılmasını, takip ve sonuç formlarını, atomik kayıtları ve yedeklemeyi kapsar. Tarayıcıda elle giriş düğmesine basılarak gerçek tahmin alındı ve sonuç görsel olarak kontrol edildi.

Tam ölçümler: `artifacts/report.json`. Anlaşılır yöntem açıklaması ve başlatma adımları: `README.md`.
