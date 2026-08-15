# Mind

Tek kullanıcılık kişisel yönetim paneli: harcama/kredi kartı takibi, kariyer yol haritası ve markdown not defteri tek bir Django uygulamasında. Kendi sunucunda çalışacak şekilde tasarlandı — dışarıya açık bir servis değil, kendi verini kendi makinende tutan bir panel.

**Yığın:** Django 6.0 + Django REST Framework · PostgreSQL 18 · Docker Compose · üretimde gunicorn + nginx.

## Modüller

| Modül | URL | Ne yapar |
|---|---|---|
| **Accounts** | `/` | Özel kullanıcı modeli (`AppUser`), giriş/çıkış, profil (avatar + telefon). Tüm sayfalar giriş ister. |
| **ExpenseTracker** | `/tracker/` | Gider, kategori, gelir, alışveriş, kredi kartı ekstreleri, taksitli krediler ve özet gösterge paneli. |
| **CareerPath** | `/career/` | Faz × kategori matrisi olarak kariyer yol haritası, görevler, kaynaklar ve konu bazlı "deep dive" sayfaları. |
| **Notebook** | `/notebook/` | Klasörlü markdown notlar, `[[wiki-link]]` bağlantıları ve `#tag`'ler, arama. |

Her modül aynı deseni izler: sayfalar sunucu tarafında render edilen HTML (`templates/`), veri ise aynı uygulamanın `api/` altındaki DRF endpoint'lerinden vanilla JS ile okunup yazılır. Ayrı bir frontend build adımı yok.

## Kredi kartı ekstre modeli

Projenin en çok kuralı olan yeri burası, kısaca:

- Bir **`Banks`** kaydı = bir kredi kartı (limit + hesap kesim günü). Bir **`Debts`** kaydı = o kartın **bir dönemlik ekstresi**.
- **Devir zinciri:** bir ekstrenin devri, önceki ekstrenin kalan bakiyesidir (`toplam borç − ödenen`). Zincir kartın tüm geçmişi üzerinden yürütülür, ay filtresi uygulanmış listelerde de doğru devir çıkar.
- **Dönem ataması takvim ayı kuralıdır:** bir ayda yapılan kart harcamalarının tamamı, *bir sonraki* ayda kesilen ekstreye yazılır. Harcamanın günü ile kesim günü karşılaştırılmaz. (Bankaların gerçek davranışından bilinçli olarak farklı — takibi kolay olsun diye.)
- Henüz girilmemiş, **birikmekte olan** ekstreler de listelenir: kayıtlı ekstrelerin ucundan devam eden devir + o döneme düşen giderler.

Tüm bu mantık tek yerde: [`Mind/ExpenseTracker/statements.py`](Mind/ExpenseTracker/statements.py). Davranışı 51 test koruyor (`Mind/ExpenseTracker/tests.py`).

## Dizin yapısı

```
Dockerfile              uygulama imajı (python:3.14-slim)
docker-compose.yml      geliştirme yığını: runserver + bind mount
compose.prod.yml        üretim yığını: gunicorn + nginx + kapalı Postgres
.env.example            üretim ortam değişkenleri şablonu
deploy/nginx.conf       static/media doğrudan nginx'ten, gerisi proxy
deploy/README.md        üretim yığını ve güvenlik sertleştirmesinin ayrıntıları
Mind/                   Django projesi (manage.py burada)
  Mind/                 settings, urls, wsgi
  Accounts/             kullanıcı + profil
  ExpenseTracker/       gider, gelir, kart, ekstre, kredi
  CareerPath/           yol haritası
  Notebook/             notlar
  templates/            index.html, login.html (ortak sayfalar)
  static/               ortak css/js
  media/                yüklenen dosyalar (banka logoları, avatarlar)
```

## Geliştirme ortamı

```bash
docker compose up -d --build
docker compose exec api-provider python3 manage.py migrate
docker compose exec api-provider python3 manage.py createsuperuser
```

Uygulama: <http://localhost:9000> · admin: <http://localhost:9000/admin/>

