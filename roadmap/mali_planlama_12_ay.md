# CorvusTunnel — 12 Aylık Mali Planlama

> Tarih: 3 Haziran 2026 | Kur: 1 USD = 46 TL | Şirketsiz başlangıç (Lemon Squeezy MoR)

---

## Temel Varsayımlar

| Parametre | Değer |
|-----------|-------|
| **Aylık bütçe** | ₺1.000 |
| **Tam zamanlı iş** | ✅ Var (CorvusTunnel = yan proje) |
| **Şirket durumu** | ❌ Yok (ilk gelir sonrası kurulacak) |
| **Satış kanalı** | Lemon Squeezy (MoR, şirketsiz, TR banka destekli) |
| **Ödeme** | Lemon Squeezy → Türk bankasına payout |
| **Fiyatlandırma** | Community: Ücretsiz / Pro: $9/ay veya $89/yıl |
| **Lisans modeli** | Open Core (core açık, pro kapalı) |
| **Mevcut müşteri** | 0 (sıfırdan başlangıç) |
| **Döviz kuru** | 1 USD = 46 TL (Haziran 2026) |

---

## Lemon Squeezy Komisyon Detayı

Her $9/ay abonelik satışında:

| Kalem | Tutar | Açıklama |
|-------|-------|----------|
| Müşteri öder | $9.00 | |
| Platform ücreti | -$0.95 | %5 + $0.50 |
| International surcharge | -$0.14 | %1.5 |
| Subscription surcharge | -$0.05 | %0.5 |
| **Subtotal (Lemon Squeezy sonrası)** | **$7.86** | |
| Payout ücreti | -$0.08 | %1 |
| **Net gelir** | **$7.78** | **≈₺358** |

> [!NOTE]
> Her $9'luk satıştan sana **₺358** kalır. Lemon Squeezy toplam **%13.6** keser.

---

## Gider Kalemleri — Detaylı Döküm

### Tek Seferlik Kuruluş Giderleri

| Kalem | Tutar (₺) | Tutar ($) | Ne Zaman | Zorunlu mu? |
|-------|-----------|-----------|----------|-------------|
| corvustunnel.com domain (yıllık) | ₺690 | ~$15 | Ay 1 | ✅ Zaten var |
| Logo tasarımı | ₺0 | $0 | Ay 1 | AI ile yapılabilir |
| Landing page | ₺0 | $0 | Ay 1 | Kendin yaparsın |
| Lemon Squeezy hesap kurulumu | ₺0 | $0 | Ay 1 | ✅ Ücretsiz |
| Docker Hub hesap | ₺0 | $0 | Ay 1 | Personal = ücretsiz |
| GitHub repo kurulumu | ₺0 | $0 | Ay 1 | ✅ Ücretsiz |
| **TOPLAM KURULUŞ** | **₺690** | **~$15** | | |

### Aylık Sabit Giderler — Şirketsiz Dönem (Ay 1-3)

| Kalem | Tutar (₺/ay) | Tutar ($/ay) | Açıklama |
|-------|-------------|-------------|----------|
| Domain yenileme (aylık payı) | ₺58 | ~$1.25 | ₺690/12 |
| Cloudflare Free plan | ₺0 | $0 | DNS + CDN ücretsiz |
| Cloudflare Tunnel | ₺0 | $0 | Kullanıcının kendi tunnel'ı |
| Docker Hub Personal | ₺0 | $0 | Ücretsiz |
| Plausible CE (self-hosted) | ₺0 | $0 | Self-hosted ücretsiz |
| GitHub (public repo) | ₺0 | $0 | Ücretsiz |
| VPS (webhook sunucu) | ₺0 | $0 | ⬇️ Aşağıda açıklama |
| E-posta (ProtonMail Free) | ₺0 | $0 | info@corvustunnel.com |
| SMMM | ₺0 | $0 | Şirket yok |
| Bağ-Kur | ₺0 | $0 | 4/a mevcut |
| **TOPLAM AYLIK SABİT** | **₺58** | **~$1.25** | |

> [!TIP]
> **VPS gerekmez mi?** Şirketsiz dönemde lisans doğrulama basit tutulabilir: Lemon Squeezy webhook'u ücretsiz Cloudflare Workers ile yakalanır. VPS'e gerek kalmaz.
> 
> Alternatif: Vercel/Netlify ücretsiz tier ile webhook endpoint yap.

