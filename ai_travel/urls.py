from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from user import views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.IndexPage, name='index'),  # root URL handled here
    path('core/', include('core.urls', namespace='core')),  # moved core URLs under /core/
    path('signup/', views.SignupPage, name='signup'),
    path('login/', views.LoginPage, name='login'),
    # path('logout/', views.LogoutPage, name='logout'),
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


