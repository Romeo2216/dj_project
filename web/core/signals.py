from django.db.models.signals import pre_save, post_save, post_delete
from django.db.models import F
from django.dispatch import receiver
from .models import Vote, Pari, Wallet
from django.contrib.auth import get_user_model

@receiver(pre_save, sender=Vote)
def store_previous_choice(sender, instance: Vote, **kwargs):
    # Mémorise l'ancien choix pour savoir s'il change
    if instance.pk:
        try:
            old = Vote.objects.only("choice").get(pk=instance.pk)
            instance._previous_choice = old.choice
        except Vote.DoesNotExist:
            instance._previous_choice = None
    else:
        instance._previous_choice = None

@receiver(post_save, sender=Vote)
def update_pari_counters_on_save(sender, instance: Vote, created, **kwargs):
    # Incrémente/decrémente selon création ou changement de choix
    if created:
        if instance.choice == Vote.OUI:
            Pari.objects.filter(pk=instance.pari_id).update(nb_oui=F("nb_oui") + 1)
        else:
            Pari.objects.filter(pk=instance.pari_id).update(nb_non=F("nb_non") + 1)
    else:
        prev = getattr(instance, "_previous_choice", None)
        if prev and prev != instance.choice:
            if prev == Vote.OUI:
                Pari.objects.filter(pk=instance.pari_id).update(nb_oui=F("nb_oui") - 1)
            else:
                Pari.objects.filter(pk=instance.pari_id).update(nb_non=F("nb_non") - 1)
            if instance.choice == Vote.OUI:
                Pari.objects.filter(pk=instance.pari_id).update(nb_oui=F("nb_oui") + 1)
            else:
                Pari.objects.filter(pk=instance.pari_id).update(nb_non=F("nb_non") + 1)

@receiver(post_delete, sender=Vote)
def update_pari_counters_on_delete(sender, instance: Vote, **kwargs):
    if instance.choice == Vote.OUI:
        Pari.objects.filter(pk=instance.pari_id).update(nb_oui=F("nb_oui") - 1)
    else:
        Pari.objects.filter(pk=instance.pari_id).update(nb_non=F("nb_non") - 1)


User = get_user_model()

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        # Crée un wallet à 100 points par défaut
        Wallet.objects.get_or_create(user=instance, defaults={"points": 100})
