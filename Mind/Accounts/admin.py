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
    list_display_links = ('email','username')

    
    # Admin panelinde sağdaki filtre bölümü
    list_filter = ('is_active','is_staff', 'is_superuser','date_joined', 'last_login',)

    # Admin panelden arama yapılabilecek featurelar 
    search_fields = ('email', 'first_name', 'last_name','username')

    ordering = ('-date_joined',) # önce en yeni
    
    list_per_page = 50

    # Admin sayfasında düzenlenebilir alanlar
    list_editable = ('is_staff',)

    

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
        }),

        #Grup 3, Permissions
        ('Permissions',{
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        #Group 4, Important Date
        ('Important Date',{
            'fields': ('last_login', 'date_joined')
        })
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
        }),
    )
    

admin.site.register(AppUser, CustomUserAdmin)
