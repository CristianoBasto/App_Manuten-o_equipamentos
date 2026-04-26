from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from .models import Equipamento, Manutencao, Oficina

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


# ── Views principais ──────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    equipamentos = Equipamento.objects.all()
    manutencoes  = Manutencao.objects.select_related("equipamento").all()

    context = {
        "total_equipamentos":    equipamentos.count(),
        "aguardando_orcamento":  manutencoes.filter(status="aguardando_orcamento").count(),
        "orcamento_aprovado":    manutencoes.filter(status="orcamento_aprovado").count(),
        "concluidas":            manutencoes.filter(status="concluida").count(),
        "proximas":              manutencoes.filter(status="aguardando_orcamento").order_by("data_prevista")[:5],
    }
    return render(request, "manutencao/dashboard.html", context)


@login_required
def lista_manutencoes(request):
    manutencoes = Manutencao.objects.select_related("equipamento").all()

    status = request.GET.get("status")
    eq_id  = request.GET.get("equipamento")
    mes    = request.GET.get("mes")
    ano    = request.GET.get("ano")
    of_id  = request.GET.get("oficina")

    if status:
        manutencoes = manutencoes.filter(status=status)
    if eq_id:
        manutencoes = manutencoes.filter(equipamento_id=eq_id)
    if mes:
        manutencoes = manutencoes.filter(data_registro__month=mes)
    if ano:
        manutencoes = manutencoes.filter(data_registro__year=ano)
    if of_id:
        manutencoes = manutencoes.filter(oficina_id=of_id)

    # Anos disponíveis para o filtro
    from django.db.models.functions import ExtractYear
    anos_disponiveis = (
        Manutencao.objects.annotate(ano=ExtractYear("data_registro"))
        .values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )

    context = {
        "manutencoes":      manutencoes,
        "equipamentos":     Equipamento.objects.all(),
        "oficinas":         Oficina.objects.all(),
        "filtro_status":    status,
        "filtro_eq":        eq_id,
        "filtro_mes":       mes,
        "filtro_ano":       ano,
        "filtro_oficina":   of_id,
        "anos_disponiveis": anos_disponiveis,
    }
    return render(request, "manutencao/lista_manutencoes.html", context)


@login_required
def cadastrar_manutencao(request):
    if request.method == "POST":
        Manutencao.objects.create(
            equipamento_id=request.POST["equipamento"],
            tipo          =request.POST["tipo"],
            descricao     =request.POST["descricao"],
            data_prevista =request.POST["data_prevista"],
            responsavel   =request.POST.get("responsavel", ""),
            horimetro     =request.POST.get("horimetro") or None,
            oficina_id    =request.POST.get("oficina") or None,
            status        ="aguardando_orcamento",
            criado_por    =request.user,
        )
        return redirect("lista_manutencoes")

    return render(request, "manutencao/cadastrar_manutencao.html", {
        "equipamentos": Equipamento.objects.all(),
        "oficinas":     Oficina.objects.all(),
    })


@login_required
def concluir_manutencao(request, pk):
    m = get_object_or_404(Manutencao, pk=pk)
    m.status         = "concluida"
    m.data_realizada = timezone.now().date()
    m.save()
    return redirect("lista_manutencoes")


@login_required
def cadastrar_equipamento(request):
    if request.method == "POST":
        Equipamento.objects.create(
            nome       =request.POST["nome"],
            localizacao=request.POST["localizacao"],
            descricao  =request.POST.get("descricao", ""),
        )
        return redirect("dashboard")

    return render(request, "manutencao/cadastrar_equipamento.html")


# ── Exportar PDF ──────────────────────────────────────────────────────────────

@login_required
def editar_manutencao(request, pk):
    m = get_object_or_404(Manutencao, pk=pk)

    # Regra 1 — registro concluído não pode ser editado por ninguém
    if m.status == "concluida":
        return render(request, "manutencao/sem_permissao.html", {
            "motivo": "Este registro já foi concluído e não pode mais ser editado."
        })

    # Regra 2 — somente o criador pode editar
    if m.criado_por != request.user:
        return render(request, "manutencao/sem_permissao.html", {
            "motivo": "Somente o usuário que criou este registro pode editá-lo."
        })

    if request.method == "POST":
        m.equipamento_id = request.POST["equipamento"]
        m.tipo           = request.POST["tipo"]
        m.descricao      = request.POST["descricao"]
        m.data_prevista  = request.POST["data_prevista"]
        m.responsavel    = request.POST.get("responsavel", "")
        m.horimetro      = request.POST.get("horimetro") or None
        m.oficina_id     = request.POST.get("oficina") or None
        m.status         = request.POST["status"]
        # Se concluindo agora, registra a data
        if m.status == "concluida" and not m.data_realizada:
            m.data_realizada = timezone.now().date()
        m.save()
        return redirect("lista_manutencoes")

    context = {
        "m":            m,
        "equipamentos": Equipamento.objects.all(),
        "oficinas":     Oficina.objects.all(),
    }
    return render(request, "manutencao/editar_manutencao.html", context)


@login_required
def lista_oficinas(request):
    oficinas = Oficina.objects.all()
    return render(request, "manutencao/lista_oficinas.html", {"oficinas": oficinas})


