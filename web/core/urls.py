from django.urls import path
from . import views

urlpatterns = [
    path("paris/", views.liste_paris, name="liste_paris"),
    path("pari/<int:pari_id>/bet/<str:choice>/", views.bet, name="bet"),
    path("pari/<int:pari_id>/vote/<str:choice>/", views.vote, name="vote"),
    path("pari/<int:pari_id>/resolve/<str:result>/", views.resolve_pari, name="resolve_pari"), 
]