`./Mind` konteynere bağlı olduğu için kod değişince runserver kendini yeniler. Postgres yalnızca `127.0.0.1:5432` üzerinde dinler — host'tan erişilir, ağa çıkmaz.

Yeni bir kullanıcı için başlangıç verisi (opsiyonel):

```bash
docker compose exec api-provider python3 manage.py seed_careerpath <kullanıcı_adı>
docker compose exec api-provider python3 manage.py seed_notebook <kullanıcı_adı>
```

## Testler

Testler host makineden, compose'daki Postgres'e karşı çalışır:

```bash
docker compose up -d postgresql-database
POSTGRES_HOST=127.0.0.1 .venv/bin/python Mind/manage.py test \
    ExpenseTracker Accounts CareerPath Notebook
```

İki tuzak:

- **Uygulama adlarını açıkça ver.** `manage.py` `Mind/` altında olduğu için argümansız çağrıda keşif kök dizinden başlar ve "0 test" bulur.
- **sqlite'a düşme.** Migration zinciri Postgres'e özgü SQL içeriyor ve `Debts` üzerindeki `nulls_distinct=False` kısıtı yalnızca Postgres 15+'ta oluşuyor.

## Ayarlar

Gizli anahtar, DEBUG, izinli hostlar ve veritabanı bilgileri ortam değişkeninden okunur; geliştirme varsayılanları koda gömülü olduğu için lokalde hiçbir şey vermek gerekmez.

| Değişken | Varsayılan | Not |
|---|---|---|
| `DJANGO_SECRET_KEY` | depodaki geliştirme anahtarı | `DEBUG=False` iken **zorunlu** |
| `DJANGO_DEBUG` | `True` | üretimde `False` |
| `DJANGO_ALLOWED_HOSTS` | boş | `DEBUG=False` iken **zorunlu**, virgülle ayrılmış |
| `DJANGO_HTTPS` | `False` | TLS kurulduktan *sonra* `True` — erken açmak yönlendirme döngüsü üretir |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | boş | `DJANGO_HTTPS=True` iken gerekli, şemayla birlikte |
| `POSTGRES_DB` / `_USER` / `_PASSWORD` | `mind-db` / `cerberus` / `cerberus` | üretimde parola zorunlu |
| `POSTGRES_HOST` / `_PORT` | `postgresql-database` / `5432` | host'tan çalışırken `127.0.0.1` |

`DEBUG` kapalıyken eksik anahtar veya boş host listesi **import anında** `ImproperlyConfigured` fırlatır: konteyner ilk istekte değil, açılışta ölür. Depodaki anahtarla sessizce üretime çıkmak mümkün değil.

## Üretim

```bash
cp .env.example .env && $EDITOR .env     # secret key + Postgres parolası üret
docker compose -f compose.prod.yml up -d --build
```

`compose.prod.yml`, geliştirme dosyasının üstüne bindirilmez — **yerine geçer**. `-f` verildiği an `docker-compose.yml` hiç okunmaz, dolayısıyla `./Mind:/code` gibi geliştirme ayarları birleşme yoluyla sızmaz. Açılışta `migrate` + `collectstatic` çalışır, gunicorn 3 worker ile kalkar, önünde nginx durur ve Postgres'in yayımlanmış portu yoktur.

Yüklenen dosyalar `./Mind/media` altında host'ta kalır (yedeklemesi kolay); `collectstatic` çıktısı nginx'in salt okunur bağladığı bir volume'dedir.

Ayrıntılar, doğrulama tablosu ve taşıma sırası: [`deploy/README.md`](deploy/README.md).

## Bilinen sınırlar

- Tek kullanıcılık kullanım için tasarlandı; veriler kullanıcı bazında ayrılmış olsa da kayıt (sign-up) akışı yok, kullanıcıyı admin'den ya da `createsuperuser` ile açıyorsun.
- Arayüz Türkçe, ancak `LANGUAGE_CODE` hâlâ `en-us` ve `TIME_ZONE` `UTC`.
- Testler yalnızca ExpenseTracker'ı kapsıyor; diğer üç uygulamanın `tests.py` dosyaları boş.
