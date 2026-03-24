"""
Views для истории просмотров.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from listings.models_history import ViewHistory


@login_required
def view_history(request):
    """
    Страница с историей просмотренных объявлений.
    """
    history = ViewHistory.objects.filter(
        user=request.user
    ).select_related('listing', 'listing__game', 'listing__seller__profile').order_by('-viewed_at')

    # Пагинация
    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'history': page_obj.object_list,
    }
    return render(request, 'listings/view_history.html', context)