### Aylık Sabit Giderler — Şirket Kurulduktan Sonra (Ay 4+)

| Kalem | Tutar (₺/ay) | Açıklama |
|-------|-------------|----------|
| Domain | ₺58 | Yıllık payı |
| SMMM aylık | ₺3.750 | Defter tutma + beyanname |
| Bağ-Kur | ₺0 | 4/a mevcut |
| VPS (webhook + lisans sunucu) | ₺250 | Giriş seviye VPS |
| Plausible Cloud (opsiyonel) | ₺0 | Self-hosted devam |
| Docker Hub Pro (opsiyonel) | ₺322 | $7/ay - private repo |
| **TOPLAM AYLIK SABİT** | **₺4.380** | |

### Opsiyonel / Değişken Giderler

| Kalem | Tutar (₺/ay) | Ne Zaman |
|-------|-------------|----------|
| Google Ads denemesi | ₺500-1.000 | Ay 3+ |
| Twitter/X reklam | ₺300-500 | Ay 2+ |
| Hetzner VPS (upgrade) | ₺500 | Müşteri artınca |
| Avukat danışmanlık | ₺2.000-5.000 | Tek sefer, Ay 3+ |
| TÜRKPATENT marka tescili | ₺3.000-5.000 | Tek sefer, Ay 6+ |
| Cloudflare Pro | ₺920 | $20/ay, Ay 6+ |

---

## Gelir Projeksiyonları — 3 Senaryo

### Müşteri Büyüme Varsayımları

| Dönem | Pessimist | Realist | Optimist |
|-------|-----------|---------|----------|
| Ay 1 | 0 müşteri | 0 müşteri | 2 müşteri |
| Ay 2 | 1 müşteri | 3 müşteri | 8 müşteri |
| Ay 3 | 3 müşteri | 8 müşteri | 20 müşteri |
| Ay 6 | 8 müşteri | 25 müşteri | 60 müşteri |
| Ay 12 | 15 müşteri | 50 müşteri | 150 müşteri |

> [!NOTE]
> **Churn (kayıp) oranı:** Aylık %5-10 varsayıldı. Yani her ay yeni müşteri kazanırken bazılarını kaybedeceksin. Yukarıdaki rakamlar net aktif müşteri sayısıdır.

---

## 📊 Dönem Bazlı Detaylı Analiz

### ═══════════════════════════════════════
### 📅 AY 1 — LANSMAN HAZIRLIĞI
### ═══════════════════════════════════════

**Hedef:** Ürünü hazırla, open core repo'yu aç, landing page yayınla

| Kalem | Tutar (₺) |
|-------|-----------|
| **GİDERLER** | |
| Domain (zaten var) | 0 |
| Landing page (kendin) | 0 |
| GitHub repo kurulumu | 0 |
| Lemon Squeezy kurulum | 0 |
| Pazarlama (organik) | 0 |
| **Toplam Gider** | **₺0** |
| | |
| **GELİR** | |
| Pessimist: 0 müşteri | ₺0 |
| Realist: 0 müşteri | ₺0 |
| Optimist: 2 müşteri × ₺358 | ₺716 |
| | |
| **NET (Realist)** | **₺0** |

**Yapılacaklar:**
- [x] Open core repo GitHub'a yükle
- [x] Landing page (corvustunnel.com) yayınla
- [x] Lemon Squeezy hesabı kur
- [x] Docker Hub'a Community image yükle
- [x] HN Show HN gönderisi yaz (henüz gönderme)
- [x] Twitter/X hesabı oluştur

---

### ═══════════════════════════════════════
### 📅 AY 1-3 — İLK SATIŞ DÖNEMİ
### ═══════════════════════════════════════

**Hedef:** İlk müşterileri kazan, geri bildirim al

#### Kümülatif Gider Tablosu (3 Ay)

