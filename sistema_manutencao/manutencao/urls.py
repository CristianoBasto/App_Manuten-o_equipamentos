from django.urls import path
from . import views

urlpatterns = [
    path("",                          views.dashboard,              name="dashboard"),
    path("manutencoes/",              views.lista_manutencoes,      name="lista_manutencoes"),
    path("manutencoes/cadastrar/",    views.cadastrar_manutencao,   name="cadastrar_manutencao"),
    path("manutencoes/<int:pk>/concluir/", views.concluir_manutencao, name="concluir_manutencao"),
    path("equipamentos/cadastrar/",   views.cadastrar_equipamento,  name="cadastrar_equipamento"),
]