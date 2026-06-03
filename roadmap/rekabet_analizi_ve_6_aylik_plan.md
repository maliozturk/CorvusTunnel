# CorvusTunnel — Rekabet Analizi & 6 Aylık Stratejik Plan

> Rakipler, avantajlar, pazar doğrulaması ve adım adım 6 aylık yol haritası.

---

## 1. Pazar Doğrulaması: "Saçma Bir Şey mi Yapıyoruz?"

### Kısa Cevap: HAYIR.

**Pazar gerçekleri:**
- AI coding agent pazarı 2026'da patlama yaşıyor (Claude Code, Codex, Antigravity)
- "Telefondan AI agent kontrol etme" ihtiyacı o kadar gerçek ki **büyük firmalar built-in çözüm ekledi**
- Ancak hiçbir firma **agent-agnostik, self-hosted, çok katmanlı güvenlikli** bir çözüm sunmuyor
- **Antigravity (Google)** için piyasada HİÇ mobil erişim çözümü yok — 18 Haziran 2026'da Gemini CLI kapanıyor, kullanıcılar çözüm arıyor

**Geliştiricilerin en büyük sorunları (2026 Reddit/forum analizi):**
1. 👶 **"Babysitting" problemi** — Agent'ı sürekli izlemek zorunda kalmak
2. 🔍 **Observability eksikliği** — Agent ne yaptı, izlenemiyor
3. 📋 **Context yönetimi** — Terminal çıktıları çok uzun/düzensiz
4. 🔐 **Governance** — Human-in-the-loop onay mekanizması eksik

> [!IMPORTANT]
> **CorvusTunnel tam olarak bu 4 sorunu çözüyor:** Audit logları, manuel onay, gerçek zamanlı stream, ve çoklu agent desteği.

---

## 2. Rakip Haritası

### 2.1 Doğrudan Rakipler

| Rakip | Fiyat | Tür | Ne Yapar | Zayıf Noktası |
|-------|-------|-----|----------|---------------|
| **Claude Remote Control** | Ücretsiz (Pro plan içinde, $20/ay) | Built-in özellik | Claude Code'a telefondan erişim, QR kod ile bağlantı | Sadece Claude, kurumsal özellik yok, terminal kapanırsa oturum biter |
| **Codex Mobile** | Ücretsiz (ChatGPT Plus içinde, $20/ay) | Built-in özellik | ChatGPT mobil uygulaması üzerinden Codex kontrolü | Sadece Codex, desktop app gerekli, CLI'dan kurulamaz |
| **CodeAgent Mobile** | $0-$9.99/ay | Bağımsız uygulama | Çoklu IDE desteği, görev onaylama, QR pairing | Cloud-bağımlı, self-hosted değil, multi-agent orkestrasyon yok |
| **Omnara** | Bilinmiyor | Mobil uygulama | Claude Code odaklı, voice-first yaklaşım | Tek agent, Apple ekosistemi odaklı |

### 2.2 Dolaylı Rakipler / DIY Çözümler

| Çözüm | Fiyat | Tür | Avantajı | Dezavantajı |
|-------|-------|-----|----------|-------------|
| **Junction Panel** | Ücretsiz/Açık kaynak | PWA kontrol paneli | Local-first, açık kaynak | Basit, lisanslama yok, tek agent |
| **CCGram** | Ücretsiz/Açık kaynak | Telegram botu | Telegram üzerinden tmux kontrolü | Teknik, UX yok, güvenlik katmanı yok |
| **Tailscale + SSH** | Ücretsiz | DIY | Tam kontrol | Kurulum karmaşık, güvenlik katmanı yok |
| **Blink Shell + Mosh** | ~$20 (tek seferlik) | SSH istemcisi | iOS'ta mükemmel terminal | Sadece terminal, akıllı özellik yok |

### 2.3 Büyük Tehditler

> [!WARNING]
> **En büyük tehdit:** Claude ve Codex'in kendi built-in mobil özelliklerinin varlığı. Bu firmaların kullanıcıları CorvusTunnel'a ihtiyaç duymayabilir — **eğer sadece terminal proxy olarak kalırsak.**

**Çözüm:** "Terminal proxy" olmaktan çıkıp **"AI Agent Command Center"** olmak.

---

## 3. CorvusTunnel'ın Rekabet Avantajları

