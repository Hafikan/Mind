# TODO

## Backend
- [ ] Month query parametresi için backend ayarlanacak
- [ ] `creadits` URL typo'su `credits` olarak düzeltilecek (urls.py router + frontend fetch URL'leri)
- [ ] `DebtsSerializer` - `bank` alanı read_only, create/update'te bank ID gönderilemiyor
- [ ] Expenses summary endpoint eksik (`/tracker/api/expenses/summary/`)
- [ ] `Response` import kontrolü (CreditsViewSet summary action'da kullanılıyor)

## Frontend
- [ ] Debts ve Credits sayfalarına kategori bazlı accordion yapısı (expenses gibi) gerekli mi değerlendirilecek
- [ ] Form validasyon hata mesajları Türkçeleştirilecek
- [ ] Confirm dialog'lar Türkçeleştirilecek ("Are you sure..." → "Emin misiniz...")

## Genel
- [ ] Tüm sayfalarda dil tutarlılığı (EN/TR karışık durumda)
- [ ] Mobil responsive test
