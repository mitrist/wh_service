from django.urls import path

from health import views

urlpatterns = [
    path("", views.index, name="health_index"),
    path("result/<int:result_id>/", views.result, name="health_result"),
]