### 3.1 "Kimse Yapamıyor" Tablosu

| Özellik | Claude RC | Codex | CodeAgent | Omnara | **CorvusTunnel** |
|---------|-----------|-------|-----------|--------|------------------|
| Multi-agent (3+ agent) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Multi-agent orkestrasyon | ❌ | ❌ | ❌ | ❌ | ✅ |
| Self-hosted Docker | ❌ | ❌ | ❌ | ❌ | ✅ |
| Audit log + IP ban + onay | ❌ | ❌ | ✅ | ❌ | ✅ |
| Sesli çıktı özeti (TTS) | ❌ | ❌ | ❌ | ❌ | ✅ |
| One-tap workflow | ❌ | ❌ | ❌ | ❌ | ✅ |
| Agent-agnostik | ❌ | ❌ | ✅ | ❌ | ✅ |
| QR ile tek tarama kurulum | ✅ | ✅ | ✅ | ❌ | ✅ |
| **TOPLAM** | **2/8** | **2/8** | **4/8** | **0/8** | **8/8** |

### 3.2 Temel Pozisyonlama

**Eski:** "Telefondan AI agent kontrol et" (herkes yapıyor)
**Yeni:** "Tüm AI agent'larını tek yerden yönet, karşılaştır ve güvenli tut"

**Tagline önerileri:**
- "Your AI Agents. One Command Center."
- "Control Every AI Agent From Your Phone."
- "The Mission Control for AI Coding Agents."

### 3.3 Antigravity Niche'i — Altın Fırsat

> [!TIP]
> **Antigravity (Google)** 18 Haziran 2026'da Gemini CLI'ın yerini alıyor ve HİÇ mobil erişim özelliği sunmuyor. Bu, CorvusTunnel için devasa bir fırsat penceresi. Lansman mesajlarında **Antigravity desteğini** öne çıkarmalıyız.

---

## 4. Özellik Yol Haritası — 6 Aylık Plan

### Fizibilite Özeti

| Özellik | Zorluk | Süre | Maliyet | Etki |
|---------|--------|------|---------|------|
| One-Tap Workflow'lar | 🟢 Düşük | 1-2 hafta | $0 | Yüksek |
| Proje Durumu Özeti | 🟢 Düşük | 1 hafta | $0 | Yüksek |
| Sesli Çıktı Özeti (TTS) | 🟢 Düşük | 1 hafta | $0 | Çok Yüksek |
| Agent Performans Dashboardı | 🟡 Orta | 3-4 hafta | $0 | Orta |
| AI Agent Co-Pilot (rule-based) | 🟡 Orta | 3-4 hafta | $0 | Orta |
| Multi-Agent Orkestrasyon | 🟡 Orta | 3-4 hafta | $0 | Çok Yüksek |
| Voice-First Kontrol (STT) | 🟡 Orta | 2-3 hafta | Test sonrası | Yüksek |

---

### Faz 1 — Lansman MVP (Ay 1-2)

**Hedef:** Satılabilir ürün çıkarmak + ilk kullanıcıları kazanmak

#### Teknik Geliştirmeler
- ✅ **İnteraktif terminal** (zaten var)
- 🆕 **Ücretsiz tier limitleri** — 30 dk oturum, 10 dk bekleme, günde 3 oturum
- 🆕 **One-Tap Workflow'lar** — 5-10 hazır şablon buton:
  - "Bu projeyi analiz et ve sorunları listele"
  - "Bu dosya için unit test yaz"
  - "Son hataları düzelt"
  - "PR açıklaması hazırla"
  - "Kodu refactor et"
  - "README güncelle"
  - Kullanıcı kendi şablonlarını da ekleyebilsin
- 🆕 **Proje Durumu Özeti** — Bağlantı kurulduğunda:
  - `git status` → değişen dosyalar
  - `git log -5` → son 5 commit
  - Son hata logları (varsa)
  - Açık TODO'lar
  - Kısa özet kartı olarak UI'da göster
- 🆕 **Sesli Çıktı Özeti** — Agent bitirdiğinde:
  - Agent'a ek özet prompt'u gönder: "Az önce yaptığın işi 2-3 cümleyle, kullanıcının dilinde özetle"
  - Agent'ın cevabını Web SpeechSynthesis ile sesli oku
  - "3 dosya değiştirildi, tüm testler geçti, PR hazır"

