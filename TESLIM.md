# Yerel proje v1.0 teslim kapsamı

## Çalışan ürün

Yedi bölüm: Genel bakış, Bir rezervasyon dene, Rezervasyon takibi, Dosya yükle, Kayıtlar ve sonuçlar, Model ve veri, Kullanım rehberi.

Sorularla girilen kayıt ve dosyadan gelen kayıt aynı doğrulama ve model puanlama yolunu kullanır. Tarihlerden hafta içi/sonu geceleri ve rezervasyon ön süresi hesaplanır. Girdi değişince eski sonuç yeni cevaba aitmiş gibi gösterilmez. Önceki denemeyle fark ve değişen cevaplar gösterilir. Denemeler ve pilotlar ayrıdır.

Yerel veritabanında tahmin anındaki değer, skor, model sürümü ve kayıt zamanı tutulur. Pilot sonuçları sonradan eklenebilir. Sonuç düzeltmeleri ve takip değişiklikleri günlükte saklanır. Kaydedilmiş tahminin üzerine yazma engellenir. JSON/CSV dışa aktarımı ve tam SQLite yedekleme vardır.

## Makine öğrenmesi teslimi

- Değiştirilmemiş kaynak CSV ve SHA-256 özeti.
- Zaman sıralı eğitim, doğrulama, kalibrasyon ve son test ayrımı.
- İki baseline, üç öğrenen aday, doğrulama AP ile seçim.
- Ayrı dönemde kalibrasyon, testte AP/ROC-AUC/Brier/log loss.
- Günlük inceleme bütçesi, kalibrasyon tablosu, otel bazlı sonuçlar, tekrar satır duyarlılığı, gün bazlı bootstrap ve permutation importance.
- Eğitilmiş model, sabit sürüm bağımlılıkları, tekrar üretilebilir komutlar.
- Öğrenciye yönelik kullanım ve yöntem açıklaması, HTML deney raporu.

Son kullanıcı formunda fiyat, isim, telefon veya gerçekleşmiş iptal sonucu sorulmaz. Model başarısı olduğundan yüksek gösterilmez. Oda kodları anonimdir; gerçek tesise eşleme gerektirir.

## Çalıştırılmış doğrulama

`artifacts/test-results.txt` son test çıktısıdır. Kapsam: veri sözleşmesi, zaman ayrımı ve bilinen sonuç sınırları, gerçek modelle CSV/Excel ve elle giriş, aynı girdide kararlılık, saklanan modelin tahmin tutarlılığı, geçersiz tarihler ve misafirler, aynı kimliklerin temizlenmesi, kayıtların ayrılması, atomik kayıt, sonuç geçmişi, CSV formül koruması, SQLite yedekleme ve ekran/form akışları.

Tarayıcıda elle giriş formu, tahmin hesaplama ve güncellenen sonuç ayrıca kontrol edilir. Bunun kanıtı `artifacts/elle-deneme.png` ekran görüntüsüdür. Test kayıtları geçici veritabanında tutulur; teslim paketine kişisel kayıt veritabanı alınmaz.

## Akademik sunumda anlatılacak hikâye

“Otellerde sınırlı çalışan zamanını hangi aktif rezervasyonları incelemeye ayıralım?” sorusunu ele aldık. Erken iptaller zaten bilindiğinden yalnız gelişten önceki gün aktif kalan rezervasyonları değerlendirdik. Sonucu bildiren alanları tahmin girdilerinden çıkardık. Zamanı karıştırmadan öğrenen modelleri basit oranlarla karşılaştırdık. Model inceleme sıralamasında sinyal gösterdi, fakat olasılık hatasında sabit referansı geçemedi. Bu sınırı ürün içinde gösterdik. Gerçek veri ve sonuç toplayabilecek izlenebilir bir iş akışı geliştirdik.

## Üretime geçişte dışarıdan gerekenler

Bu sürüm tek bilgisayarda çalışan yerel akademik üründür. Otelde doğrulanmış ticari hizmet olduğunu iddia etmez. Ticari sonraki adımda izinli gerçek rezervasyon zaman çizelgeleri, kod eşlemesi, ileriye dönük pilot, kullanıcı/tesis yetkilendirmesi, PMS entegrasyonu, güvenli barındırma ve izleme gerekir. Bu işler otel erişimi ve işletme kararları olmadan doğrulanmış sayılmaz.

Kaynak CSV'nin snapshot belirsizliği ve iki eski otelle sınırlı olması yazılımla ortadan kaldırılamaz. İletişimin iptali azaltıp azaltmadığı kontrollü ayrı bir değerlendirme ister. Gelecekteki yeni rezervasyonlar, oda kapasitesi, fiyatlandırma ve overbooking bu sürümün tahmin ettiği hedef değildir.
