from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Equipamento, Manutencao


def dashboard(request):
    """Tela principal com resumo geral do sistema."""
    hoje = timezone.now().date()

    equipamentos  = Equipamento.objects.all()
    manutencoes   = Manutencao.objects.select_related("equipamento").all()

    # Atualiza automaticamente manutenções atrasadas
    manutencoes.filter(
        status="pendente",
        data_prevista__lt=hoje
    ).update(status="atrasada")

    pendentes  = manutencoes.filter(status="pendente").count()
    atrasadas  = manutencoes.filter(status="atrasada").count()
    concluidas = manutencoes.filter(status="concluida").count()

    proximas = manutencoes.filter(
        status="pendente"
    ).order_by("data_prevista")[:5]

    context = {
        "equipamentos":       equipamentos,
        "total_equipamentos": equipamentos.count(),
        "pendentes":          pendentes,
        "atrasadas":          atrasadas,
        "concluidas":         concluidas,
        "proximas":           proximas,
    }
    return render(request, "manutencao/dashboard.html", context)


def lista_manutencoes(request):
    """Lista todas as manutenções com filtros opcionais."""
    manutencoes = Manutencao.objects.select_related("equipamento").all()

    status = request.GET.get("status")
    tipo   = request.GET.get("tipo")
    eq_id  = request.GET.get("equipamento")

    if status:
        manutencoes = manutencoes.filter(status=status)
    if tipo:
        manutencoes = manutencoes.filter(tipo=tipo)
    if eq_id:
        manutencoes = manutencoes.filter(equipamento_id=eq_id)

    context = {
        "manutencoes":  manutencoes,
        "equipamentos": Equipamento.objects.all(),
        "filtro_status": status,
        "filtro_tipo":   tipo,
        "filtro_eq":     eq_id,
    }
    return render(request, "manutencao/lista_manutencoes.html", context)


def cadastrar_manutencao(request):
    """Formulário para cadastrar nova manutenção."""
    if request.method == "POST":
        Manutencao.objects.create(
            equipamento_id = request.POST["equipamento"],
            tipo           = request.POST["tipo"],
            descricao      = request.POST["descricao"],
            data_prevista  = request.POST["data_prevista"],
            responsavel    = request.POST.get("responsavel", ""),
            status         = "pendente",
        )
        return redirect("lista_manutencoes")

    context = {"equipamentos": Equipamento.objects.all()}
    return render(request, "manutencao/cadastrar_manutencao.html", context)


def concluir_manutencao(request, pk):
    """Marca uma manutenção como concluída."""
    manutencao = get_object_or_404(Manutencao, pk=pk)
    manutencao.status         = "concluida"
    manutencao.data_realizada = timezone.now().date()
    manutencao.save()
    return redirect("lista_manutencoes")


def cadastrar_equipamento(request):
    """Formulário para cadastrar novo equipamento."""
    if request.method == "POST":
        Equipamento.objects.create(
            nome        = request.POST["nome"],
            localizacao = request.POST["localizacao"],
            descricao   = request.POST.get("descricao", ""),
        )
        return redirect("dashboard")

    return render(request, "manutencao/cadastrar_equipamento.html")