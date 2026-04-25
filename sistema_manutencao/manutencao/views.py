from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from .models import Equipamento, Manutencao

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


# ── Helpers ───────────────────────────────────────────────────────────────────

def _atualizar_atrasadas():
    """Marca como atrasadas todas as manutenções pendentes com data vencida."""
    hoje = timezone.now().date()
    Manutencao.objects.filter(
        status="pendente",
        data_prevista__lt=hoje
    ).update(status="atrasada")


# ── Views principais ──────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    _atualizar_atrasadas()

    equipamentos = Equipamento.objects.all()
    manutencoes  = Manutencao.objects.select_related("equipamento").all()

    context = {
        "total_equipamentos": equipamentos.count(),
        "pendentes":          manutencoes.filter(status="pendente").count(),
        "atrasadas":          manutencoes.filter(status="atrasada").count(),
        "concluidas":         manutencoes.filter(status="concluida").count(),
        "proximas":           manutencoes.filter(status="pendente").order_by("data_prevista")[:5],
    }
    return render(request, "manutencao/dashboard.html", context)


@login_required
def lista_manutencoes(request):
    _atualizar_atrasadas()
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
        "manutencoes":   manutencoes,
        "equipamentos":  Equipamento.objects.all(),
        "filtro_status": status,
        "filtro_tipo":   tipo,
        "filtro_eq":     eq_id,
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
            status        ="pendente",
        )
        return redirect("lista_manutencoes")

    return render(request, "manutencao/cadastrar_manutencao.html",
                  {"equipamentos": Equipamento.objects.all()})


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
def exportar_pdf(request):
    _atualizar_atrasadas()

    manutencoes = Manutencao.objects.select_related("equipamento").all()
    status = request.GET.get("status")
    if status:
        manutencoes = manutencoes.filter(status=status)
    manutencoes = manutencoes.order_by("data_prevista")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio_manutencao.pdf"'

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
        f"Relatório gerado em {timezone.now().strftime('%d/%m/%Y às %H:%M')} "
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

    header = ["Equipamento", "Tipo", "Descrição", "Registro", "Prev.", "Status", "Responsável", "Dias"]
    rows   = [header]

    STATUS_CORES = {
        "pendente":  colors.HexColor("#fefcbf"),
        "atrasada":  colors.HexColor("#fed7d7"),
        "concluida": colors.HexColor("#c6f6d5"),
    }

    for m in manutencoes:
        dias = f"{m.dias_ate_conclusao}d" if m.dias_ate_conclusao is not None else "—"
        rows.append([
            m.equipamento.nome,
            m.get_tipo_display(),
            m.descricao[:45] + ("…" if len(m.descricao) > 45 else ""),
            m.data_registro.strftime("%d/%m/%Y"),
            m.data_prevista.strftime("%d/%m/%Y"),
            m.get_status_display(),
            m.responsavel or "—",
            dias,
        ])

    col_widths = [3.0*cm, 2.0*cm, 4.5*cm, 2.0*cm, 2.0*cm, 2.0*cm, 2.5*cm, 1.5*cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("ALIGN",         (3,0), (4,-1),  "CENTER"),
        ("ALIGN",         (7,0), (7,-1),  "CENTER"),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e0")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f7fafc")]),
    ]

    for i, m in enumerate(manutencoes, start=1):
        cor = STATUS_CORES.get(m.status, colors.white)
        style_cmds.append(("BACKGROUND", (4, i), (4, i), cor))

    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    doc.build(story)
    return response