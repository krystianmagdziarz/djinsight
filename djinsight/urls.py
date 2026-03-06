from django.urls import path

from djinsight import views

app_name = "djinsight"

urlpatterns = [
    path("record-view/", views.record_page_view, name="record_page_view"),
    path("page-stats/", views.get_page_stats, name="get_page_stats"),
]