| Kalem | Ay 1 | Ay 2 | Ay 3 | 3-Ay Toplam |
|-------|------|------|------|-------------|
| Domain (aylık payı) | ₺58 | ₺58 | ₺58 | ₺174 |
| Altyapı (Cloudflare Workers) | ₺0 | ₺0 | ₺0 | ₺0 |
| Docker Hub | ₺0 | ₺0 | ₺0 | ₺0 |
| Pazarlama (organik) | ₺0 | ₺0 | ₺0 | ₺0 |
| Twitter Ads (opsiyonel) | ₺0 | ₺0 | ₺300 | ₺300 |
| **Toplam Gider** | **₺58** | **₺58** | **₺358** | **₺474** |

#### Kümülatif Gelir Tablosu (3 Ay) — $9/ay Pro

| Senaryo | Ay 1 | Ay 2 | Ay 3 | 3-Ay Toplam |
|---------|------|------|------|-------------|
| **Pessimist** (0→1→3) | ₺0 | ₺358 | ₺1.074 | **₺1.432** |
| **Realist** (0→3→8) | ₺0 | ₺1.074 | ₺2.864 | **₺3.938** |
| **Optimist** (2→8→20) | ₺716 | ₺2.864 | ₺7.160 | **₺10.740** |

#### 3-Aylık Net Kâr/Zarar

| Senaryo | Gelir | Gider | **Net** |
|---------|-------|-------|---------|
| **Pessimist** | ₺1.432 | ₺474 | **+₺958** ✅ |
| **Realist** | ₺3.938 | ₺474 | **+₺3.464** ✅ |
| **Optimist** | ₺10.740 | ₺474 | **+₺10.266** ✅ |

> [!IMPORTANT]
> **Şirketsiz dönemde gider neredeyse sıfır!** Pessimist senaryoda bile 3 ayda kâr.

---

### ═══════════════════════════════════════
### 📅 AY 1-6 — BÜYÜME DÖNEMİ
### ═══════════════════════════════════════

**Hedef:** Şirket kurulumu (Ay 4), Paddle'a geçiş, büyüme

#### Kümülatif Gider Tablosu (6 Ay)

| Kalem | Ay 1-3 | Ay 4 | Ay 5 | Ay 6 | 6-Ay Toplam |
|-------|--------|------|------|------|-------------|
| Domain | ₺174 | ₺58 | ₺58 | ₺58 | ₺348 |
| Altyapı | ₺0 | ₺250 | ₺250 | ₺250 | ₺750 |
| Docker Hub | ₺0 | ₺0 | ₺322 | ₺322 | ₺644 |
| SMMM | ₺0 | ₺3.750 | ₺3.750 | ₺3.750 | ₺11.250 |
| Şirket kuruluş (tek sefer) | ₺0 | ₺10.000 | ₺0 | ₺0 | ₺10.000 |
| Bağ-Kur | ₺0 | ₺0 | ₺0 | ₺0 | ₺0 |
| Pazarlama | ₺300 | ₺500 | ₺500 | ₺1.000 | ₺2.800 |
| **Toplam** | **₺474** | **₺14.558** | **₺4.880** | **₺5.380** | **₺25.792** |

#### Kümülatif Gelir Tablosu (6 Ay)

| Senaryo | Ay 1-3 | Ay 4 | Ay 5 | Ay 6 | 6-Ay Toplam |
|---------|--------|------|------|------|-------------|
| **Pessimist** (→5→7→8) | ₺1.432 | ₺1.790 | ₺2.506 | ₺2.864 | **₺8.592** |
| **Realist** (→12→18→25) | ₺3.938 | ₺4.296 | ₺6.444 | ₺8.950 | **₺23.628** |
| **Optimist** (→30→45→60) | ₺10.740 | ₺10.740 | ₺16.110 | ₺21.480 | **₺59.070** |

#### 6-Aylık Net Kâr/Zarar

| Senaryo | Gelir | Gider | **Net** | Durum |
|---------|-------|-------|---------|-------|
| **Pessimist** | ₺8.592 | ₺25.792 | **-₺17.200** | 🔴 Zarar |
| **Realist** | ₺23.628 | ₺25.792 | **-₺2.164** | 🟡 Neredeyse başa baş |
| **Optimist** | ₺59.070 | ₺25.792 | **+₺33.278** | 🟢 Kâr |

> [!WARNING]
> **6 ayda pessimist senaryo zararda!** Ana neden: Ay 4'te şirket kuruluş maliyeti (₺10.000) + SMMM başlangıcı. Bu yüzden şirket kurmayı mümkün olduğunca ertele.