#### İş Altyapısı
- 📋 Şahıs Şirketi kaydı başlat
- 💳 Paddle hesabı oluştur + doğrulama
- 📧 Cloudflare Email Routing kur
- 🌐 corvustunnel.com landing page yap + deploy
- 📜 Hukuki belgeler (Privacy Policy, ToS, KVKK, Refund Policy, AUP, EULA)
- 🐳 Docker Hub'a ilk image push
- 🎥 Demo video çek + YouTube'a yükle
- 🐦 Twitter/X hesabı oluştur

#### Pazarlama & Lansman
- Twitter'da teaser paylaşımları (demo GIF'leri)
- **Lansman günü:** Twitter + Hacker News + Reddit
- r/selfhosted, r/programming, r/devops'a paylaşım

---

### Faz 2 — Büyüme (Ay 3-4)

**Hedef:** Rekabette öne geçmek + Pro dönüşüm oranını artırmak

#### Teknik Geliştirmeler
- 📊 **Agent Performans Dashboardı:**
  - Oturum süresi istatistikleri
  - Agent başarı/hata oranları
  - Terminal çıktı boyutu metrikleri
  - Günlük/haftalık kullanım grafikleri
  - Mobilde güzel görünen kartlar ve grafikler
- 🤖 **AI Agent Co-Pilot (rule-based):**
  - Agent çalışırken terminal çıktısını izle
  - Pattern tanıma ile uyarılar: "Test başarısız", "Build hatası", "Dosya çakışması"
  - Akıllı öneriler: "Bu hata daha önce de oldu, şu prompt'u dene"
  - CLAUDE.md / .cursorrules dosyası algılama ve güncelleme önerileri
- 🔧 **Gelişmiş One-Tap:**
  - Kullanıcı kendi workflow şablonlarını oluşturabilsin
  - Şablonlar JSON olarak export/import
  - Topluluk şablon paylaşımı (corvustunnel.com/workflows)

#### Pazarlama
- Blog yazıları: "CorvusTunnel vs Claude Remote Control: Karşılaştırma"
- YouTube tutorial serileri
- Kullanıcı referansları topla
- Product Hunt lansmanı
- dev.to makaleleri

---

### Faz 3 — Liderlik (Ay 5-6)

**Hedef:** "Kimse yapamıyor" özellikleri + pazar liderliği

#### Teknik Geliştirmeler
- 🔀 **Multi-Agent Orkestrasyon:**
  - Kullanıcı prompt gönderir + 2 agent seçer
  - Proje klasörü `.tmp1/` ve `.tmp2/` olarak kopyalanır (`rsync --exclude node_modules --exclude .git`)
  - Agent A → `.tmp1/` üzerinde, Agent B → `.tmp2/` üzerinde paralel çalışır
  - Split-screen veya tab'lı görünüm ile her iki çıktı izlenir
  - Agent'lar bitirdiğinde diff karşılaştırma gösterilir
  - Kullanıcı birini seçer → ana klasöre kopyalanır → `.tmp`'ler silinir
  - Sıralı çalıştırma opsiyonu da ekle (düşük kaynak modeli)
- 🎤 **Voice-First Kontrol (test sonucuna göre):**
  - Web Speech API ile sesli komut gönderme
  - Veya Deepgram/Whisper entegrasyonu
  - Alternatif: telefonun kendi klavye sesli giriş özelliğine yönlendir
- 👥 **Takım Tier Hazırlığı:**
  - Çoklu kullanıcı altyapısı (kullanıcı yönetimi)
  - Paylaşımlı audit loglar
  - Takım lisans yönetimi
  - Fiyatlandırma: $29/ay/seat

#### Pazarlama
- "CorvusTunnel Multi-Agent: Claude vs Codex karşılaştır" demo videosu
- Hacker News'e ikinci gönderi (yeni özelliklerle)
- Potansiyel yatırımcı görüşmeleri (gelir varsa)
- Kullanıcı topluluğu oluşturma

---

## 5. Detaylı Haftalık Lansman Takvimi (İlk 6 Hafta)

### Hafta 1 — Temel Altyapı

