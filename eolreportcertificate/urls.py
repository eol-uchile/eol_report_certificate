from django.conf.urls import url
from .views import EolReportCertificateView


urlpatterns = [
    url('data', EolReportCertificateView.as_view(), name='data'),
]