---

### ═══════════════════════════════════════
### 📅 AY 1-12 — TAM YIL
### ═══════════════════════════════════════

**Hedef:** Sürdürülebilir gelir, Team tier lansmanı

#### Kümülatif Gider Tablosu (12 Ay)

| Kalem | Ay 1-3 | Ay 4-6 | Ay 7-9 | Ay 10-12 | 12-Ay Toplam |
|-------|--------|--------|--------|----------|-------------|
| Domain | ₺174 | ₺174 | ₺174 | ₺174 | ₺696 |
| Altyapı (VPS) | ₺0 | ₺750 | ₺750 | ₺1.500 | ₺3.000 |
| Docker Hub Pro | ₺0 | ₺644 | ₺966 | ₺966 | ₺2.576 |
| SMMM | ₺0 | ₺11.250 | ₺11.250 | ₺11.250 | ₺33.750 |
| Şirket kuruluş | ₺0 | ₺10.000 | ₺0 | ₺0 | ₺10.000 |
| Bağ-Kur | ₺0 | ₺0 | ₺0 | ₺0 | ₺0 |
| Pazarlama | ₺300 | ₺2.500 | ₺3.000 | ₺3.000 | ₺8.800 |
| Avukat (tek sefer) | ₺0 | ₺0 | ₺5.000 | ₺0 | ₺5.000 |
| TÜRKPATENT (opsiyonel) | ₺0 | ₺0 | ₺0 | ₺4.000 | ₺4.000 |
| Cloudflare Pro (Ay 9+) | ₺0 | ₺0 | ₺920 | ₺2.760 | ₺3.680 |
| **Toplam** | **₺474** | **₺25.318** | **₺22.060** | **₺23.650** | **₺71.502** |

#### Kümülatif Gelir Tablosu (12 Ay)

| Senaryo | Ay 1-3 | Ay 4-6 | Ay 7-9 | Ay 10-12 | 12-Ay Toplam |
|---------|--------|--------|--------|----------|-------------|
| **Pessimist** (→15 aktif) | ₺1.432 | ₺7.160 | ₺12.522 | ₺16.102 | **₺37.216** |
| **Realist** (→50 aktif) | ₺3.938 | ₺19.690 | ₺39.380 | ₺53.700 | **₺116.708** |
| **Optimist** (→150 aktif) | ₺10.740 | ₺48.330 | ₺107.400 | ₺161.100 | **₺327.570** |

#### 12-Aylık Net Kâr/Zarar

| Senaryo | Gelir | Gider | **Net** | Aylık Ort. Kâr |
|---------|-------|-------|---------|----------------|
| **Pessimist** | ₺37.216 | ₺71.502 | **-₺34.286** | 🔴 -₺2.857/ay |
| **Realist** | ₺116.708 | ₺71.502 | **+₺45.206** | 🟢 +₺3.767/ay |
| **Optimist** | ₺327.570 | ₺71.502 | **+₺256.068** | 🟢 +₺21.339/ay |

---

## 📈 Break-Even (Başa Baş) Analizi

### Şirketsiz Dönem (Ay 1-3)
- Aylık sabit gider: ~₺58
- Break-even: **1 müşteri** (₺358 > ₺58)

### Şirketli Dönem (Ay 4+)
- Aylık sabit gider: ~₺4.380
- Break-even: **13 aylık müşteri** (13 × ₺358 = ₺4.654)

### Şirket kuruluş maliyetini karşılama:
- ₺10.000 / ₺358 = **28 müşteri-ay** 
- (örn: 28 müşteri × 1 ay veya 10 müşteri × 3 ay)

---

## 🔴 Risk Matrisi

### Finansal Riskler

