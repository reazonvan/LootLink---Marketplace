# LootLink Project Rules

## Core Principles

### 1. User Equality
- All users have equal opportunities
- No paid advantages or subscriptions
- Success depends only on work quality and reputation
- Badges are earned through activity, not purchased

### 2. Design Uniqueness
- Avoid generic AI design patterns
- Create our own visual language
- Minimalist but memorable
- Functionality over decoration
- No emojis in code or user-facing content

### 3. Honesty and Transparency
- No hidden fees
- Transparent rating system
- Open platform statistics
- Fair rules for everyone

---

## What We DON'T Do

### Forbidden:
- Emojis in interface and documentation
- Premium subscriptions with advantages
- VIP statuses for money
- Paid listing promotion (gives unfair advantage)
- Generic gradients and effects
- Excessive animation
- Aggressive monetization

### Instead:
- Clean text and icons
- Equal conditions for all
- Merit-based badges
- Organic ranking by quality
- Unique color scheme
- Smooth, unobtrusive transitions
- Honest business model

---

## Monetization (Right Approach)

### Acceptable Revenue Sources:

1. **Optional Services (no advantages):**
   - Extended analytics for sellers
   - Data export
   - API access for integrations

2. **Partnership Programs:**
   - Referral system (bonuses for both sides)
   - Partnership with gaming companies

3. **Voluntary Contributions:**
   - Donations for platform development
   - Community support

### Unacceptable Sources:
- Sales commissions (we are P2P platform)
- Paid listing promotion
- Premium accounts with advantages
- Paid badges
- Third-party advertising

---

## Design System

### Colors:
- Primary: #2563eb (blue) - actions, links
- Success: #10b981 (green) - success, verification
- Warning: #f59e0b (orange) - attention, important
- Danger: #ef4444 (red) - errors, deletion
- Dark: #1e293b (dark gray) - text, headers
- Light: #f8fafc (light gray) - background

### Avoid:
- Acid colors
- Typical AI gradients (purple-pink)
- Neon shades
- Too bright accents

### Typography:
- Main: System fonts (San Francisco, Segoe UI, Roboto)
- Headers: Weight 600-700
- Text: Weight 400-500
- Sizes: 14px (text), 16px (large text), 24-32px (headers)

---

## Code Style

### Python:
- Follow PEP 8
- Type hints where applicable
- Docstrings for all public functions
- No emojis in code comments

### Templates:
- Clean, semantic HTML
- Bootstrap 5 components
- No inline styles (use classes)
- Accessibility first (WCAG AA)

### JavaScript:
- ES6+ syntax
- Minimal dependencies
- Progressive enhancement
- No jQuery for new code

---

## Documentation

### Style:
- Clear, concise language
- No emojis
- Code examples for complex features
- English for technical terms

### Structure:
- README.md - project overview
- docs/ - detailed documentation
- CHANGELOG.md - version history
- CONTRIBUTING.md - contribution guidelines

---

## Testing

### Requirements:
- 80%+ code coverage
- Unit tests for all models
- Integration tests for views
- E2E tests for critical paths

### Tools:
- pytest for Python
- Playwright for E2E
- Django Debug Toolbar for profiling

---

## Performance

### Requirements:
- Homepage load < 1 sec
- Time to Interactive < 2 sec
- Lighthouse Score > 90
- Minimal HTTP requests

### Methods:
- Lazy loading images
- Code splitting
- Caching (Redis)
- Minification CSS/JS

---

## Security

### Mandatory:
- CSRF protection
- XSS prevention
- SQL injection protection (ORM)
- Rate limiting
- Security headers

### Testing:
- Regular security audits
- Dependency updates
- Penetration testing
- Bug bounty program (future)

---

## Accessibility

### Requirements:
- Text contrast (WCAG AA)
- Alt text for images
- Keyboard navigation
- Screen reader support
- Focus indicators

### Testing:
- VoiceOver/NVDA testing
- Keyboard-only navigation
- Contrast checking
- Testing on different devices

---

## Git Workflow

### Branches:
- main - production
- develop - development
- feature/* - new features
- fix/* - bug fixes

### Commits:
- Clear, descriptive messages
- Reference issues when applicable
- Co-authored by Claude when AI-assisted

### Pull Requests:
- Description of changes
- Screenshots for UI changes
- Tests passing
- Code review required

---

## Deployment

### Environments:
- Development (local)
- Staging (testing)
- Production (live)

### Process:
1. Test locally
2. Deploy to staging
3. Run smoke tests
4. Deploy to production
5. Monitor logs

---

These rules are the foundation of LootLink. They help create an honest, convenient, and unique platform.

---

## AI Assistant Communication Protocol

### Response Pattern:
1. **First: Acknowledge and Explain**
   - Confirm understanding of the request
   - Explain what will be done
   - Outline the approach
   - Ask clarifying questions if needed

2. **Then: Execute**
   - Make tool calls
   - Perform the actual work
   - Show results

### Example:

**WRONG:**
User: "Add a new feature"
Assistant: [immediately starts making tool calls without explanation]

**CORRECT:**
User: "Add a new feature"
Assistant: "Understood. I'll add the feature by creating X file and modifying Y. This will involve Z steps. Starting now..."
[then makes tool calls]

### Why This Matters:
- User always knows what's happening
- Prevents misunderstandings
- Allows user to stop/redirect before work begins
- Makes the process transparent

### Work Priority:
1. **Focus on Real Changes**
   - Prioritize actual code changes over documentation
   - Create .md files only when explicitly requested
   - Don't create reports/summaries unless asked
   - Action > Documentation

2. **When to Create Documentation:**
   - User explicitly asks for it
   - Critical technical documentation (API, architecture)
   - Setup/deployment guides that are essential
   - NOT: progress reports, summaries, completion reports

3. **What to Do Instead:**
   - Make the actual changes
   - Fix the actual bugs
   - Implement the actual features
   - Brief verbal summary at the end (2-3 sentences max)

---
