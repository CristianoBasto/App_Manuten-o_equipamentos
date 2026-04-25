from django.db import models


class Equipamento(models.Model):
    nome        = models.CharField(max_length=100)
    localizacao = models.CharField(max_length=100)
    descricao   = models.TextField(blank=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name        = "Equipamento"
        verbose_name_plural = "Equipamentos"
        ordering            = ["nome"]


class Manutencao(models.Model):
    TIPO_CHOICES = [
        ("preventiva", "Preventiva"),
        ("corretiva",  "Corretiva"),
    ]
    STATUS_CHOICES = [
        ("pendente",  "Pendente"),
        ("concluida", "Concluída"),
        ("atrasada",  "Atrasada"),
    ]

    equipamento    = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name="manutencoes"
    )
    tipo           = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao      = models.TextField()
    data_prevista  = models.DateField()
    data_realizada = models.DateField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    responsavel    = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.equipamento} — {self.tipo} ({self.get_status_display()})"

    class Meta:
        verbose_name        = "Manutenção"
        verbose_name_plural = "Manutenções"
        ordering            = ["data_prevista"]
