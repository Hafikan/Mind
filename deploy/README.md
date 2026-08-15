# Üretim yığını ve güvenlik sertleştirmesi

Beş riskin hepsi kapatıldı ve üretim yığını ayrı bir proje adı altında gerçekten ayağa kaldırılıp doğrulandı — mevcut veritabanına dokunulmadı (5 banka / 20 ekstre / 70 gider yerinde).

## Yapılanlar

**`Mind/Mind/settings.py`** — gizli anahtar, DEBUG, ALLOWED_HOSTS ve veritabanı bilgileri artık ortam değişkeninden okunuyor; bugünkü değerler geliştirme varsayılanı olarak duruyor, yani lokalde hiçbir şey değişmiyor. `DEBUG` kapalıyken:

- `DJANGO_SECRET_KEY` verilmemişse veya `DJANGO_ALLOWED_HOSTS` boşsa **import anında** `ImproperlyConfigured` fırlatıyor. Konteyner ilk istekte değil, açılışta ölüyor — depodaki anahtarla sessizce çalışma ihtimali kalmıyor. İkisini de test ettim, doğru mesajla patlıyor.
- Güvenli çerezler / SSL yönlendirmesi / HSTS `DJANGO_HTTPS` bayrağına bağlı, varsayılanı kapalı. Sertifikan yokken açmak seni dışarıda bırakırdı; sertifika kurunca tek satır değiştiriyorsun. `DJANGO_HTTPS=True` ile `manage.py check --deploy` **sıfır uyarı** veriyor.

**`compose.prod.yml`** (yeni) — geliştirme dosyasının üstüne bindirme değil, onun **yerine geçen** ayrı bir yığın; `-f` verdiğin an `docker-compose.yml` hiç okunmuyor, dolayısıyla `./Mind:/code` bind mount'u gibi geliştirme ayarları birleşme yoluyla sızamıyor. İçinde: gunicorn (3 worker), açılışta `migrate` + `collectstatic`, önünde nginx, Postgres'in **hiç yayımlanmış portu yok**. Yüklenen dosyalar `./Mind/media` bind mount'unda kalıyor — yedeklemesi ve `git` ile taşıması eskisi gibi.

**`deploy/nginx.conf`** (yeni) — `/static/` ve `/media/` doğrudan nginx'ten, gerisi gunicorn'a proxy. `X-Forwarded-Proto`'yu yazıyor, Django'nun `SECURE_PROXY_SSL_HEADER` ayarı onu okuyor.

**`.env.example`** (yeni) + `.env` gitignore'da. `requirements.txt`'e `gunicorn==26.0.0`.

**`docker-compose.yml`** — Postgres portu `127.0.0.1:5432:5432`'ye çekildi (testlerin host'tan çalışmaya devam ediyor, ağa çıkmıyor). İki ek düzeltme: `postgres` etiketi `postgres:18`'e sabitlendi (yüzen ana sürüm mevcut veri dizinini açamaz — taşıma sırasında tam da bunu konuşmuştuk) ve healthcheck `curl` yerine Python çağırıyor. Konteynerin haftalardır `(unhealthy)` görünmesinin sebebi buydu: imajda curl hiç yok.

## Doğrulama

Yığını `-p mind-prodtest` altında ayrı volume'lerle kaldırdım, sonra `down -v` ile sildim:

| Kontrol | Sonuç |
|---|---|
| `DEBUG=False` ile giriş sayfası (nginx üzerinden) | 200 |
| `/static/css/style.css` — nginx servis ediyor mu | 200, 27 KB, `Server: nginx` |
| `/media/bank_logo/TEB_LOGO.png` | 200, `image/png` |
| Yanlış `Host` başlığı | 400 (ALLOWED_HOSTS çalışıyor) |
| Postgres yayımlanmış port | yok |
| `check --deploy` (`DJANGO_HTTPS=True`) | 0 uyarı |
| Test paketi | 51/51 |

## Senin yapman gerekenler

Lokalde bir `.env` oluşturdum (gitignore'da) — üretim yığınını denemek istersen `HTTP_PORT=8081`, hostlar `localhost`. **Sunucuda bu dosyayı kopyalama**: orada `DJANGO_SECRET_KEY` ile `POSTGRES_PASSWORD`'ü yeniden üret, `DJANGO_ALLOWED_HOSTS`'a sunucunun adını yaz. Komutlar `.env.example` içinde.

Geliştirme tarafındaki healthcheck ve port değişikliği ancak konteyner yeniden oluşturulunca geçerli olur — hazır olduğunda `docker compose up -d`.

Taşıma adımları bir önceki mesajdaki gibi, sadece son adım değişiyor: `docker compose -f compose.prod.yml up -d --build`. Sıralamaya dikkat — `pg_restore`'u bundan **önce** çalıştır, yoksa açılıştaki `migrate` boş bir şema kurar ve restore çakışır.
