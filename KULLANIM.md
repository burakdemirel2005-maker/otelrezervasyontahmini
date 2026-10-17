### Kendin denemek için

1. Soldan **Bir rezervasyon dene** bölümünü aç.
2. Giriş, çıkış ve rezervasyonun yapıldığı günü seç.
3. Otel türünü, misafir sayılarını, yemek planını ve rezervasyon kanallarını cevapla.
4. **Tahmini hesapla** düğmesine bas. Gerçek eğitilmiş model çalışır ve bir yüzde üretir.
5. Örneğin rezervasyonun yapıldığı tarihi değiştirip tekrar hesapla. Önceki ve yeni tahmin arasındaki farkı gör.
6. **Denemeyi kaydet** ile sakla. **Kayıtlar ve sonuçlar** bölümünden yeniden aç.

Denemeler modeli eğitmez. Aynı cevaplar aynı modelle aynı sonucu verir. Bir cevabı değiştirmek her zaman farklı sonuç üretmeyebilir: ağaç modeli benzer örnekleri aynı gruba yerleştirebilir.

### Tahmin ne anlama geliyor?

Gelişten önceki gün, gün sonunda hâlâ aktif olan rezervasyonun bundan sonra iptal edilmesi veya misafirin gelmemesi tahmin ediliyor. Örneğin “%4”, bu misafirin kesin iptal edeceği anlamına gelmez. Benzer skor verilen çok sayıda kayıtta gerçekleşen oranla sınanması gerekir.

Bu veriyle yapılan testte model sıralama sinyali gösterdi. Olasılık hatası sabit oran yönteminden iyi çıkmadı. Bu nedenle modelin verdiği yüzdeye dayanarak rezervasyon iptal etmek veya fazladan oda satmak uygun bir ürün işlevi değildir.

### Sorulardaki terimler

- **Şehir / tatil oteli:** Kaynak verideki iki tesis türü.
- **Oda kodu A–H:** Anonim kodlar. Harflerin lüks, standart veya oda büyüklüğü anlamı doğrulanmadı. Gerçek tesiste kod eşlemesi gerekir.
- **Müşteri grubu:** Doğrudan, kurumsal, çevrim içi acente, grup gibi rezervasyon segmenti.
- **Satış kanalı:** Rezervasyonun otele ulaştığı dağıtım yolu. Segmentten ayrı sorulur; farklı kombinasyonların gerçek rezervasyona uygun olması gerekir.
- **Bireysel / sözleşmeli / grup:** Rezervasyonun başka rezervasyonlara veya bir sözleşmeye bağlı olup olmadığı.
- **Hafta sonu gecesi:** Cumartesi ve pazar geceleri. Tarihlerden hesaplanır.

### Dosyayla çalışmak için

**Dosya yükle** bölümünden şablonu indir. Tek tesisin, tek gün sonundaki aktif ve ertesi gün gelecek rezervasyonlarını hazırla. Tesis kodunu her seferinde aynı yaz. Gerçek kişilerin adını, telefonunu veya e-postasını eklemen gerekmez.

Dosya denetlenip puanlanınca **Rezervasyon takibi → Yüklenen aktif dosya** seçeneğinden çalış. **Bu rezervasyonları yerelde sakla** düğmesine basarsan pencereyi kapattığında da kayıtlar korunur. Bu düğmeye basılmamış dosyalar yalnız mevcut oturumda kalır.

### Günlük takip

**Rezervasyon takibi** ekranında tarih, otel türü ve inceleme kapasitesini seç. Liste risk skoruna göre sıralanır. Not ve durum kaydet. “Yalnızca bekleyen kayıtlar” açıkken incelenen kayıt listeden çıkar; tekrar görmek için kutunun işaretini kaldır.

İnceleme kapasitesi ekrandaki liste uzunluğunu sınırlar. İncelediğin kayıtlar çıkarıldıkça sıradakiler gelir; bir günde toplam kaç görüşme yapabileceğin üzerinde zorunlu bir kota değildir.

### Gerçek sonuçları kaydetmek

Saklanmış pilot dosyaları için **Kayıtlar ve sonuçlar** ekranından “Konakladı / Geç iptal / Gelmedi” seç. Geliş günü henüz gelmemiş kayıtlara sonuç girilemez. Önceki gün iptal edilmiş rezervasyonlar bu modelin kapsamı dışındadır.

Takipteki “Teyit edildi” ile gerçekleşen “Konakladı” farklıdır. Sonucu değiştirmek eski tahmini değiştirmez; düzeltmenin geçmişi saklanır. Yalnız sonucu girilmiş kayıtlar üzerinden ölçüm yapılır. Eksik sonuçlar değerlendirmeyi yanıltabilir. Elle girilmiş denemeler gerçek pilot hesabına alınmaz.

### Saklama ve yedek

Kayıtlar bu bilgisayardaki SQLite veritabanındadır. **Kayıt ve takip geçmişini JSON indir** düğmesi seçili tesisin kayıtlarını, notlarını ve sonuç geçmişini dışarı verir. Tam yedek için proje içindeki `yedekle.py` betiği kullanılır. **Model ve veri** ekranından eğitim raporu indirilebilir.

Bu sürüm tek bilgisayarda çalışma ve akademik sunum için tamamlanmıştır. Çok kullanıcılı internet servisi, PMS entegrasyonu ve gerçek otelde ileriye dönük doğrulama ayrı üretim aşamasıdır.
