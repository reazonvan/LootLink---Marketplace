# Deployment Checklist - Phase 1

## Pre-Deployment Testing

### 1. Local Testing
```bash
# Start development server
python manage.py runserver

# Test URLs:
# - http://127.0.0.1:8000/ (homepage with badges)
# - http://127.0.0.1:8000/catalog/alphabet/ (alphabetical catalog)
# - http://127.0.0.1:8000/accounts/profile/[username]/ (profile with badges)
```

### 2. Verify Badge System
```python
python manage.py shell

from accounts.models import Profile
profile = Profile.objects.first()
badges = profile.get_badges()
print(badges)
# Should return list of badge dictionaries
```

### 3. Check for Errors
```bash
# Check for Python syntax errors
python manage.py check

# Run existing tests
python manage.py test
```

## Deployment Steps

### 1. Review Changes
```bash
git status
git diff
```

### 2. Commit Changes
```bash
git add .

git commit -m "Phase 1: User badges, alphabetical catalog, dark theme

- Add merit-based badge system (no paid advantages)
- Add alphabetical game catalog with navigation
- Add dark theme switcher
- Establish project principles (equality, unique design, honesty)
- Remove emojis from documentation
- Update roadmap (no premium features)

Features:
- 6 badge types (all earned, not bought)
- Alphabetical game catalog with sticky navigation
- Dark/light theme switcher with localStorage
- Comprehensive documentation

Files created: 16
Files modified: 18

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### 3. Push to Repository
```bash
git push origin main
```

### 4. Deploy to Server
```bash
# SSH to server
ssh user@your-server

# Navigate to project
cd /path/to/LootLink---Marketplace

# Pull changes
git pull origin main

# Collect static files
python manage.py collectstatic --noinput

# Restart services
docker-compose restart web

# OR if using systemd:
sudo systemctl restart lootlink
```

### 5. Verify Deployment
```bash
# Check logs
tail -f logs/lootlink.log

# Check for errors
docker-compose logs web --tail=50

# Test live site
curl -I https://lootlink.ru
```

### 6. Clear Cache (if needed)
```bash
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

## Post-Deployment Verification

### Check These URLs:
- [ ] https://lootlink.ru/ - homepage loads
- [ ] https://lootlink.ru/catalog/alphabet/ - alphabetical catalog works
- [ ] https://lootlink.ru/accounts/profile/[username]/ - badges display
- [ ] Theme switcher in navbar works
- [ ] Badges show on listing cards
- [ ] Mobile view (badges show icons only)

### Monitor Metrics:
- [ ] Page load times < 1 sec
- [ ] No JavaScript errors in console
- [ ] No Python errors in logs
- [ ] Cache is working (check Redis)

## Rollback Plan (if needed)

```bash
# If something breaks, rollback:
git revert HEAD
git push origin main

# On server:
git pull origin main
docker-compose restart web
```

## Notes

- All changes follow principle of user equality
- No paid advantages or premium features
- All badges are merit-based
- No emojis in user-facing content
- Design is unique, not generic AI patterns

## Support

If issues occur:
1. Check logs: `tail -f logs/lootlink.log`
2. Check browser console (F12)
3. Verify all files were uploaded
4. Clear browser cache
5. Clear Redis cache

---

Ready to deploy!
