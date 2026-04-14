from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("favicon.ico", serve, {"path": "favicon.ico", "document_root": settings.BASE_DIR}),
    path("policy.pdf", serve, {"path": "main_page/policy.pdf", "document_root": settings.BASE_DIR}, name="policy_pdf"),
    path("policy/", RedirectView.as_view(url="/policy.pdf", permanent=False), name="policy"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("", include("apps.frontend.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