| Risk | Olasılık | Etki | Sonuç | Önlem |
|------|----------|------|-------|-------|
| Hiç müşteri gelmemesi | Orta | Yüksek | Şirketsiz dönemde ₺0 zarar, şirketli dönemde SMMM maliyeti akar | Şirket kurmayı ertele, organik pazarlamaya odaklan |
| Yüksek churn (kayıp) | Yüksek | Orta | Müşteri sayısı artmaz | Onboarding iyileştir, müşteri geri bildirimi al |
| Dolar kuru düşmesi | Düşük | Düşük | TL gelir azalır (ama giderler de TL) | Fiyatlandırma USD, minimal etki |
| Lemon Squeezy kapanması | Çok Düşük | Yüksek | Ödeme alınamaz | Alternatif: Paddle (şirket kurduktan sonra) |
| SMMM maliyeti artması | Orta | Düşük | Aylık gider artar | E-defter/e-fatura ile dijitalleş |

### Teknik Riskler

| Risk | Olasılık | Etki | Sonuç | Önlem |
|------|----------|------|-------|-------|
| AI agent ToS değişikliği | Düşük | Yüksek | Terminal I/O yasaklanabilir | Agent-agnostik yapı, hızlı adaptasyon |
| Docker Hub policy değişikliği | Çok Düşük | Orta | Image dağıtımı zorlaşır | Alternatif: GitHub Container Registry |
| Güvenlik açığı bulunması | Orta | Yüksek | İtibar kaybı | Security audit, bug bounty, open core |
| Rakip ürün çıkması | Yüksek | Orta | Pazar payı düşer | Hızlı iterasyon, niş odağı |

### Operasyonel Riskler

| Risk | Olasılık | Etki | Sonuç | Önlem |
|------|----------|------|-------|-------|
| Tam zamanlı iş + CorvusTunnel yorgunluğu | Yüksek | Yüksek | Geliştirme yavaşlar | Haftalık 10 saat sınırı koy |
| Destek taleplerini karşılayamama | Orta | Orta | Müşteri memnuniyetsizliği | Community forum, detaylı dokümantasyon |
| Vergi denetimi | Düşük | Orta | Geçmişe dönük vergi talebi | SMMM ile düzenli çalış |

---

## 💰 Nakit Akışı Projeksiyonu — Realist Senaryo (Aylık)

| Ay | Müşteri | Gelir (₺) | Gider (₺) | Net (₺) | Kümülatif (₺) |
|----|---------|-----------|-----------|---------|---------------|
| 1 | 0 | 0 | 58 | -58 | -58 |
| 2 | 3 | 1.074 | 58 | +1.016 | +958 |
| 3 | 8 | 2.864 | 358 | +2.506 | +3.464 |
| 4 ⬅️ Şirket | 12 | 4.296 | 14.558 | -10.262 | -6.798 |
| 5 | 18 | 6.444 | 4.880 | +1.564 | -5.234 |
| 6 | 25 | 8.950 | 5.380 | +3.570 | -1.664 |
| 7 | 30 | 10.740 | 5.130 | +5.610 | +3.946 |
| 8 | 35 | 12.530 | 5.130 | +7.400 | +11.346 |
| 9 | 40 | 14.320 | 7.050 | +7.270 | +18.616 |
| 10 | 43 | 15.394 | 7.050 | +8.344 | +26.960 |
| 11 | 47 | 16.826 | 7.050 | +9.776 | +36.736 |
| 12 | 50 | 17.900 | 9.550 | +8.350 | **+45.086** |

> [!IMPORTANT]
> **Ay 7'de kümülatif pozitife geçiyor!** İlk 6 ayda şirket kuruluş maliyeti nedeniyle kümülatif negatif olsa da, Ay 7'den itibaren sürekli kâr.

---

## 🎯 Kritik Kilometre Taşları

| Kilometre Taşı | Ne Zaman | Koşul |
|----------------|----------|-------|
| **İlk müşteri** | Ay 2 | HN/Reddit/Twitter paylaşımı |
| **İlk ₺1.000 gelir** | Ay 2-3 | 3 aylık müşteri |
| **Break-even (şirketsiz)** | Ay 2 | 1 müşteri |
| **Şirket kurma kararı** | Ay 3-4 | >5 aktif müşteri |
| **Break-even (şirketli)** | Ay 7 | >30 aktif müşteri |
| **₺10.000/ay gelir** | Ay 7-8 | ~30 müşteri |
| **Team tier lansmanı** | Ay 9 | Kurumsal talep gelirse |
| **₺50.000 kümülatif kâr** | Ay 12 | ~50 aktif müşteri |

---

## 🛡️ Senaryoya Göre Aksiyon Planı

