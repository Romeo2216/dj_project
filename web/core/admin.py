from django.contrib import admin
from .models import Pari, Vote, Wallet

@admin.register(Pari)
class PariAdmin(admin.ModelAdmin):
    list_display = ("id", "description", "nb_oui", "nb_non", "result", "resolved", "resolved_at", "created_at")
    list_filter = ("resolved", "result", "created_at")
    search_fields = ("description",)
    readonly_fields = ("nb_oui", "nb_non", "resolved_at", "created_at", "updated_at")

from django.contrib import admin
from .models import Pari, Vote, Wallet
from django.core.exceptions import ValidationError

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "pari", "choice", "stake_points", "created_at")
    list_filter = ("choice", "created_at")
    search_fields = ("user__username", "pari__description")
    readonly_fields = ("user", "pari", "choice", "stake_points", "created_at", "updated_at")

    def has_change_permission(self, request, obj=None):
        # Lecture seule : pas d'édition
        return False

    def has_delete_permission(self, request, obj=None):
        # Si tu veux aussi interdire la suppression, renvoie False.
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "updated_at")
    search_fields = ("user__username", "user__email")
