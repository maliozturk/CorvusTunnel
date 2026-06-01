# CorvusTunnel 🦅

**Telefonundan bilgisayarındaki AI kodlama asistanını güvenli şekilde kontrol et.**

CorvusTunnel, Cloudflare Quick Tunnel üzerinden uzaktan güvenli komut göndermenizi sağlayan bir FastAPI tabanlı remote agent kontrol sistemidir.

## ✨ Özellikler

- 📱 **Mobil-Responsive Chat UI** — Telefondan komut gönder, durumu izle
- 🔐 **Çok Katmanlı Güvenlik** — Bearer token + localhost-only onay
- ⏳ **Manuel Onay** — Her komut masaüstü bildirimiyle onay bekler
- 📊 **Real-time Streaming** — SSE ile canlı çıktı izleme
- 📝 **Audit Log** — Her işlem JSONL formatında loglanır
- 🌐 **Cloudflare Quick Tunnel** — Ücretsiz, rastgele domain, port açmadan

## 🏗️ Mimari

```
[Telefon]
    │ HTTPS
    ▼
[Cloudflare Edge]
    │ Quick Tunnel (*.trycloudflare.com)
    ▼
[cloudflared → localhost:8000]
    │
    ├── Chat UI (/)
    ├── POST /api/prompt (Bearer Auth)
    ├── GET  /api/status/{id}
    ├── GET  /api/jobs
    └── GET  /api/stream/{id} (SSE)

[localhost:8001 — Sadece Yerel]
    ├── POST /approve/{id}
    ├── POST /reject/{id}
    └── GET  /pending
```

## 🚀 Kurulum

### 1. Python Bağımlılıkları

```bash
cd CorvusTunnel
pip install -r requirements.txt
```

### 2. Konfigürasyon

```bash
# .env dosyası oluştur
copy .env.example .env

# Token oluştur (Python ile)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# .env dosyasında AGENT_TOKEN değerini güncelle
```

### 3. Çalıştır

```bash
python main.py
```

İki server başlayacak:
- `http://0.0.0.0:8000` — Public API + Chat UI
- `http://127.0.0.1:8001` — Local onay API

### 4. Cloudflare Tunnel Başlat

Ayrı bir terminalde:

```bash
# cloudflared kurulu değilse:
# https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

cloudflared tunnel --url http://localhost:8000
```

Çıktıda rastgele bir URL göreceksin:
```
+----------------------------+
|  Your URL: https://xxx-yyy-zzz.trycloudflare.com  |
+----------------------------+
```

Bu URL'yi telefonundan aç, token'ı gir, komut göndermeye başla!

## 📱 Kullanım

1. Telefonda tunnel URL'sini aç
2. Bearer token ile giriş yap
3. Chat alanına komut/soru yaz
4. Bilgisayarında onay bildirimi çıkacak
5. Terminalde `curl -X POST http://localhost:8001/approve/<job_id>` ile onayla
6. Sonucu telefondan real-time izle

### Onay Komutları (Bilgisayar Terminali)

```bash
# Bekleyen işleri gör
curl http://localhost:8001/pending

# Onayla
curl -X POST http://localhost:8001/approve/JOB_ID

# Reddet
curl -X POST http://localhost:8001/reject/JOB_ID

# Audit loglarını gör
curl http://localhost:8001/audit
```

## 🔒 Güvenlik

### Aktif Korumalar

| Katman | Açıklama |
|--------|----------|
| Bearer Token | 64+ karakter, timing-safe karşılaştırma |
| Localhost-only Onay | approve/reject sadece 127.0.0.1 |
| Komut Allowlist | Sadece izin verilen executor hedefleri |
| Manuel Onay | Varsayılan: her iş onay bekler |
| Audit Log | Her işlem JSONL'de loglanır |
| Ortam Temizliği | Subprocess'e hassas env var gönderilmez |
| Çıktı Limiti | Max 5000 karakter, 5 dakika timeout |

### ⚠️ Uyarılar

- Quick Tunnel modunda Cloudflare Access **aktif değil** — Bearer token tek auth katmanıdır
- Token'ı güçlü tut (64+ karakter, `secrets.token_urlsafe`)
- Token'ı git'e commit etme
- `require_approval=True` varsayılanını değiştirme (başlangıçta)
- Onay endpoint'ini (`/approve`) public porta taşıma

## 📁 Proje Yapısı

```
CorvusTunnel/
├── main.py               # Dual-server başlatıcı
├── public_app.py          # Public FastAPI (port 8000)
├── internal_app.py        # Internal FastAPI (port 8001)
├── config/
│   ├── settings.py        # Pydantic konfigürasyon
│   └── allowlist.py       # Komut güvenlik filtreleri
├── auth/
│   ├── bearer.py          # Token doğrulama
│   └── dependencies.py    # FastAPI auth dependency'leri
├── models/
│   ├── requests.py        # Request modelleri
│   └── responses.py       # Response modelleri
├── executor/
│   ├── base.py            # Abstract executor
│   └── antigravity.py     # Antigravity CLI executor
├── queue/
│   ├── manager.py         # Job queue yönetimi
│   └── notifier.py        # Masaüstü bildirimleri
├── audit/
│   └── logger.py          # JSONL audit logger
├── routers/
│   ├── public.py          # Public API endpoints
│   └── internal.py        # Local-only endpoints
└── static/
    └── index.html         # Mobil chat arayüzü
```

## 🛠️ API Referansı

### Public Endpoints (`:8000`)

| Method | Path | Auth | Açıklama |
|--------|------|------|----------|
| `GET` | `/` | — | Chat UI |
| `POST` | `/api/prompt` | Bearer | Komut gönder |
| `GET` | `/api/status/{id}` | Bearer | İş durumu |
| `GET` | `/api/jobs` | Bearer | Tüm işler |
| `GET` | `/api/stream/{id}` | Query token | SSE stream |
| `GET` | `/api/health` | — | Sağlık kontrolü |

### Internal Endpoints (`:8001`, localhost only)

| Method | Path | Açıklama |
|--------|------|----------|
| `POST` | `/approve/{id}` | Onayla |
| `POST` | `/reject/{id}` | Reddet |
| `GET` | `/pending` | Bekleyen işler |
| `GET` | `/audit` | Audit logları |

## 📄 Lisans

MIT
