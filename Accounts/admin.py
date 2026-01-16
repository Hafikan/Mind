from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserChangeForm, CustomUserCreationForm

AppUser = get_user_model()

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm  # Yeni kullanıcı ekleme formu
    form = CustomUserChangeForm        # Mevcut kullanıcıları düzenleme formu
    model = AppUser                    # Uygulamadaki auth usera bağla
    

    # Admin panel de görünecek alanlar
    list_display = (
        "email",
        # varsa full_name (custom method)
        "is_staff",
        "username",
        "date_joined",
    )

    # Admin panelinde her bir row daki attributeların hangisi tıklanabilir
    list_display_links = ('email','full_name')

    
    # Admin panelinde sağdaki filtre bölümü
    list_filter = ('is_active','is_staff', 'is_superuser','date_joined', 'last_login',)

    # Admin panelden arama yapılabilecek featurelar 
    search_fields = ('email', 'first_name', 'last_name','username')

    ordering = ('-date_joined',) # önce en yeni
    
    list_per_page = 50

    # Admin sayfasında düzenlenebilir alanlar
    list_editable = ('is_staff','is_superuser')

    
https://claude.ai/oauth/authorize?code=true&client_id=9d1c250a-e61b-44d9-88ed-5944d1962f5e&response_type=code&redirect_uri=https%3A%2F%2Fplatform.claude.com%2Foauth%2Fcode%2Fcallback&scope=org%3Acreate_api_key+user%3Aprofile+user%3Ainference+user%3Asessions%3Aclaude_code&code_challenge=FyGUrZTaKBomXQGk0zqyuu2i3vXYuUszqbdL7BZqXu8&code_challenge_method=S256&state=l5_B0QSarL-3QGuBBXXTl9brzLRyL8LXvhIi00QHEII
    # ***********************************
    # Edit Page
    # ***********************************

    fieldsets =(
        #Grup 1
        (None,{
            'fields': ('email','password')
        }),
        
        #Grup 2, Personal Informations
        ('Personal Informations',{
            'fields': ('first_name', 'last_name', 'phone')
        })

        #Grup 3, Permissions
        ('Permissions',{
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
      
<class 'Accounts.admin.CustomUserAdmin'>: (admin.E008) The value of 'fieldsets[3]' must be a list or tuple.
<class 'Accounts.admin.CustomUserAdmin'>: (admin.E008) The value of 'fieldsets[4]' must be a list or tuple.  }),
        #Group 4, Important Date
        ('Important Date'),{
            'fields': ('last_login', 'date_joined')
        }
    )
    
    # ***********************************
    # Add New User Page
    # ***********************************

    add_fieldsets = (
        (None,{
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'phone',
                'password1',
                'password2',
            )
        })
    )
    

admin.site.register(CustomUser, CustomUserAdmin)