### Pessimist Senaryo Gerçekleşirse (3 ayda <3 müşteri):

1. ❌ Şirket kurma — ertelemeye devam
2. 🔍 Ürün-pazar uyumunu sorgula:
   - Fiyat mı yüksek? → $5/ay'a düşür
   - Özellikler mi eksik? → Kullanıcı anketi yap
   - Pazarlama mı yetersiz? → Demo video yap, HN'ye gönder
3. 💡 Pivot seçenekleri:
   - Freelance danışmanlık (CorvusTunnel kurulum hizmeti)
   - Özel kurumsal kurulum hizmeti satışı

### Realist Senaryo Gerçekleşirse (3 ayda 8 müşteri):

1. ✅ Ay 4'te şirket kur
2. ✅ Lemon Squeezy'den Paddle'a geçiş değerlendir
3. ✅ Pazarlama bütçesini artır (₺1.000/ay)
4. ✅ Multi-agent özelliğini önceliklendir (upsell)

### Optimist Senaryo Gerçekleşirse (3 ayda 20 müşteri):

1. ✅ Hemen şirket kur (Ay 3)
2. ✅ Paddle'a geç
3. ✅ VPS ölçeklendir
4. ✅ Team tier'ı hızlandır
5. ✅ Part-time destek personeli düşün

---

## 📋 Vergisel Özet

### Şirketsiz Dönem (Ay 1-3)
- Lemon Squeezy geliri = **yurt dışı kazancı**
- Küçük tutarlarda genellikle sorun olmaz ama **teknik olarak** gelir vergisi beyanı gerekir
- ⚠️ Vergi müfettişi tarafından tespit riski düşük ama sıfır değil
- 💡 SMMM'ye danışarak geriye dönük beyanname verilebilir

### Şirketli Dönem (Ay 4+)
| Vergi | Oran | Detay |
|-------|------|-------|
| Gelir Vergisi | %15-40 (artan oranlı) | İlk ₺158K → %15, sonrası artan |
| KDV | %0 | Hizmet ihracatı KDV'den muaf |
| Stopaj | Yok | Hizmet ihracatı |
| Damga Vergisi | ~₺835/beyanname | Aylık beyannameler |

> [!TIP]
> **Genç Girişimci muafiyeti** (eşin üzerine kurulursa, 29 yaş altı, ilk kez): İlk ₺400K kâr vergisiz. Ama Bağ-Kur ₺10.157/ay başlar — vergi tasarrufundan fazla! Kendi üzerine kur.

---

## ⚡ Hemen Yapılacaklar (Bu Hafta)

1. **[ ] Lemon Squeezy hesabı oluştur** — lemonsqueezy.com
2. **[ ] Ürün/fiyat sayfası oluştur** — $9/ay Pro, $89/yıl Pro
3. **[ ] Twitter/X hesabı oluştur** — @CorvusTunnel
4. **[ ] Open core repo'yu GitHub'a yükle** — corvustunnel-core
5. **[ ] Landing page'i corvustunnel.com'a yayınla**
6. **[ ] Docker Hub'a Community image yükle**
7. **[ ] HN Show HN gönderisi taslağını hazırla**

---

## 📌 Sonuç

| Soru | Cevap |
|------|-------|
| İlk 3 ayda para kaybeder miyim? | **Hayır** — şirketsiz dönemde gider ≈₺0 |
| Ne zaman şirket kurmalıyım? | **5+ aktif müşteri** olunca (Ay 3-4) |
| Ne zaman kâra geçerim? | **Ay 7** (realist, kümülatif) |
| 1 yılda ne kadar kazanırım? | Realist: **₺45K kâr** / Optimist: **₺256K kâr** |
| En büyük maliyet ne? | **SMMM aylık ücreti** (₺3.750/ay = yıllık ₺45K) |
| En büyük risk ne? | **Müşteri gelmemesi** → çözüm: şirket kurmayı ertele |

> [!IMPORTANT]
> **Ana strateji: Şirketsiz başla, şirketsiz kanıtla, şirketli ölçekle.**
> 
> Sabit maliyetleri sıfıra yakın tutarak riski minimize ediyoruz. İlk müşteriler gelene kadar tek harcaman domain (₺690/yıl).
