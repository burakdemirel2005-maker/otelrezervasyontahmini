# Ölçülen Sonuçlar (Yüksek Başarılı v2.0 Modeli)

Zenginleştirilmiş 30 PMS ve alan mühendisliği (feature engineering) özelliği ile 6 farklı model yarıştırılmış; hem katı kronolojik gelecek dönem sınamasında (2017 Out-of-Time Test) hem de akademik literatür kıyaslama protokolünde (Stratified %80/%20 Split) yüksek doğruluk elde edilmiştir.

| Ölçüm | Kronolojik 2017 Testi | Akademik Standart Split (%20) |
|---|---:|---:|
| Eğitim + Önceki Dönem Rezervasyonu | 76.874 | 94.852 |
| Dokunulmamış Test Rezervasyonu | 40.510 | 23.713 |
| Testte İptal / Gelmeme | 15.730 (%38,83) | 8.835 (%37,26) |
| Seçilen Yöntem | Dengelenmiş Rastgele Orman | Dengelenmiş Rastgele Orman |
| **Test Doğruluk (Accuracy)** | **%81,06** | **%87,21** |
| **Test ROC-AUC** | **0,8963 (%89,63)** | **0,9474 (%94,74)** |
| **Test PR-AUC (AP)** | **0,8507 (%85,07)** | **0,9242 (%92,42)** |
| **Test F1-Score** | **0,7316 (%73,16)** | **0,8312 (%83,12)** |
| **Test Brier Hatası** | **0,1306** | **0,0951** |
| Sabit Oran Referans Brier Hatası | 0,2382 | 0,2338 |

Model hem sıralama başarısında (ROC-AUC: **0,8963** / Akademik Benchmark: **0,9474**) hem de olasılık hatasında (Brier: **0,1306** < 0,2382, `beats_constant_brier: True`) referans modelleri açık farkla geçmektedir.

Otel başına günde en fazla 10 inceleme ile 2017 test döneminde toplam 4.860 kayıt inceleniyor ve **3.769 gerçek iptal (%77,6 kesinlik, Lift: 2,25x)** yakalanıyor (rastgele inceleme beklentisi 1.676,2 olay). Kapasite 20 olduğunda 9.709 incelemede **6.676 gerçek iptal (Lift: 1,99x)** yakalanmaktadır.

AP için test günleri bazında 200 bootstrap örnekleminden %95 güven aralığı **0,8296–0,8677** olarak ölçülmüştür.

## Tamamlanan işlevler

Geçmiş analiz ve filtreler, Türkçe sorularla tek rezervasyon girişi, tarih/gece hesabı, gerçek modelden tahmin, önceki denemeyle karşılaştırma, test döneminden risk sıralaması, günlük liste kapasitesi, SQLite üzerinde kalıcı denemeler ve pilot kayıtları, takip notları, gerçekleşen sonuçlar, düzeltme geçmişi, CSV/Excel sözleşme denetimi ve puanlama, CSV/JSON dışa aktarma, tam SQLite yedekleme, model karşılaştırma, kalibrasyon, veri kalite raporu, HTML deney raporu ve tekrar üretilebilir eğitim komutu.

Gerçek otel verisi alınmadı, PMS entegrasyonu kurulmadı, ödeme/ticari paket hazırlanmadı ve internet yayını yapılmadı. Prototipteki dosya yükleme gerçek bir pilotun veri girişini denemek içindir.

## Doğrulama

`artifacts/test-results.txt` çalıştırılmış testlerin çıktısıdır. Testler zaman sınırlarını, sonuç sütunlarının dışlanmasını, hatalı girdileri, günlük kapasiteyi, farklı tesis kayıtlarının yalıtımını, CSV/Excel ve elle puanlamayı, model kaydetme/yükleme tutarlılığını, yedi ekranın açılmasını, takip ve sonuç formlarını, atomik kayıtları ve yedeklemeyi kapsar. Tarayıcıda elle giriş düğmesine basılarak gerçek tahmin alındı ve sonuç görsel olarak kontrol edildi.

Tam ölçümler: `artifacts/report.json`. Anlaşılır yöntem açıklaması ve başlatma adımları: `README.md`.
