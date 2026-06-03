# CorvusTunnel — Yasal Analiz Raporu

> CorvusTunnel'ın ticari olarak geliştirilmesi ve satışını engelleyen/kısıtlayan yasal konuların kapsamlı değerlendirmesi.

---

## Yönetici Özeti

| Konu | Risk | Sonuç |
|------|------|-------|
| **AI CLI binary redistribüsyon** | 🔴 Yüksek | Düzeltme gerekli — entrypoint.sh'de runtime yüklemeye geçilmeli |
| **PyArmor ticari lisans** | 🟡 Orta | Alternatif obfuscation aracı kullanılacak |
| **pexpect terminal I/O** | 🟢 Düşük | Yasal — SSH istemcisi ile aynı kategori |
| **Cloudflare Quick Tunnel** | 🟢 Düşük | Kullanıcının sorumluluğu, Named Tunnel önerilmeli |
| **GDPR uyumu** | 🟢 Düşük | Minimal veri işleme, gizlilik politikası yeterli |
| **KVKK uyumu** | 🟢 Düşük | Aydınlatma Metni yazılacak |
| **AB AI Act** | 🟢 Düşük | CorvusTunnel AI sistemi değil |
| **Sorumluluk** | 🟡 Orta | ToS'da kapsamlı feragat gerekli |
| **Trademark** | 🟡 Orta | Agent isimlerini referans olarak kullan |
| **Türkiye yasaları** | 🟢 Engel yok | Tam destek + vergi avantajları |
| **Patent** | 🟢 Düşük | Orijinal uygulama, genel teknolojiler |

> [!IMPORTANT]
> **Genel sonuç: CorvusTunnel'ın geliştirilmesini ve satışını engelleyen HİÇBİR yasal engel bulunmamaktadır.** Tespit edilen riskler teknik düzeltmeler ve standart hukuki belgelerle yönetilebilir.

---

## 1. 🔴 AI Agent CLI Binary Redistribüsyonu — KRİTİK

### Mevcut Durum