| Gün | Görev | Çıktı |
|-----|------|-------|
| Pzt | SMMM bul, Şahıs Şirketi sürecini başlat | Mali müşavir sözleşmesi |
| Pzt | Twitter/X hesabı oluştur (@corvustunnel) | İlk tweet: "Coming soon 🐦‍⬛" |
| Sal | Paddle hesabı oluştur, doğrulama başlat | Paddle başvuru ID |
| Sal | Cloudflare Email Routing kur | support@corvustunnel.com aktif |
| Çar | Landing page tasarımı başla | İlk mockup/wireframe |
| Per | Docker Hub hesabı + repository oluştur | corvustunnel/corvustunnel repo |
| Cum | Privacy Policy + Terms of Service taslağı | İlk draft'lar hazır |

### Hafta 2 — Ürün + Hukuki

| Gün | Görev | Çıktı |
|-----|------|-------|
| Pzt | Ücretsiz tier oturum limitlerini kodla | term_session.py güncellendi |
| Sal | Lisans plan farkındalığı kodla (free vs pro) | validator.py güncellendi |
| Çar | One-Tap Workflow UI'ını yap | 5-10 buton + şablon sistemi |
| Per | Proje Durumu Özeti özelliğini kodla | Bağlantıda git status kartı |
| Cum | KVKK Aydınlatma Metni + İade Politikası + AUP + EULA | 4 belge hazır |

### Hafta 3 — Entegrasyon + İçerik

