from django.db import models
from django.conf import settings
from django.db.models import F
from django.core.exceptions import ValidationError

class Pari(models.Model):
    description = models.TextField(help_text="Description du pari.")
    nb_oui = models.PositiveIntegerField(default=0, verbose_name="Votes OUI")
    nb_non = models.PositiveIntegerField(default=0, verbose_name="Votes NON")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    OUI = "oui"
    NON = "non"
    RESULT_CHOICES = [(OUI, "Oui"), (NON, "Non")]

    result = models.CharField(
        max_length=3, choices=RESULT_CHOICES, null=True, blank=True,
        help_text="Résultat validé (oui/non)."
    )
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pari"
        verbose_name_plural = "Paris"

    def __str__(self):
        return (self.description[:50] + "...") if len(self.description) > 50 else self.description

    @property
    def total_votes(self):
        return self.nb_oui + self.nb_non

    @property
    def pourcentage_oui(self):
        return round(self.nb_oui * 100 / self.total_votes, 2) if self.total_votes else 0

    @property
    def pourcentage_non(self):
        return round(self.nb_non * 100 / self.total_votes, 2) if self.total_votes else 0


class Vote(models.Model):
    OUI = "oui"
    NON = "non"
    CHOICES = [(OUI, "Oui"), (NON, "Non")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes")
    pari = models.ForeignKey(Pari, on_delete=models.CASCADE, related_name="votes")
    choice = models.CharField(max_length=3, choices=CHOICES)
    stake_points = models.PositiveIntegerField(default=0)  # ✅ montant parié en points
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # interdire toute modification après création
        if self.pk is not None and self.__class__.objects.filter(pk=self.pk).exists():
            raise ValidationError("Vote définitif : modification interdite.")
        super().save(*args, **kwargs)

    class Meta:
        unique_together = [("user", "pari")]
        indexes = [
            models.Index(fields=["pari", "user"]),
            models.Index(fields=["pari", "choice"]),
        ]



class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    points = models.PositiveIntegerField(default=100)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Portefeuille"
        verbose_name_plural = "Portefeuilles"

    def __str__(self):
        return f"Wallet({self.user.username}): {self.points} pts"

    # Utilitaires sûrs (atomic + F() conseillé côté vues/services)
    def add_points(self, amount: int):
        """Ajoute (ou retire si négatif) des points de façon atomique."""
        type(self).objects.filter(pk=self.pk).update(points=F("points") + amount)
        self.refresh_from_db()

    def set_points(self, value: int):
        """Fixe le solde à une valeur précise."""
        type(self).objects.filter(pk=self.pk).update(points=max(0, value))
        self.refresh_from_db()


