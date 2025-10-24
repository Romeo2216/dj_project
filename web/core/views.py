from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Pari, Vote


from django.shortcuts import render
from django.contrib.auth.models import User
from .models import Wallet

def index(request):
    # On récupère tous les utilisateurs avec leurs points
    users = User.objects.select_related("wallet").order_by("-wallet__points")
    return render(request, "index.html", {"users": users})


def liste_paris(request):
    paris = Pari.objects.all().order_by("-created_at")

    my_vote_by_id = {}
    if request.user.is_authenticated:
        votes = Vote.objects.filter(user=request.user, pari__in=paris).only("pari_id","choice","stake_points","created_at")
        my_vote_by_id = {v.pari_id: v for v in votes}

    return render(request, "core/liste_paris.html", {
        "paris": paris,
        "my_vote_by_id": my_vote_by_id,
    })

# (facultatif) si tu as déjà implémenté le vote plus tôt :
@login_required
@require_POST
def vote(request, pari_id, choice):
    from .models import Vote  # si déjà défini dans models.py
    pari = get_object_or_404(Pari, pk=pari_id)
    if choice not in (Vote.OUI, Vote.NON):
        return redirect("liste_paris")
    Vote.objects.update_or_create(user=request.user, pari=pari, defaults={"choice": choice})
    return redirect("liste_paris")

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import F

from .models import Pari, Vote, Wallet

@login_required
@require_POST
def bet(request, pari_id, choice):
    if choice not in (Vote.OUI, Vote.NON):
        messages.error(request, "Choix invalide.")
        return redirect("liste_paris")

    pari = get_object_or_404(Pari, pk=pari_id)

    # points
    try:
        points = int(request.POST.get("points", "0"))
    except ValueError:
        points = 0
    if points <= 0:
        messages.error(request, "Veuillez saisir un nombre de points valide (≥ 1).")
        return redirect("liste_paris")

    user = request.user
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={"points": 100})

    # ❌ Si un vote existe déjà pour cet utilisateur sur ce pari -> interdit
    if Vote.objects.filter(user=user, pari=pari).exists():
        messages.error(request, "Votre vote est définitif et ne peut pas être modifié.")
        return redirect("liste_paris")

    # ✅ Premier (et seul) vote : débiter et créer
    with transaction.atomic():
        updated = Wallet.objects.filter(pk=wallet.pk, points__gte=points).update(points=F("points") - points)
        if not updated:
            messages.error(request, "Solde insuffisant pour placer ce pari.")
            return redirect("liste_paris")
        try:
            Vote.objects.create(user=user, pari=pari, choice=choice, stake_points=points)
        except IntegrityError:
            # Cas rare de double-submit simultané : on rembourse la mise et refuse
            Wallet.objects.filter(pk=wallet.pk).update(points=F("points") + points)
            messages.error(request, "Votre vote existe déjà. Il est définitif.")
            return redirect("liste_paris")

    messages.success(request, f"Pari enregistré : {points} points sur « {choice.upper()} ». (définitif)")
    return redirect("liste_paris")


from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Pari, Vote, Wallet

def _is_super(user):
    return user.is_active and user.is_superuser

@user_passes_test(_is_super)
@require_POST
def resolve_pari(request, pari_id, result):
    if result not in (Pari.OUI, Pari.NON):
        messages.error(request, "Résultat invalide.")
        return redirect("liste_paris")

    pari = get_object_or_404(Pari, pk=pari_id)
    if pari.resolved:
        messages.info(request, "Ce pari est déjà résolu.")
        return redirect("liste_paris")

    # Récupère toutes les mises
    votes = list(Vote.objects.select_related("user").filter(pari=pari))

    total_yes = sum(v.stake_points for v in votes if v.choice == Vote.OUI)
    total_no  = sum(v.stake_points for v in votes if v.choice == Vote.NON)
    total = total_yes + total_no

    winners_choice = result
    winners = [v for v in votes if v.choice == winners_choice]
    winners_total_stake = sum(v.stake_points for v in winners)

    with transaction.atomic():
        # Aucun gagnant -> remboursement intégral de tout le monde
        if winners_total_stake == 0:
            for v in votes:
                Wallet.objects.filter(user=v.user).update(points=F("points") + v.stake_points)
            pari.result = result
            pari.resolved = True
            pari.resolved_at = timezone.now()
            pari.save(update_fields=["result", "resolved", "resolved_at"])
            messages.warning(request, "Aucun gagnant : toutes les mises ont été remboursées.")
            return redirect("liste_paris")

        # Si pas de perdant -> cote = 1 -> tout le monde remboursé (gagnants seuls)
        losers_total = total - winners_total_stake
        if losers_total == 0:
            for v in winners:
                Wallet.objects.filter(user=v.user).update(points=F("points") + v.stake_points)
            pari.result = result
            pari.resolved = True
            pari.resolved_at = timezone.now()
            pari.save(update_fields=["result", "resolved", "resolved_at"])
            messages.info(request, "Aucun perdant : gagnants remboursés de leur mise.")
            return redirect("liste_paris")

        # Cote = 1 / prob = total / winners_total_stake
        # payout_i = stake_i * (total / winners_total_stake)
        # Pour rester en entiers, on distribue le reliquat après arrondi à l'entier inférieur.
        payouts = []
        distributed = 0
        shares = []  # pour répartir le reliquat selon les parties décimales

        # ratio constant
        ratio = total / winners_total_stake  # float
        for v in winners:
            raw = v.stake_points * ratio
            floor_amount = int(raw)  # plancher
            distributed += floor_amount
            payouts.append((v, floor_amount))
            shares.append((v, raw - floor_amount))  # partie fractionnaire

        # Redistribuer le reliquat (total - distributed) aux plus grosses fractions
        remainder = total - distributed
        if remainder > 0:
            shares.sort(key=lambda x: x[1], reverse=True)
            for i in range(min(remainder, len(shares))):
                v, _ = shares[i]
                for j in range(len(payouts)):
                    if payouts[j][0].pk == v.pk:
                        vv, amt = payouts[j]
                        payouts[j] = (vv, amt + 1)
                        break

        # Créditer les gagnants
        for v, amount in payouts:
            Wallet.objects.filter(user=v.user).update(points=F("points") + amount)

        # Marquer le pari comme résolu
        pari.result = result
        pari.resolved = True
        pari.resolved_at = timezone.now()
        pari.save(update_fields=["result", "resolved", "resolved_at"])

    messages.success(
        request,
        f"Pari #{pari.id} validé ({result.upper()}) — gains redistribués selon la cote 1/probabilité."
    )
    return redirect("liste_paris")


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PariForm

@login_required
def creer_pari(request):
    if request.method == "POST":
        form = PariForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("liste_paris")
    else:
        form = PariForm()
    return render(request, "core/creer_pari.html", {"form": form})