| Gün | Görev | Çıktı |
|-----|------|-------|
| Pzt | Sesli Çıktı Özeti özelliğini kodla | Agent özet + TTS çalışıyor |
| Sal | Paddle webhook sunucusu yap | Otomatik lisans üretimi |
| Çar | Landing page'i bitir (fiyatlandırma, özellikler, demo) | corvustunnel.com canlı |
| Per | İlk demo video çek (60-90 saniye) | YouTube'a yüklendi |
| Cum | Hukuki sayfaları siteye deploy et | /legal/* sayfaları canlı |

### Hafta 4 — Test + Polish

| Gün | Görev | Çıktı |
|-----|------|-------|
| Pzt | Docker image build + Docker Hub'a push | v1.0.0 hazır |
| Sal | Uçtan uca test: satın al → lisans → Docker → kullanım | Tüm akış çalışıyor |
| Çar | Landing page son düzeltmeler + SEO | Site optimize edildi |
| Per | Paddle sandbox → production geçişi | Gerçek ödeme kabul ediliyor |
| Cum | Son bug fix'ler + 2. demo video | Her şey hazır |

### Hafta 5 — 🚀 LANSMAN

| Gün | Görev | Çıktı |
|-----|------|-------|
| **Pzt** | **LANSMAN GÜNÜ** | 🚀 |
| Pzt | Twitter'da demo video ile duyuru | İlk paylaşım |
| Pzt | Hacker News "Show HN" gönderisi | Show HN linki |
| Sal | Reddit paylaşımları (r/selfhosted, r/programming, r/devops) | 3 paylaşım |
| Çar | dev.to lansman makalesi | Blog yazısı |
| Per | Geri bildirimlere yanıt, acil bug fix | Hızlı iterasyon |
| Cum | İlk hafta metrikleri analizi | Rapor |

### Hafta 6 — İterasyon

| Gün | Görev | Çıktı |
|-----|------|-------|
| Pzt | Kullanıcı geri bildirimlerine göre iyileştirmeler | Patch release |
| Sal | FAQ/Docs sayfası oluştur | /docs/faq canlı |
| Çar | İkinci YouTube video (detaylı kurulum rehberi) | Video yüklendi |
| Per | Twitter'da kullanım senaryosu paylaşımı | Engagement artışı |
| Cum | Ay 3-4 özelliklerinin planlamasını başlat | Sprint planı |

---

## 6. Pazarlama Stratejisi Detayları

### 6.1 Twitter/X İçerik Takvimi

**Hesap oluşturma (@corvustunnel):**
- Bio: "Control every AI coding agent from your phone. 🐦‍⬛ Multi-agent | Self-hosted | Docker"
- Header: CorvusTunnel logo + QR kod görseli
- Pinned tweet: Demo video

**Haftalık içerik planı:**
| Gün | İçerik Türü | Örnek |
|-----|------------|-------|
| Pzt | Özellik tanıtımı (GIF/video) | "One-tap ile 'Test yaz' demeniz yeterli 🎯" |
| Çar | Kullanım senaryosu | "Otobüste projenin durumunu kontrol ettim 📱" |
| Cum | Build in public / metrik paylaşımı | "İlk 100 kullanıcıya ulaştık! 🎉" |

### 6.2 YouTube İçerik Planı

| Ay | Video | Uzunluk |
|----|-------|---------|
| 1 | "CorvusTunnel: AI Agent'larını Telefondan Kontrol Et" (demo) | 60-90 sn |
| 1 | "CorvusTunnel Kurulum Rehberi" (tutorial) | 3-5 dk |
| 2 | "CorvusTunnel vs Claude Remote Control" (karşılaştırma) | 5-7 dk |
| 3 | "Agent Performans Dashboard İncelemesi" | 3-5 dk |
| 4 | "Multi-Agent Orkestrasyon: Claude vs Codex Karşılaştır" | 5-7 dk |
| 5 | "Sesli Kontrol ile Hands-Free Kodlama" | 3-5 dk |

### 6.3 Hacker News Stratejisi

**İlk gönderi (Lansman):**
- Başlık: "Show HN: CorvusTunnel – Control AI coding agents from your phone (self-hosted Docker)"
- Zamanlama: Salı veya Çarşamba, 14:00-16:00 UTC (HN'de en yoğun saatler)
- Açıklama: Kısa, teknik, samimi — ne yaptığını, neden yaptığını anlat

**İkinci gönderi (Multi-Agent lansmanı, ~Ay 5):**
- Başlık: "Show HN: Multi-agent coding – Run Claude and Codex in parallel, pick the best result"

### 6.4 Reddit Stratejisi

| Subreddit | Yaklaşım |
|-----------|----------|
| r/selfhosted | "I built a self-hosted Docker tool for remote AI agent control" — bu topluluk Docker araçlarını SEVİYOR |
| r/programming | Demo video odaklı — teknik detaylar |
| r/devops | Güvenlik ve altyapı odaklı anlatım |
| r/ChatGPT, r/ClaudeAI | "I use this to control Codex/Claude from my phone" |

---

## 7. Anahtar Metrikler (KPI)

### İzlenmesi Gereken Metrikler

| Metrik | Ay 1 Hedef | Ay 3 Hedef | Ay 6 Hedef |
|--------|-----------|-----------|-----------|
| Docker Pull sayısı | 100 | 500 | 2.000 |
| Ücretsiz kullanıcı | 50 | 200 | 500 |
| Pro abone | 5 | 25 | 75 |
| MRR (Aylık Gelir) | $45 | $225 | $675 |
| Twitter takipçi | 100 | 500 | 2.000 |
| YouTube abone | 50 | 200 | 500 |
| Website aylık ziyaretçi | 500 | 2.000 | 5.000 |
| Hacker News upvote | 50+ | - | 100+ (2. gönderi) |

### Başabaş Analizi
- Aylık maliyetler: ~$200/ay (SMMM + Bağ-Kur + VPS)
- Müşteri başına net gelir: ~$8/ay (Paddle komisyonu sonrası)
- **Başabaş: ~25 Pro abone** (muhafazakâr tahminle Ay 3-4)

---

## 8. Risk Matrisi & Azaltma Planları

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| Claude/Codex kendi çözümlerini geliştiriyor | Yüksek | Yüksek | Agent-agnostik + multi-agent orkestrasyon ile farklılaş. Antigravity niche'ini hedefle |
| Hiçbir rakip olmayan multi-agent özelliğini birisi daha önce yapar | Orta | Orta | Hızlı lansman. One-tap + TTS ile ek farklar oluştur |
| PyArmor kırılır, kod sızar | Orta | Orta | Lisans doğrulama sunucudan bağımsız. Gelecekte phone-home ekle |
| Paddle Türk işletmeyi reddeder | Düşük | Yüksek | Erken başvur. Yedek: iyzico (yurt içi) + LemonSqueezy (yurt dışı) |
| Kimse kaydolmaz | Orta | Orta | Ücretsiz tier sürtünmeyi kaldırır. Demo video viralitesine odaklan |
| Google Antigravity'ye mobil erişim ekler | Orta | Yüksek | Multi-agent orkestrasyon ve TTS özeti gibi "fazlası" ile farklılaş |
| Solo developer burnout | Orta | Yüksek | MVP'yi küçük tut. Faz'ları takip et. Mükemmeliyetçilik yapma |

---

## 9. "Sevilir mi?" Testi — Kullanıcı Değer Senaryoları

### Senaryo 1: "Otobüste Kodlama"
> Ali otobüste, laptop'u çantasında. Telefonundan CorvusTunnel'ı açıyor. "Proje Durumu" kartında 3 başarısız test görüyor. One-tap ile "Testleri düzelt" butonuna basıyor. Agent çalışmaya başlıyor. 10 dk sonra agent bitiyor ve telefondan sesli özet geliyor: "3 test düzeltildi, hepsi geçti, 2 dosya değişti." Ali gülümsüyor.

### Senaryo 2: "Claude mu Codex mi?"
> Ayşe yeni bir feature eklemek istiyor ama hangi agent'ın daha iyi yazacağını bilmiyor. Multi-Agent Orkestrasyon ile ikisine de aynı prompt'u gönderiyor. 5 dk sonra iki farklı çözümü yan yana görüyor. Claude'un çözümü daha temiz, onu seçiyor. Tek dokunuşla ana projeye uygulanıyor.

### Senaryo 3: "Güvenlik Denetimi"
> Mehmet bir şirkette çalışıyor ve AI agent'larını monitör etmesi gerekiyor. CorvusTunnel'ın audit logları her komutu kaydediyor. IP ban mekanizması yetkisiz erişimleri engelliyor. Manuel onay sistemi kritik komutları onay bekletiyor. Tüm bunlar self-hosted Docker'da, şirket verisi dışarı çıkmıyor.

---

## 10. Lansman Öncesi Kontrol Listesi

### Hazır Olması GEREKEN Şeyler (Lansmandan Önce)

**Ürün:**
- [ ] Ücretsiz tier oturum limitleri çalışıyor
- [ ] One-Tap Workflow butonları UI'da mevcut (en az 5 şablon)
- [ ] Proje Durumu Özeti bağlantıda gösteriliyor
- [ ] Sesli Çıktı Özeti (TTS) agent bitirdiğinde çalışıyor
- [ ] Docker image Docker Hub'da (public, tagged)
- [ ] Paddle webhook → otomatik lisans üretimi çalışıyor

**İş:**
- [ ] Şahıs Şirketi kaydı tamamlandı (veya süreçte)
- [ ] Paddle hesabı doğrulandı ve production'da
- [ ] support@corvustunnel.com çalışıyor

**Web Sitesi:**
- [ ] corvustunnel.com landing page canlı
- [ ] Fiyatlandırma sayfası hazır (Free + Pro + "Team: Bize Ulaşın")
- [ ] Tüm hukuki belgeler yayında (/legal/*)
- [ ] Docs/FAQ sayfası mevcut

**Pazarlama:**
- [ ] Demo video YouTube'da
- [ ] Twitter/X hesabı aktif (@corvustunnel)
- [ ] Hacker News gönderisi taslağı hazır
- [ ] Reddit gönderisi taslakları hazır (3 subreddit)

---

## 11. Özet: Neden Başarılı Olacağız

| Faktör | Durum |
|--------|-------|
| **Pazar ihtiyacı var mı?** | ✅ Evet — büyük firmalar bile bu sorunu çözmeye çalışıyor |
| **Rakiplerden farklı mıyız?** | ✅ Evet — 8/8 özellik, en yakın rakip 4/8 |
| **Teknik olarak yapılabilir mi?** | ✅ Evet — tüm özellikler $0 maliyetle uygulanabilir |
| **Para kazanabilir miyiz?** | ✅ Evet — 25 Pro abone ile başabaş |
| **Zamanımız var mı?** | ✅ Evet — Antigravity mobil erişim boşluğu şu an açık |
| **Risk yönetilebilir mi?** | ✅ Evet — düşük maliyetler, fazlı yaklaşım |

> [!TIP]
> **Bugün yapılması gereken 3 şey:**
> 1. Twitter/X hesabı oluştur (@corvustunnel)
> 2. Paddle hesabı aç ve doğrulama sürecini başlat
> 3. SMMM ile iletişime geç
>
> Bu 3 adım kritik yolda — her biri gün alıyor ve paralelde devam etmeli.
