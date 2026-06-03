# CorvusTunnel — Eleştiri Savunma Rehberi

> Hacker News, Reddit ve Twitter'da karşılaşılacak potansiyel eleştirilere karşı sözel cevaplar, teknik savunmalar ve kod düzeltmeleri.

---

## Stratejik Kararlar Özeti

| Karar | Sonuç |
|-------|-------|
| **Lisans modeli** | ✅ Open Core (core açık kaynak, premium kapalı) |
| **CORS** | ✅ Dinamik env variable ile kısıtlanacak |
| **Grace period** | ✅ 5dk → 15dk, env variable ile ayarlanabilir |
| **IP ban** | ✅ Docker volume'a persist edilecek |
| **Docker AI agents** | ✅ Build-time → runtime install'a geçilecek |
| **2FA/TOTP** | ⏳ Sonraya — Pro tier özelliği olarak gelecekte |
| **Singleton session** | ⏳ MVP'de kalır, Multi-Agent ile dict-based'e geçilecek |

---

## Kategori 1 — "Neden Var?" Eleştirileri

### 1. 🗣️ *"Bu sadece SSH + Termius. Niye $9/ay ödeyeyim?"*

**Sözel cevap:**
> "CorvusTunnel sadece terminal değil. SSH ile yapamadığın şeyler:
> - One-tap iş akışları (butonla 'Test yaz' de)
> - Agent bitirince sesli özet alırsın
> - İki farklı agent'ı aynı prompt'la karşılaştırabilirsin
> - Audit log (kim ne zaman ne çalıştırdı)
> - QR ile 5 saniyede bağlan — SSH key yönetimi yok
> - Oturum limitli ücretsiz tier — dene, beğen, öde."

**Teknik savunma:**
- Landing page'de **"CorvusTunnel vs SSH"** karşılaştırma tablosu:

| Özellik | SSH + Termius | CorvusTunnel |
|---------|---------------|-------------|
| QR ile 5sn kurulum | ❌ | ✅ |
| One-tap workflow | ❌ | ✅ |
| Sesli çıktı özeti | ❌ | ✅ |
| Multi-agent karşılaştırma | ❌ | ✅ |
| Audit loglama | ❌ | ✅ |
| IP ban + güvenlik | ❌ | ✅ |
| Agent seçici UI | ❌ | ✅ |
| Reconnect + replay buffer | Manuel | Otomatik |

---

### 2. 🗣️ *"Claude zaten Remote Control sunuyor. Neden gerekli?"*

**Sözel cevap:**
> "Claude RC sadece Claude için çalışır ve sadece Pro plan içinde. CorvusTunnel:
> - **Agent-agnostik** — Claude + Codex + Antigravity aynı arayüzden
> - **Self-hosted** — verilerin senin sunucunda
> - **Multi-agent orkestrasyon** — iki agent'ı karşılaştır
> - **Audit log + IP ban** — kurumsal güvenlik
> - Claude RC kapanırsa elinizde hiçbir şey kalmaz. CorvusTunnel sizin Docker'ınızda."

**Teknik savunma:**
- Demo videoda 3 farklı agent'ı tek arayüzden göster
- Landing page'de **"CorvusTunnel vs Claude RC vs Codex Mobile"** tablosu

---

### 3. 🗣️ *"Kim telefondan kod yazdırır ki?"*

**Sözel cevap:**
> "Sen kod yazmıyorsun — AI yazıyor, sen yönetiyorsun. Fark bu.
> - 📱 Otobüstesin, AI 30 dk'lık bir iş yapıyor, ilerlemesini izliyorsun
> - 📱 Gece yatakta, son test sonuçlarını kontrol ediyorsun
> - 📱 Toplantıdasın, agent bitirdiğinde sesli özet alıyorsun
> - Bu 'kod yazma' değil, 'AI babysitting' — ve bu gerçek bir sorun."

**Teknik savunma:**
- Landing page'de kullanım senaryoları (GIF/video)
- "Use Cases" bölümü: otobüs, yürüyüş, toplantı, gece

---

## Kategori 2 — Güvenlik Eleştirileri

### 4. 🗣️ *"WebSocket üzerinden terminal açmak reverse shell'den farksız"*

