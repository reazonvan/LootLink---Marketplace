"""
SEO утилиты: Open Graph, Schema.org.
"""


def get_og_tags(title, description, image=None, url=None):
    """
    Генерация Open Graph тегов.
    
    Args:
        title: Заголовок
        description: Описание
        image: URL изображения
        url: URL страницы
    
    Returns:
        dict: Open Graph теги
    """
    tags = {
        'og:type': 'website',
        'og:site_name': 'LootLink',
        'og:title': title,
        'og:description': description,
    }
    
    if image:
        tags['og:image'] = image
        tags['og:image:width'] = '1200'
        tags['og:image:height'] = '630'
    
    if url:
        tags['og:url'] = url
    
    # Twitter Card
    tags['twitter:card'] = 'summary_large_image'
    tags['twitter:title'] = title
    tags['twitter:description'] = description
    if image:
        tags['twitter:image'] = image
    
    return tags


def get_product_schema(listing):
    """
    Генерация Schema.org разметки для товара.
    
    Args:
        listing: Объект Listing
    
    Returns:
        dict: Schema.org JSON-LD
    """
    schema = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": listing.title,
        "description": listing.description,
        "offers": {
            "@type": "Offer",
            "price": str(listing.price),
            "priceCurrency": "RUB",
            "availability": "https://schema.org/InStock" if listing.status == 'active' else "https://schema.org/OutOfStock",
            "seller": {
                "@type": "Person",
                "name": listing.seller.username
            }
        }
    }
    
    if listing.image:
        schema["image"] = listing.image.url
    
    if listing.seller.profile.rating > 0:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(listing.seller.profile.rating),
            "bestRating": "5",
            "worstRating": "1",
            "ratingCount": str(listing.seller.profile.total_sales)
        }
    
    return schema


def get_organization_schema():
    """Schema.org для организации"""
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "LootLink",
        "description": "P2P маркетплейс для торговли игровыми предметами",
        "url": "http://91.218.245.178",
        "logo": "http://91.218.245.178/static/favicon.svg",
        "contactPoint": {
            "@type": "ContactPoint",
            "email": "ivanpetrov20066.ip@gmail.com",
            "contactType": "customer service"
        }
    }

