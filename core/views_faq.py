"""
Views для FAQ.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models_faq import FAQ, DescriptionTemplate
from listings.models import Game


def faq_page(request):
    """Страница FAQ"""
    faqs = FAQ.objects.filter(is_active=True).order_by('category', 'order')
    
    categories = FAQ.CATEGORIES
    
    context = {
        'faqs': faqs,
        'categories': categories,
    }
    return render(request, 'pages/faq.html', context)


@require_http_methods(['POST'])
def mark_faq_helpful(request, faq_id):
    """Отметить FAQ как полезный"""
    try:
        faq = FAQ.objects.get(id=faq_id)
        
        helpful = request.POST.get('helpful') == 'true'
        
        if helpful:
            faq.helpful_count += 1
            faq.save(update_fields=['helpful_count'])
        
        return JsonResponse({'success': True})
    except FAQ.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


def get_templates(request, game_slug):
    """Получить шаблоны описаний для игры (API)"""
    try:
        game = Game.objects.get(slug=game_slug)
        templates = DescriptionTemplate.objects.filter(
            game=game,
            is_active=True
        ).order_by('-usage_count')
        
        data = []
        for template in templates:
            data.append({
                'id': template.id,
                'name': template.name,
                'template': template.template,
                'variables': template.variables
            })
        
        return JsonResponse({'templates': data})
    except Game.DoesNotExist:
        return JsonResponse({'templates': []})