**Sözel cevap:**
> "CorvusTunnel bir reverse shell değil. 10 katmanlı güvenlik modeli var:
> 1. Cloudflare Tunnel — port açmıyorsun, outbound connection
> 2. One-time boot token — QR ile tek kullanımlık, timing-safe
> 3. Session token + IP binding — claim eden IP'den başka kimse bağlanamaz
> 4. One-time WS ticket (30s TTL, IP-bound) — WebSocket auth
> 5. IP ban (5 başarısız deneme → 15 dk ban)
> 6. Rate limiting (tüm endpoint'lerde)
> 7. Input throttling (flood koruması)
> 8. ALLOWED_DIRS — workspace dışına erişim engelli
> 9. Security headers (CSP, HSTS, X-Frame-Options)
> 10. Forensic audit logging (her input/output kaydediliyor)
>
> Bu SSH'den fazla katman."

**Teknik savunma:**
- `/security` sayfasında güvenlik mimarisini detaylı açıkla
- Open Core ile güvenlik kodu tamamen audit edilebilir
- Security headers listesini göster

---

### 5. 🗣️ *"Token QR kodla geliyor — birisi omzumun üstünden bakarsa?"*

**Sözel cevap:**
> "QR kodu tek kullanımlık boot token taşır. Bir kere taranıp claim edildikten sonra ölür — aynı QR'le tekrar bağlanamaz kimse. Üstelik session token IP'ye bağlı — farklı IP'den gelen istek reddedilir."

**Mevcut kod koruması:**
- ✅ `claim_boot_token()` tek seferlik ([bearer.py:60-86](file:///c:/Users/alini/phdworks/CorvusTunnel/auth/bearer.py#L60-L86))
- ✅ IP binding aktif ([bearer.py:82-84](file:///c:/Users/alini/phdworks/CorvusTunnel/auth/bearer.py#L82-L84))
- ✅ Timing-safe comparison ([bearer.py:74](file:///c:/Users/alini/phdworks/CorvusTunnel/auth/bearer.py#L74))

---

### 6. 🗣️ *"CORS allow_origins=* ciddi mi?"*

> [!WARNING]
> **Bu gerçek bir zayıflık.** Düzeltme gerekli.

**Mevcut kod** ([public_app.py:48](file:///c:/Users/alini/phdworks/CorvusTunnel/public_app.py#L48)):
```python
allow_origins=["*"],
```

**Düzeltme:**
```python
import os
CORS_ORIGINS = os.getenv("CORS_ORIGIN", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Sözel savunma (düzeltmeden önce bile):**
> "`allow_credentials=False` olduğu için cookie/session hijack riski yok. Auth Bearer token ile header'da yapılıyor, CORS bunu engellemez. Ancak yine de CORS_ORIGIN env variable ile kısıtlama desteği eklendi."

---

### 7. 🗣️ *"2FA/MFA yok. 2026'da tek token ile güvenlik mi?"*

**Sözel cevap:**
> "Mevcut güvenlik katmanları:
> - One-time boot token (bilgi faktörü)
> - IP binding (ağ faktörü — fiilen ikinci faktör)
> - Cloudflare Tunnel (ek ağ koruması)
> - Self-hosted Docker (fiziksel erişim gerekli)
>
> TOTP 2FA desteği yol haritamızda ve Pro tier'da gelecek."

**Gelecek plan:**
- pyotp ile TOTP implementasyonu (~1-2 gün iş)
- Google Authenticator / Authy uyumlu
- Pro tier özelliği olarak

---

## Kategori 3 — Teknik Eleştiriler

### 8. 🗣️ *"Tek TerminalSession singleton — aynı anda 2 proje açamam"*

**Sözel cevap:**
> "CorvusTunnel kişisel kullanım için tasarlandı — tek kullanıcı, tek oturum. Telefondan 2 projeyi aynı anda yönetmek gerçekçi bir senaryo değil. Ancak Multi-Agent özelliğinde paralel session desteği gelecek."

**Mevcut kod:** Singleton ([term_session.py:378-388](file:///c:/Users/alini/phdworks/CorvusTunnel/executor/term_session.py#L378-L388))

**Gelecek düzeltme:**
```python
# Dict-based session yönetimi (Multi-Agent ile birlikte)
_sessions: Dict[str, TerminalSession] = {}

def get_terminal_session(work_dir: str = None) -> TerminalSession:
    if work_dir and work_dir in _sessions:
        return _sessions[work_dir]
    session = TerminalSession()
    if work_dir:
        _sessions[work_dir] = session
    return session
```

---

### 9. 🗣️ *"In-memory IP ban — container restart'ta sıfırlanıyor"*

**Sözel cevap:**
> "Container restart = yeni oturum = yeni token. Eski token geçersiz, saldırgan tekrar denese de sıfırdan başlar."

**Düzeltme (planlandı):**
```python
import json
from pathlib import Path

BAN_FILE = Path("/workspace/.corvus/ip_bans.json")

def _save_bans(self):
    BAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"bans": {ip: exp for ip, exp in self._bans.items()}}
    BAN_FILE.write_text(json.dumps(data))

def _load_bans(self):
    if BAN_FILE.exists():
        data = json.loads(BAN_FILE.read_text())
        now = time.monotonic()
        # Sadece hala geçerli olanları yükle
        self._bans = {ip: exp for ip, exp in data.get("bans", {}).items() if exp > now}
```

---

### 10. 🗣️ *"Grace period 5 dk — telefon cebimde 6 dk kalsa terminal ölüyor"*

**Düzeltme:**

```python
# Eski:
GRACE_PERIOD_S = 300  # 5 minutes

# Yeni:
GRACE_PERIOD_S = int(os.getenv("GRACE_PERIOD", 900))  # default 15 min
```

**Sözel cevap:**
> "Grace period artık 15 dakika (varsayılan) ve GRACE_PERIOD env variable ile ayarlanabilir. Ayrıca reconnect ettiğinizde 64KB replay buffer ile kaldığınız yerden devam edersiniz."

---

## Kategori 4 — İş Modeli Eleştirileri

### 11. 🗣️ *"Solo developer, yarın bırakırsan ne olacak?"*

**Sözel cevap:**
> "CorvusTunnel self-hosted ve Open Core:
> - Core açık kaynak — topluluk sürdürebilir
> - Docker image'lar Docker Hub'da kalır
> - Lisans sunucusu olmadan çalışır (offline validation)
> - Verileriniz tamamen sizin sunucunuzda
> - Bu Figma gibi SaaS değil — sizin makinenizde çalışıyor"

**Teknik savunma:**
- Perpetual license: abonelik bitse bile son indirdiğin versiyon çalışmaya devam eder
- Public roadmap (corvustunnel.com/roadmap)
- Open Core = community can fork and maintain

---

### 12. 🗣️ *"Açık kaynak değil, güvenlik audit'i yapamıyorum"*

**Sözel cevap (YENİ — Open Core kararı ile):**
> "CorvusTunnel Open Core modelini kullanıyor. Tüm güvenlik katmanları — auth, IP ban, rate limiting, ALLOWED_DIRS sandboxing, audit logging — **tamamen açık kaynak** ve GitHub'da audit edilebilir. Premium özellikler (multi-agent, dashboard, TTS) ayrı bir modülde."

**Teknik savunma:**
- GitHub'da `corvustunnel-core` reposu
- `/security` sayfasında güvenlik mimarisi
- security@corvustunnel.com disclosure policy
- Bug bounty: "güvenlik açığı bulursan bildir → ücretsiz Pro lisans"

---

### 13. 🗣️ *"Bu bir AI wrapper — AI slop."*

**Sözel cevap:**
> "CorvusTunnel bir AI wrapper değil. Tek satır AI kodu yok. Hiçbir LLM API'si çağrılmıyor.
> Bu bir **terminal arayüz aracı** — pexpect ile PTY yönetimi, WebSocket ile real-time streaming, Docker ile izolasyon.
> GitHub'a bak — hiç GPT, Claude veya Gemini API call'u yok."

**Teknik savunma:**
- HN başlığında "AI" kelimesini baş karakter olarak kullanma
- Doğru başlık: *"Show HN: CorvusTunnel – Control AI coding agents from your phone (self-hosted Docker)"*
- Yanlış başlık: *"AI-powered mobile coding assistant"*

---

## Yapılması Gereken Kod Düzeltmeleri

### 🔴 Lansmandan Önce (Zorunlu)

| # | Dosya | Değişiklik | Süre |
|---|-------|-----------|------|
| 1 | [public_app.py](file:///c:/Users/alini/phdworks/CorvusTunnel/public_app.py) | CORS `allow_origins` → env variable | 15 dk |
| 2 | [term_session.py](file:///c:/Users/alini/phdworks/CorvusTunnel/executor/term_session.py) | Grace period 5dk → 15dk + env variable | 15 dk |
| 3 | [Dockerfile.prod](file:///c:/Users/alini/phdworks/CorvusTunnel/Dockerfile.prod) | AI agent install → entrypoint.sh runtime | 30 dk |
| 4 | [entrypoint.sh](file:///c:/Users/alini/phdworks/CorvusTunnel/entrypoint.sh) | Runtime agent install fonksiyonu ekle | 30 dk |

### 🟡 İlk Ay İçinde (Önerilen)

| # | Dosya | Değişiklik | Süre |
|---|-------|-----------|------|
| 5 | [ip_ban.py](file:///c:/Users/alini/phdworks/CorvusTunnel/middleware/ip_ban.py) | Ban'leri JSON dosyaya persist et | 1 saat |
| 6 | Yeni: `/security` page | Güvenlik mimarisi dokümantasyonu | 2 saat |
| 7 | Yeni: `SECURITY.md` | Security disclosure policy | 30 dk |
| 8 | Yeni: `LICENSE` (core repo) | MIT veya Apache 2.0 lisansı | 15 dk |

### 🟢 Gelecekte

| # | Dosya | Değişiklik | Süre |
|---|-------|-----------|------|
| 9 | [term_session.py](file:///c:/Users/alini/phdworks/CorvusTunnel/executor/term_session.py) | Dict-based multi-session | 1 hafta |
| 10 | Yeni: `auth/totp.py` | Opsiyonel TOTP 2FA (Pro) | 2 gün |
| 11 | Yeni: repo split | corvustunnel-core + corvustunnel-pro | 1 hafta |

---

## Landing Page Savunma İçeriği

Landing page'de şu bölümler olmalı (eleştirilere karşı proaktif savunma):

### 1. "Security Model" Bölümü
10 güvenlik katmanını listele ve görselleştir:
```
Cloudflare Tunnel → One-time Token → IP Binding → WS Ticket →
IP Ban → Rate Limit → Input Throttle → ALLOWED_DIRS → 
Security Headers → Audit Logging
```

### 2. "Why CorvusTunnel?" Karşılaştırma Tablosu
| Özellik | SSH | Claude RC | Codex Mobile | CorvusTunnel |
|---------|-----|-----------|-------------|-------------|
| Agent-agnostik | ✅ | ❌ | ❌ | ✅ |
| Self-hosted | ✅ | ❌ | ❌ | ✅ |
| QR kurulum | ❌ | ✅ | ✅ | ✅ |
| One-tap workflow | ❌ | ❌ | ❌ | ✅ |
| Multi-agent | ❌ | ❌ | ❌ | ✅ |
| Sesli özet | ❌ | ❌ | ❌ | ✅ |
| Audit log | ❌ | ❌ | ❌ | ✅ |
| Açık kaynak | ✅ | ❌ | ❌ | ✅ (core) |

### 3. "Use Cases" GIF/Video Bölümü
- 📱 Otobüste proje durumu kontrolü
- 📱 Yürürken sesli özet alma
- 📱 Toplantıda agent izleme
- 📱 Gece son test sonuçlarını kontrol

### 4. "Open Source" Bölümü
- GitHub linki (corvustunnel-core)
- Star count badge
- "Audit our security code" mesajı
- Contribution rehberi linki

### 5. "FAQ" Bölümü
Her eleştiriyi proaktif olarak cevaplayacak soru-cevaplar.

---

## HN / Reddit Gönderi Stratejisi

### Hacker News Show HN Başlığı

**✅ Doğru:**
> Show HN: CorvusTunnel – Control AI coding agents from your phone (self-hosted, open core)

**❌ Yanlış:**
> Show HN: AI-powered mobile coding assistant for remote development

### HN Gönderi Açıklaması (Taslak)

```
Hey HN,

I built CorvusTunnel because I was tired of babysitting AI coding agents 
at my desk. I wanted to check on my agent from my phone while commuting.

What it does:
- Self-hosted Docker container with a mobile-optimized terminal UI
- QR code to connect — no SSH keys, no port forwarding
- Works with any CLI agent (Claude Code, Codex, Antigravity)
- 10-layer security model (one-time tokens, IP binding, audit logging)
- Multi-agent comparison: run two agents on the same prompt, pick the best result

Core is open source: [GitHub link]
Pro features (multi-agent, one-tap workflows, TTS summary): $9/mo

Happy to answer questions about the security model or architecture.
```

### Reddit Gönderi Stratejisi

| Subreddit | Yaklaşım | Eleştiri beklentisi |
|-----------|----------|-------------------|
| r/selfhosted | Docker + self-hosted vurgusu | "Neden SSH değil?" → karşılaştırma tablosu |
| r/programming | Teknik detay, güvenlik modeli | "Güvenlik audit?" → open core, /security sayfası |
| r/devops | Infrastructure, audit loglama | "Production'da mı?" → use case'ler |
| r/ClaudeAI | Claude Remote Control alternatifi | "Claude RC var" → agent-agnostik, multi-agent |

---

## Eleştiri Cevaplama Kuralları

1. **Savunmaya geçme, dinle.** "That's a great point. Here's how we handle it..."
2. **Teknik ol.** "Our auth uses `hmac.compare_digest()` with timing-safe comparison..."
3. **Açık ol.** "You're right, CORS was `*`. We've fixed it to be configurable via env."
4. **Satmaya çalışma.** "If this isn't for you, that's totally fine. Our target is..."
5. **Kodu göster.** "Check our security module: [GitHub link to auth/bearer.py]"
