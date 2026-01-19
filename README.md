<div align="center">

![LootLink Banner](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=210&section=header&text=LootLink&fontSize=82&fontColor=fff&animation=twinkling&fontAlignY=35)

<p align="center">
  <b>🎮 P2P Marketplace for Gaming Items</b><br/>
  Trade in-game items directly with players worldwide — fast, safe, and commission-free.
</p>

<p align="center">
  <a href="http://91.218.245.178"><img alt="Live Demo" src="https://img.shields.io/badge/🌐%20Live%20Demo-91.218.245.178-22c55e?style=for-the-badge"></a>
  <a href="docs/"><img alt="Docs" src="https://img.shields.io/badge/📖%20Docs-Read-3b82f6?style=for-the-badge"></a>
  <a href="https://github.com/reazonvan/LootLink---Marketplace/issues"><img alt="Issues" src="https://img.shields.io/badge/🐛%20Issues-Report-f43f5e?style=for-the-badge"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/🧾%20License-MIT-8b5cf6?style=for-the-badge"></a>
</p>

<p align="center">
  <a href="https://github.com/reazonvan/LootLink---Marketplace/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/reazonvan/LootLink---Marketplace?style=for-the-badge&logo=github&label=Stars&color=FACC15"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-111827?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-4.2+-111827?style=for-the-badge&logo=django&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-15+-111827?style=for-the-badge&logo=postgresql&logoColor=white">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-7.0+-111827?style=for-the-badge&logo=redis&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Ready-111827?style=for-the-badge&logo=docker&logoColor=white">
</p>

<br/>

<!-- quick nav -->
<p align="center">
  <a href="#-highlights">Highlights</a> •
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-security">Security</a> •
  <a href="#-testing">Testing</a> •
  <a href="#-deployment">Deployment</a>
</p>

</div>

---

## ✨ Highlights

<div align="center">

<table>
<tr>
<td width="33%" valign="top">

### 💸 Zero commission
Trade directly between players — no marketplace fee.

</td>
<td width="33%" valign="top">

### 🧾 Escrow-ready flow
Built for safer deals and dispute-resistant trades.

</td>
<td width="33%" valign="top">

### ⚡ Fast search & UX
Full-text search + filters + optimized queries & caching.

</td>
</tr>
</table>

</div>

---

## 📌 Project at a glance

<div align="center">

<table>
<tr>
<td align="center"><b>Lines</b><br/>32,000+</td>
<td align="center"><b>Coverage</b><br/>65%</td>
<td align="center"><b>Files</b><br/>221</td>
<td align="center"><b>Tech</b><br/>15+</td>
<td align="center"><b>Latency</b><br/>&lt; 200ms</td>
<td align="center"><b>Uptime</b><br/>99.9%</td>
</tr>
</table>

</div>

---

## 🎬 Features

### ✅ Core
- 🔁 **P2P Trading** — listings, offers, deal flow  
- 🧾 **Escrow-style protection** — safer transactions (flow-ready)
- 💬 **Real-time chat** — notifications + history
- 🔎 **Smart search** — PostgreSQL full-text + morphology
- ⭐ **Ratings & reviews** — trust system & reputation
- 🧠 **Recommendations** — deal tips / price tracking (optional blocks)

### 👤 Accounts
- Email verification (anti-spam)
- Profiles + avatars
- Favorites / watchlist
- Transaction history

### 🛠️ Admin
- User & content moderation
- Reports handling
- Logs / analytics
- Bulk actions

<details>
<summary><b>📋 Full feature list</b></summary>

<br/>

#### 👤 User Management
- ✅ Email & phone verification  
- ✅ Profile customization with avatars  
- ✅ Personal rating system  
- ✅ Transaction history  
- ✅ Favorites & watchlist  
- ✅ Push notifications  

#### 🛒 Marketplace
- ✅ Create & manage listings  
- ✅ Advanced filtering & sorting  
- ✅ Multi-game support  
- ✅ Image uploads (AWS S3 ready)  
- ✅ Price tracking  
- ✅ Deal recommendations  

#### 💬 Communication
- ✅ Real-time chat system  
- ✅ Conversation history  
- ✅ Read receipts  
- ✅ Email notifications  
- ✅ Mobile-optimized  

#### 🔒 Security
- ✅ CSRF & XSS protection  
- ✅ SQL injection prevention  
- ✅ Rate limiting (anti-spam)  
- ✅ Content Security Policy  
- ✅ Secure password hashing  
- ✅ Two-factor ready  

#### ⚡ Performance
- ✅ PostgreSQL full-text search  
- ✅ Redis caching  
- ✅ Query optimization  
- ✅ Lazy loading  
- ✅ CDN integration  
- ✅ Gzip compression  

</details>

---

## 🚀 Quick Start

> **Fastest:** Docker • **Dev:** venv + runserver

### 🐳 Docker (Recommended)

```bash
docker-compose up -d --build
docker-compose logs -f
