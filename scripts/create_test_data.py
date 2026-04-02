from accounts.models import CustomUser
from listings.models import Game, Listing

# Create users
if not CustomUser.objects.filter(username='reazonvan').exists():
    CustomUser.objects.create_superuser('reazonvan', 'admin@test.com', 'admin123')
    print('Created reazonvan')

if not CustomUser.objects.filter(username='seller1').exists():
    CustomUser.objects.create_user('seller1', 'seller@test.com', 'pass123')
    print('Created seller1')

# Create game
if not Game.objects.filter(slug='cs2').exists():
    game = Game.objects.create(name='Counter-Strike 2', slug='cs2')
    print('Created game')
else:
    game = Game.objects.get(slug='cs2')

# Get seller
seller = CustomUser.objects.get(username='seller1')

# Create listings
listings_data = [
    ('M4A4 Howl', 'Редкий скин с уникальным дизайном', 25000),
    ('AK-47 Fire Serpent', 'Легендарный скин огненного змея', 8500),
    ('AWP Dragon Lore', 'Эксклюзивный снайперский скин', 15000),
]

for title, desc, price in listings_data:
    if not Listing.objects.filter(title=title).exists():
        Listing.objects.create(
            title=title,
            description=desc,
            price=price,
            game=game,
            seller=seller,
            status='active'
        )
        print(f'Created: {title}')

print('Done!')