[Dockerfile.prod](file:///c:/Users/alini/phdworks/CorvusTunnel/Dockerfile.prod) dosyasında (satır 39-41):

```dockerfile
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash
RUN curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh
RUN curl -fsSL https://claude.ai/install.sh | bash
```

Bu komutlar Docker **build-time**'da çalışır. Binary'ler Docker image layer'ına gömülür ve Docker Hub'a push edildiğinde her `docker pull` yapan kullanıcıya dağıtılır.

### Hukuki Sorun

| Agent | Lisans | Redistribüsyon Politikası |
|-------|--------|--------------------------|
| **Claude Code CLI** | Proprietary (Anthropic) | ❌ Yeniden dağıtım açıkça yasaklanmış |
| **Codex CLI** | Proprietary (OpenAI) | ❌ Üçüncü parti wrapping/redistribüsyon yasaklanmış |
| **Antigravity CLI** | Proprietary (Google) | ❌ Yetkisiz wrapper'lar yasaklanmış |

Her üç firma da:
- CLI binary'lerinin yeniden dağıtımını yasaklıyor
- Ticari ürünlerde resmi API kullanımını zorunlu tutuyor
- Yetkisiz wrapper'lara karşı hesap askıya alma hakkını saklı tutuyor

### Çözüm: Runtime Install Yaklaşımı

**Dockerfile.prod'dan** agent kurulum satırlarını kaldır. **entrypoint.sh'de** runtime'da yükle:

```bash
# entrypoint.sh'e eklenecek (container her başlatıldığında çalışır)
install_agents() {
    echo "🔄 Checking AI agents..."
    
    # Antigravity
    if ! command -v agy &>/dev/null; then
        echo "📦 Installing Antigravity CLI..."
        curl -fsSL https://antigravity.google/cli/install.sh | bash 2>/dev/null
    fi
    
    # Codex
    if ! command -v codex &>/dev/null; then
        echo "📦 Installing Codex CLI..."
        curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh 2>/dev/null
    fi
    
    # Claude
    if ! command -v claude &>/dev/null; then
        echo "📦 Installing Claude Code..."
        curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null
    fi
    
    echo "✅ AI agents ready."
}

install_agents
```

**Bu yaklaşımın avantajları:**
- ✅ Docker image'ında hiçbir üçüncü parti proprietary binary yok
- ✅ Redistribüsyon yok — kullanıcı kendi container'ında kendi indiriyor
- ✅ Her zaman en güncel versiyon yüklenir
- ✅ Image boyutu önemli ölçüde küçülür
- ⚠️ İlk başlatımda 1-2 dakika ek kurulum süresi (Docker volume ile cache'lenebilir)

> [!CAUTION]
> **Bu değişiklik lansmandan ÖNCE yapılmalıdır.** Mevcut Dockerfile ile Docker Hub'a push etmek yasal risk taşır.

---

## 2. 🟡 PyArmor Ticari Lisansı

### Mevcut Durum

[Dockerfile.prod](file:///c:/Users/alini/phdworks/CorvusTunnel/Dockerfile.prod) dosyasında (satır 4, 10-13):

```dockerfile
RUN pip install --no-cache-dir pyarmor
RUN pyarmor gen --output /obfuscated --recursive ...
```

### Hukuki Sorun

PyArmor'ın lisans koşulları:
- ❌ **Ücretsiz versiyon ticari kullanım için YASAK**
- ✅ Ticari lisans alınırsa: obfuscate edilmiş kodu dağıtabilirsin
- ✅ Son kullanıcıların PyArmor lisansına ihtiyacı yok
- 💰 Fiyat: ~$59-299 (tek seferlik, tier'a göre)

### Kullanıcının Kararı

**PyArmor kullanılmayacak.** Alternatif obfuscation araçları değerlendirilecek.

**Olası alternatifler:**
- **Cython** — Python kodunu C'ye derle (ücretsiz, açık kaynak)
- **Nuitka** — Python → standalone executable derleyici (MIT lisanslı)
- **cx_Freeze** / **PyInstaller** — executable oluşturma (ücretsiz)
- **Docker multi-stage build** ile kaynak kodu son image'dan hariç tut (zaten yapılıyor)

> [!TIP]
> En basit yaklaşım: Docker multi-stage build zaten kaynak kodu son image'dan çıkarıyor. Ek olarak Nuitka veya Cython ile kritik modülleri derleyerek ek koruma sağlanabilir.

---

## 3. 🟢 pexpect ile Terminal I/O — Yasal

### Analiz

CorvusTunnel'ın çekirdek mekanizması:

```python
# executor/term_session.py
child = pexpect.spawn(agent_command)  # Agent CLI'ı başlat
child.send(user_input)                # Kullanıcı girdisi gönder
output = child.read()                 # Çıktıyı oku
```

### Hukuki Değerlendirme

| Faktör | Durum |
|--------|-------|
| Agent kaynak kodu değiştiriliyor mu? | ❌ Hayır |
| Agent binary'si redistribute ediliyor mu? | ❌ Hayır (runtime install sonrası) |
| Agent API'si kullanılıyor mu? | ❌ Hayır — sadece terminal stdin/stdout |
| Kullanıcı kendi hesabıyla mı giriyor? | ✅ Evet |
| Bu bir SSH istemcisi/terminal emülatörü mü? | ✅ Evet — fonksiyonel olarak aynı |

**Sonuç:** pexpect ile terminal I/O yapmak, bir SSH istemcisi (Termius, Blink Shell) veya terminal multiplexer (tmux, screen) kullanmaktan hukuki olarak farklı değildir.

**Benzer ürünlerin varlığı:**
- CCGram (Telegram → tmux köprüsü) — açık kaynak, aktif olarak kullanılıyor
- CodeAgent Mobile — ticari ürün, benzer yaklaşım
- Junction Panel — açık kaynak, terminal kontrol paneli

Bu ürünlerin hiçbiri hukuki sorun yaşamamıştır.

> [!NOTE]
> **Risk:** AI agent sağlayıcıları gelecekte ToS'larını değiştirip "automated third-party interaction" yasaklayabilir. Bu risk tüm piyasadaki benzer araçlar için geçerlidir ve şu an için gerçekleşmemiştir.

---

## 4. 🟢 Cloudflare Quick Tunnel

### Analiz

[entrypoint.sh](file:///c:/Users/alini/phdworks/CorvusTunnel/entrypoint.sh) dosyasında (satır 17):

```bash
cloudflared tunnel --url http://localhost:8000 --no-autoupdate
```

### Hukuki Durum

| Konu | Durum |
|------|-------|
| **cloudflared lisansı** | ✅ Apache 2.0 — redistribüsyon serbest |
| **Quick Tunnel ToS** | ⚠️ Geçici/test amaçlı, production için tasarlanmamış |
| **Sorumluluk kime ait?** | ✅ Kullanıcıya — tunnel onun makinesinde açılıyor |
| **Cloudflare yeniden satış yasağı** | ✅ Geçerli değil — CloudFlare hizmetini yeniden satmıyoruz |

### Gerekli Aksiyonlar

1. ✅ cloudflared binary'si Docker image'ında kalabilir (Apache 2.0)
2. ⚠️ Dokümantasyonda belirt: "Quick Tunnel yalnızca geliştirme/test içindir"
3. ⚠️ Named Tunnel kurulumunu alternatif olarak belgele
4. ⚠️ ToS'da ekle: "Cloudflare hizmetlerinin kullanımı Cloudflare'in kendi koşullarına tabidir"
5. 🆕 corvustunnel.com domain'i ile Named Tunnel seçeneği sun (opsiyonel, Pro tier)

---

## 5. 🟢 GDPR Uyumu — Minimal Risk

### CorvusTunnel'ın Veri İşleme Profili

CorvusTunnel **self-hosted** bir ürün. Kullanıcı verileri senin sunucuna gelmez.

**Topladığın veriler:**

| Veri | Nerede | Amaç | GDPR Temeli |
|------|--------|------|-------------|
| E-posta adresi | Webhook sunucun | Lisans anahtarı teslimatı | Sözleşmenin ifası |
| IP adresi | Webhook sunucu logları | Güvenlik | Meşru menfaat |
| Ödeme bilgisi | Paddle (MoR) | Fatura | Paddle halleder |
| Web sitesi analitiği | Plausible (anonim) | İyileştirme | Çerez yok, rıza gerekmez |

**Toplamadığın veriler:**
- ❌ Kullanıcı komutları/promptları (kendi makinelerinde)
- ❌ AI çıktısı (kendi makinelerinde)
- ❌ Audit logları (kendi Docker container'larında)
- ❌ Kimlik doğrulama token'ları (yerel olarak üretilir)

### Gerekli Aksiyonlar

1. ✅ **Gizlilik Politikası** yaz — hangi verileri, neden, nasıl topladığını açıkla
2. ✅ **GDPR hakları** sağla — silme, erişim, taşınabilirlik (e-posta ile talep)
3. ✅ **Veri işleme kaydı** (ROPA) — basit belge tut
4. ✅ **Paddle DPA** — Paddle ile Data Processing Agreement mevcut (otomatik)
5. 🟢 **AB Temsilcisi** — küçük ölçekli, düşük riskli işleme olduğu için muhtemelen muaf

---

## 6. 🟢 KVKK Uyumu

### Gerekli Belgeler

| Belge | Zorunlu mu? | Dil |
|-------|------------|-----|
| KVKK Aydınlatma Metni | ✅ Evet | Türkçe zorunlu |
| Veri envanteri | ✅ Evet | Dahili belge |
| VERBİS kaydı | ❌ Henüz değil | Eşik altındasın |
| Açık rıza formu | ⚠️ Gerekirse | Türkçe |

### KVKK Aydınlatma Metni İçeriği

1. Veri Sorumlusu kimliği (Şahıs Şirketi olarak senin adın/unvanın)
2. İşlenen kişisel veriler ve işleme amaçları
3. Kişisel verilerin aktarıldığı taraflar (Paddle, Cloudflare)
4. Kişisel veri toplama yöntemi ve hukuki sebebi
5. Veri sahibinin hakları (KVKK Md. 11)
6. İletişim bilgileri

---

## 7. 🟢 AB AI Act — CorvusTunnel Kapsam Dışı

### Analiz

| Sınıflandırma Kriteri | CorvusTunnel |
|-----------------------|--------------|
| AI modeli mi? | ❌ Hayır — AI modeli sağlamıyor |
| AI sistemi mi? | ❌ Hayır — terminal arayüz aracı |
| AI üretici/sağlayıcı mı? | ❌ Hayır — kullanıcının kendi AI'ına arayüz |
| Yüksek riskli mi? | ❌ Hayır — istihdam, kritik altyapı vb. ile ilgisi yok |
| Şeffaflık yükümlülüğü var mı? | ❌ Hayır — AI içerik üretmiyor |

**Sonuç:** CorvusTunnel AB AI Act kapsamında **sınıflandırılmıyor**. AI Act'in hedefi model sağlayıcıları (Anthropic, OpenAI, Google), terminal arayüz araçları değil.

> [!NOTE]
> Gelecekte AI Act kapsamı genişleyebilir. Gelişmeleri takip et, ancak şu an endişelenecek bir durum yok.

---

## 8. 🟡 Sorumluluk Sınırlandırması — ÖNEMLİ

### Risk Senaryosu

CorvusTunnel, kullanıcının bilgisayarında AI tarafından üretilen komutları çalıştırır. Potansiyel zarar senaryoları:
- AI agent yanlışlıkla veritabanını silerse
- AI agent production sunucusunu bozarsa
- AI agent hassas dosyaları ifşa ederse

### Mevcut Korumalar (Kodda)

CorvusTunnel'da zaten güvenlik katmanları var:
- ✅ `ALLOWED_DIRS` ile workspace dışı erişim engelleniyor
- ✅ Manuel onay mekanizması (kritik komutlar için)
- ✅ Audit loglama (tüm komutlar kaydediliyor)
- ✅ IP banning (yetkisiz erişim engeli)

### Kullanım Koşulları'na (ToS) Eklenmesi GEREKEN Maddeler

```
1. GARANTİ FERAGATİ
   Yazılım "OLDUĞU GİBİ" (AS IS) sağlanmaktadır. 
   Herhangi bir garanti, açık veya zımni, verilmemektedir.

2. SORUMLULUK SINIRLANDIRMASI
   CorvusTunnel, yazılım aracılığıyla çalıştırılan AI tarafından 
   üretilen komutlardan kaynaklanabilecek hiçbir doğrudan, dolaylı, 
   arızi, özel veya cezai zarardan sorumlu tutulamaz.

3. KULLANICI SORUMLULUĞU
   Kullanıcı, AI agent'ların çalıştırdığı komutların sonuçlarından 
   tamamen kendisi sorumludur. CorvusTunnel bir terminal arayüz 
   aracıdır ve AI çıktılarını kontrol etmez.

4. MAKSİMUM SORUMLULUK
   CorvusTunnel'ın toplam sorumluluğu, son 12 ayda kullanıcının 
   ödediği toplam tutarı aşamaz.

5. TAZMİNAT
   Kullanıcı, CorvusTunnel'ı yazılımın kullanımından kaynaklanan 
   her türlü talep, dava ve masrafa karşı tazmin etmeyi kabul eder.
```

> [!CAUTION]
> **Bu maddelerin bir avukat tarafından Türk hukukuna uygunluğunun doğrulanması önerilir.** Özellikle sorumluluk sınırlandırması Türk Borçlar Kanunu açısından sınırlı olabilir.

---

## 9. 🟡 Trademark / Marka Riskleri

### Yapılması Gerekenler

| Konu | Yapılmalı | Yapılmamalı |
|------|-----------|-------------|
| Ürün adı | ✅ "CorvusTunnel" kullan | ❌ "Claude Controller" gibi agent ismi içeren isim |
| Pazarlama | ✅ "Supports Claude Code, Codex, and Antigravity" | ❌ "CorvusTunnel for Claude" |
| Logo | ✅ Kendi orijinal logon | ❌ Anthropic/OpenAI/Google logoları |
| Referans | ✅ "Third-party trademarks belong to their respective owners" | ❌ İzin almadan logo kullanma |

### Trademark Tescili

- ⚠️ "CorvusTunnel" markasını Türk Patent ve Marka Kurumu'na (TÜRKPATENT) tescil ettirmeni öneririm
- 💰 Maliyet: ~₺2.000-5.000 (online başvuru + vekil ücreti)
- ⏰ Süre: 6-12 ay
- 🎯 Fayda: Marka koruması, başkalarının aynı ismi kullanmasını engeller

---

## 10. 🟢 Python Bağımlılıkları — Tümü Temiz

| Paket | Lisans | Ticari Kullanım | Atıf Gerekli mi? |
|-------|--------|----------------|------------------|
| FastAPI | MIT | ✅ Serbest | Evet (lisans metni) |
| Uvicorn | BSD 3-Clause | ✅ Serbest | Evet (lisans metni) |
| pexpect | ISC | ✅ Serbest | Evet (lisans metni) |
| httpx | BSD 3-Clause | ✅ Serbest | Evet (lisans metni) |
| Pydantic | MIT | ✅ Serbest | Evet (lisans metni) |
| slowapi | MIT | ✅ Serbest | Evet (lisans metni) |
| qrcode | MIT-like | ✅ Serbest | Evet (lisans metni) |
| cloudflared | Apache 2.0 | ✅ Serbest | Evet (lisans metni) |

**Aksiyon:** Web sitesinde `/legal/open-source` sayfası oluştur ve tüm lisans atıflarını listele.

---

## 11. 🟢 Türkiye Yasaları — Tam Destek

### Yazılım İhracatı

| Konu | Durum |
|------|-------|
| Yazılım ihracatı izni | ✅ Özel izin/ruhsat gerekmiyor |
| Kripto/şifreleme ihracatı kısıtlaması | ✅ Geçerli değil — CorvusTunnel kripto silahı/ürünü değil |
| İhracat kontrol listesi | ✅ Yazılım aracı, kontrol listesinde değil |
| Döviz kazanma zorunluluğu | ⚠️ Vergi indiriminden faydalanmak için ödeme Türkiye'deki bankaya gelmeli |

### Vergi Avantajları

| Avantaj | Detay |
|---------|-------|
| KDV istisnası | %0 — hizmet ihracatı KDV'den muaf |
| Gelir Vergisi indirimi | %100 — 2026 düzenleme ile ihracat geliri vergisiz |
| Genç Girişimci desteği | Yıllık ₺400K gelir vergisi istisnası (3 yıl, uygunluk kontrolü gerekir) |

### Fikri Mülkiyet

- ✅ Türkiye'de yazılım otomatik olarak telif hakkı ile korunur (Fikir ve Sanat Eserleri Kanunu)
- ✅ Kayıt zorunluluğu yok (ama ispat için isteğe bağlı kayıt yapılabilir)
- ✅ Berne Sözleşmesi üyesi — uluslararası koruma geçerli

---

## 12. Docker Hub Dağıtımı — Sorun Yok

| Konu | Durum |
|------|-------|
| Proprietary image dağıtımı | ✅ Docker Hub'da serbest |
| Lisans koşullarını sen belirlersin | ✅ EULA ile |
| Public/private repository | ✅ İkisi de mümkün |
| Docker Desktop ticari lisansı | ⚠️ Kullanıcının sorumluluğu (büyük şirketlerde ücretli) |

---

## 13. Yapılacaklar Listesi — Öncelik Sırasına Göre

### 🔴 Lansmandan ÖNCE (Zorunlu)

1. **[ ] Dockerfile.prod'dan AI agent install satırlarını kaldır → entrypoint.sh'e taşı**
2. **[ ] PyArmor yerine alternatif obfuscation çözümü belirle**
3. **[ ] Kullanım Koşulları (ToS) taslağı yaz — sorumluluk sınırlandırması dahil**
4. **[ ] Gizlilik Politikası (Privacy Policy) yaz**
5. **[ ] KVKK Aydınlatma Metni yaz (Türkçe)**
6. **[ ] EULA taslağı yaz**

### 🟡 İlk Ay İçinde (Önerilen)

7. **[ ] İade Politikası (Refund Policy) yaz**
8. **[ ] Kabul Edilebilir Kullanım Politikası (AUP) yaz**
9. **[ ] Açık kaynak lisans atıf sayfası oluştur (/legal/open-source)**
10. **[ ] Named Tunnel kurulum rehberi dokümantasyona ekle**
11. **[ ] Dokümantasyonda Quick Tunnel uyarısı ekle**

### 🟢 Gelecekte (İsteğe Bağlı)

12. **[ ] TÜRKPATENT'e marka tescil başvurusu yap**
13. **[ ] Avukat ile ToS/KVKK/EULA incelemesi yap (~₺2.000-5.000)**
14. **[ ] VERBİS kaydı (kullanıcı sayısı eşiği aşıldığında)**
15. **[ ] AB temsilcisi atama (AB müşteri sayısı artarsa)**

---

## 14. Avukat İncelemesi Gereken Konular

Aşağıdaki konular için bir avukata danışılması **önerilir** (zorunlu değil ama güvenli):

| Konu | Neden | Tahmini Maliyet |
|------|-------|----------------|
| ToS sorumluluk maddeleri | Türk Borçlar Kanunu uyumu | ₺1.000-2.000 |
| KVKK Aydınlatma Metni | Yasal format ve dil uyumu | ₺500-1.500 |
| EULA hükümleri | Lisans koşullarının geçerliliği | ₺1.000-2.000 |
| Marka tescili | TÜRKPATENT başvuru süreci | ₺2.000-5.000 |
| **TOPLAM** | | **₺4.500-10.500** |

> [!TIP]
> **Bu inceleme lansmanı engellememeli.** Taslakları kendin yaz, lansman yap, ardından avukat incelemesini yaptır ve gerekli düzeltmeleri sonra uygula. Birçok startup bu yaklaşımı izler.

---

## 15. Sonuç

### CorvusTunnel'ı geliştirmeni ve satmanı engelleyen yasal engel var mı?

# HAYIR.

**İki teknik düzeltme gerekiyor:**
1. AI Agent CLI'larını Docker image'ından çıkar → runtime install yap
2. PyArmor yerine alternatif obfuscation aracı kullan

**Standart hukuki belgeler gerekiyor:**
- ToS, Privacy Policy, KVKK Aydınlatma Metni, EULA, AUP, Refund Policy

**Hepsi yapılabilir ve hiçbiri lansman için engel teşkil etmiyor.**

> [!IMPORTANT]
> **Hemen yapılması gereken en önemli şey:** [Dockerfile.prod](file:///c:/Users/alini/phdworks/CorvusTunnel/Dockerfile.prod) dosyasındaki AI agent install satırlarını entrypoint.sh'e taşımak. Bu değişiklik 30 dakikada tamamlanabilir ve en büyük yasal riski ortadan kaldırır.
