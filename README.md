<h1 align="center">🤖 Roblox User Verifier</h1>

<p align="center">
A verification system that analyzes Roblox account authenticity, blacklist status, and activity patterns.<br>
Can be used as both a <b>Streamlit web app</b> and a <b>command-line tool</b>.
</p>

---

## 🔍 Overview

**Roblox User Verifier** evaluates the trustworthiness of a Roblox account using official API data and rule-based logic.  
It checks for account maturity, suspicious names, group affiliations, and blacklist status to help communities detect alt accounts and impersonators.

### Key Analysis Metrics
- 🧾 Account age and username quality  
- 👥 Friend count and group membership  
- 🏅 Badge history  
- 🚫 Blacklisted or impersonating identities  
- 📋 Configurable rule thresholds via `config.json`

---

## ⚙️ Features

| Category | Description |
|:--|:--|
| 🧭 Interfaces | Web UI (`app.py`) and Command-Line (`verification.py`) |
| ⚡ Performance | Cached Roblox API requests for fast lookup |
| 🔒 Blacklist Detection | Reads local CSV or live Google Sheets |
| ⚙️ Configurable Rules | Fully customizable via `config.json` |
| 📊 Reports | Displays avatars, flags, groups, and badge data |
| 💾 Export | Downloadable JSON reports for audit or automation |

---

## 🧠 Verification Flow

1. **Input** — Enter Roblox username  
2. **Fetch** — Retrieve user data via Roblox APIs  
3. **Evaluate** — Apply thresholds:
   - Account age ≥ 60 days  
   - ≥ 30 friends  
   - ≥ 13 non-BA groups  
   - ≥ 300 badges  
   - No blacklisted or impersonating usernames  
4. **Decision** —
   - ❌ Dismissed (blacklisted or fails major rules)  
   - ⚠️ Flagged (minor concerns)  
   - ✅ Verified (passes all rules)
5. **Output** —
   - Web UI → dashboard + downloadable JSON  
   - CLI → formatted terminal summary

---

## 💻 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Kapukaso/user-verifier.git
cd user-verifier
```

### 2️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

If missing:
```bash
pip install streamlit requests
```

### 3️⃣ Run Locally

#### Web Interface
```bash
streamlit run app.py
```

#### Command Line
```bash
python verification.py
```

---

## ⚙️ Configuration Guide

All rules are defined in **`config.json`**.

| Key | Purpose |
|:--|:--|
| `FRIENDLY_OWNER_IDS` | Trusted Roblox group owners |
| `BA_UK_GROUP_IDS` | Official BA Roblox group IDs |
| `BLACKLISTED_GROUP_IDS` | Suspicious group IDs |
| `BA_BADGE_IDS` | Restricted badge indicators |
| `IFD_BLACKLIST_IDS` | Known malicious user IDs |
| `BA_BLACKLIST_IDS` | Blacklisted BA-related accounts |
| `NSFW_WORDS` | Banned username keywords |
| `BA_MEMBER_IMPERSONATION_LIST` | Impersonated BA member names |

You can edit these fields to adapt rules to your community.

---

## 🌐 Live Blacklist Sync

Add a **Google Sheet CSV export URL** to dynamically load blacklists.

**Example:**
```
https://docs.google.com/spreadsheets/d/.../export?format=csv
```

Requirements:
- Must be a valid `docs.google.com` CSV export link  
- Automatically fetched during verification

---

## 📊 Example Outputs

### Streamlit Dashboard
- Avatar and profile link  
- Verification status with flags  
- Expandable lists for groups/badges  
- Downloadable JSON summary

### CLI Report
```
Roblox User Verification
========================
User: DisplayName (@Username)
User ID: 123456789
Status: ✅ VERIFIED
Total Flags: 1
→ Fewer than 13 non-BA groups (10)
```

---

## 🧩 Developer Notes

**Core APIs**
```
https://users.roblox.com/v1/users/
https://friends.roblox.com/v1/users/{id}/friends/count
https://groups.roblox.com/v1/users/{id}/groups/roles
https://badges.roblox.com/v1/users/{id}/badges
```

**Implementation Highlights**
- Uses Streamlit caching (`@st.cache_data`)
- Supports VS Code Dev Containers via `.devcontainer/`
- Config-driven and modular for easy expansion

---

## ⚠️ Limitations

- Dependent on Roblox’s public APIs (rate-limited)
- Google Sheets must be public CSV links
- Manual review suggested for edge cases

---

## 📜 License

Released under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.

---

## 👤 Maintainer

**Kapukaso**  
GitHub: [Kapukaso/user-verifier](https://github.com/Kapukaso/user-verifier)

---
