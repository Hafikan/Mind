# Abstract User ve Abstract Base User Farklılıkları
Abstract User model varsayılan olarak 11 featuredan oluşur. Mevcut alanlar değiştirilebilir, yeni alanlar eklenebilir. Django da default olarak username girişi ile auth sağlanır. mail phone number vs gibi durumlar auth için gerekli değilse kullanabilirsin. Mevcut featurelara bir kaç feature da ben ekleyim diyorsan bio, avatar gibi vs tercih edebilirsin.Default alanlar
    - id, username, password, email, first_name, last_name
    - is_staff,  is_active, is_superuser
    - last_login, date_joined
CustomManager'ı opsiyonel olarak ekleyebilirsin.

AbstractBaseUser sınıfı başlangıçta sadece 3 alan içermektedir. 

     - id,  password, last_login

> Custom User Manager kullanmak zorundasın
> AUTH_USER_MODEL (settings.py) göstermeyi unutma
> referanslarda django.contrib.auth.get_user_model() kullan, file dan import edip referans çıkarma. Foreign key de de django.conf. setting.AUTH_USER_MODEL yeterli

> Profile Auth Pattern kullanmayı deneyebilirsin. 

# Custom User Forms
A user model can be both created and edited within the Django admin. So we'll need to update the build-in forms too to point to CustomerUser instead of User (Default). Remember, you must create app/forms.py.

> **Form initialization** 
> Meta class model için statik tanımlamalar yapar.__init__ ise runtime da ve miras alınan sınıfda değişiklik yapar.