from django.urls import include, path

urlpatterns = [
    path("djinsight/", include("djinsight.urls")),
]