@login_required
def cadastrar_oficina(request):
    if request.method == "POST":
        Oficina.objects.create(
            nome       =request.POST["nome"],
            telefone   =request.POST.get("telefone", ""),
            responsavel=request.POST.get("responsavel", ""),
        )
        return redirect("lista_oficinas")
    return render(request, "manutencao/cadastrar_oficina.html")


@login_required
def exportar_pdf(request):
    manutencoes = Manutencao.objects.select_related("equipamento", "oficina").all()
    status = request.GET.get("status")
    mes    = request.GET.get("mes")
    ano    = request.GET.get("ano")
    of_id  = request.GET.get("oficina")

    if status:
        manutencoes = manutencoes.filter(status=status)
    if mes:
        manutencoes = manutencoes.filter(data_registro__month=mes)
    if ano:
        manutencoes = manutencoes.filter(data_registro__year=ano)
    if of_id:
        manutencoes = manutencoes.filter(oficina_id=of_id)

    manutencoes = manutencoes.order_by("data_registro")

    # Monta título do período
    MESES_PT = {
        "1":"Janeiro","2":"Fevereiro","3":"Março","4":"Abril",
        "5":"Maio","6":"Junho","7":"Julho","8":"Agosto",
        "9":"Setembro","10":"Outubro","11":"Novembro","12":"Dezembro",
    }
    if mes and ano:
        periodo = f"{MESES_PT.get(mes, mes)}/{ano}"
    elif mes:
        periodo = MESES_PT.get(mes, mes)
    elif ano:
        periodo = ano
    else:
        periodo = "Geral"

    nome_arquivo = f"relatorio_manutencao_{periodo.replace('/', '_')}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'

    doc    = SimpleDocTemplate(response, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # ── Título ────────────────────────────────────────────────────────────────
    titulo_style = ParagraphStyle(
        "titulo", parent=styles["Heading1"],
        fontSize=16, alignment=TA_CENTER, spaceAfter=6,
        textColor=colors.HexColor("#1e3a5f"),
    )
    subtitulo_style = ParagraphStyle(
        "subtitulo", parent=styles["Normal"],
        fontSize=9, alignment=TA_CENTER, spaceAfter=20,
        textColor=colors.grey,
    )

    story.append(Paragraph("Sistema de Controle de Manutenção", titulo_style))
    story.append(Paragraph(
        f"Relatório de Manutenções — Período: {periodo}",
        ParagraphStyle("periodo", parent=styles["Heading2"], fontSize=12,
                       alignment=TA_CENTER, textColor=colors.HexColor("#2d4a6e"), spaceAfter=4)
    ))
    story.append(Paragraph(
        f"Gerado em {timezone.now().strftime('%d/%m/%Y às %H:%M')} "
        f"por {request.user.get_full_name() or request.user.username}",
        subtitulo_style
    ))

    # ── Cards de resumo ───────────────────────────────────────────────────────
    total      = Manutencao.objects.count()
    pendentes  = Manutencao.objects.filter(status="pendente").count()
    atrasadas  = Manutencao.objects.filter(status="atrasada").count()
    concluidas = Manutencao.objects.filter(status="concluida").count()

    resumo_data = [
        ["Total", "Pendentes", "Atrasadas", "Concluídas"],
        [str(total), str(pendentes), str(atrasadas), str(concluidas)],
    ]
    resumo_table = Table(resumo_data, colWidths=[4*cm]*4)
    resumo_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("BACKGROUND",    (0,1), (-1,1), colors.HexColor("#f0f4f8")),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ("INNERGRID",     (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(resumo_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Tabela de manutenções ─────────────────────────────────────────────────
    story.append(Paragraph("Detalhamento das Manutenções", styles["Heading2"]))
    story.append(Spacer(1, 0.3*cm))

    header = ["Equipamento", "Tipo", "Descrição", "Registro", "Prev.", "Horímetro", "Oficina", "Status", "Resp.", "Dias"]
    rows   = [header]

    STATUS_CORES = {
        "aguardando_orcamento": colors.HexColor("#fefcbf"),
        "orcamento_aprovado":   colors.HexColor("#bee3f8"),
        "concluida":            colors.HexColor("#c6f6d5"),
    }

    for m in manutencoes:
        dias      = f"{m.dias_ate_conclusao}d" if m.dias_ate_conclusao is not None else "—"
        horimetro = f"{m.horimetro} h" if m.horimetro is not None else "—"
        oficina   = m.oficina.nome if m.oficina else "—"
        rows.append([
            m.equipamento.nome,
            m.get_tipo_display(),
            m.descricao[:35] + ("…" if len(m.descricao) > 35 else ""),
            m.data_registro.strftime("%d/%m/%Y"),
            m.data_prevista.strftime("%d/%m/%Y"),
            horimetro,
            oficina,
            m.get_status_display(),
            m.responsavel or "—",
            dias,
        ])

    col_widths = [2.6*cm, 1.7*cm, 3.8*cm, 1.9*cm, 1.9*cm, 1.6*cm, 2.2*cm, 1.7*cm, 2.0*cm, 1.3*cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("ALIGN",         (3,0), (5,-1),  "CENTER"),
        ("ALIGN",         (9,0), (9,-1),  "CENTER"),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
    ]

    for i, m in enumerate(manutencoes, start=1):
        cor = STATUS_CORES.get(m.status, colors.white)
        style_cmds.append(("BACKGROUND", (7, i), (7, i), cor))

    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    doc.build(story)
    return response