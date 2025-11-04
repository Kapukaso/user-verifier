Here’s a concise, professional **README.md** suitable for the `user-verifier` repository:

---

````markdown
# Roblox User Verifier

A verification system for Roblox users that automatically analyzes account authenticity, blacklist status, and activity patterns.  
It can be used as both a **Streamlit web app** and a **command-line tool**.

---

## 🔍 Overview

The **Roblox User Verifier** checks a player’s trustworthiness using public Roblox API data and configurable rule sets.  
It evaluates multiple factors such as:

- Account age  
- Username characteristics (e.g., “alt”, impersonation, NSFW)  
- Friend count and group activity  
- Badge count and history  
- Membership in known blacklisted groups  
- Presence in internal or live blacklists

The system helps Roblox communities, moderators, or recruiters quickly filter alt accounts, impersonators, and malicious users.

---

## ⚙️ Features

- ✅ **Two Interfaces** — Streamlit Web UI (`app.py`) and Command-Line Interface (`verification.py`)  
- ⚡ **Fast API Access** — Uses Roblox REST APIs with caching  
- 🔒 **Blacklist Detection** — Reads local and live blacklists from CSV or Google Sheets  
- 🧩 **Configurable Rules** — Adjust thresholds and groups in `config.json`  
- 📊 **Visual Reports** — Displays avatars, flags, and group/badge data  
- 💾 **Downloadable Reports** — JSON output for recordkeeping or automation

---

## 🧠 How It Works

1. **Input** — Enter a Roblox username.  
2. **Fetch** — The app queries Roblox APIs for user info, badges, friends, and groups.  
3. **Check Rules** — The verifier runs:
   - Account age ≥ 60 days  
   - ≥ 30 friends  
   - ≥ 13 non-BA groups  
   - ≥ 300 badges  
   - No banned or impersonating usernames  
   - Not part of blacklisted groups or IDs  
4. **Decision** —  
   - ❌ *Instant Dismissal* if blacklisted or fails major rules  
   - ⚠️ *Red Flags* if minor issues are found  
   - ✅ *Verified* if safe or trusted  
5. **Output** —  
   - Web UI: summary dashboard + downloadable JSON report  
   - CLI: formatted terminal report

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Kapukaso/user-verifier.git
cd user-verifier
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:

```bash
pip install streamlit requests
```

### 3. Run locally

#### Web App (Streamlit)

```bash
streamlit run app.py
```

Then open the provided local URL in your browser.

#### Command-Line Version

```bash
python verification.py
```

---

## 🧰 Configuration

All verification rules and IDs are stored in **`config.json`**.

Key sections:

| Field                          | Purpose                                   |
| ------------------------------ | ----------------------------------------- |
| `FRIENDLY_OWNER_IDS`           | Trusted group owners                      |
| `BA_UK_GROUP_IDS`              | Official British Army Roblox groups       |
| `BLACKLISTED_GROUP_IDS`        | Suspicious or banned group IDs            |
| `BA_BADGE_IDS`                 | Badges indicating restricted groups       |
| `IFD_BLACKLIST_IDS`            | Known malicious or fraudulent user IDs    |
| `BA_BLACKLIST_IDS`             | Blacklisted British Army-related accounts |
| `NSFW_WORDS`                   | Words banned in usernames                 |
| `BA_MEMBER_IMPERSONATION_LIST` | List of impersonated members              |

You can add or remove IDs as needed.

---

## 🌐 Live Blacklist Support

Optionally, you can link a **Google Sheet CSV export** URL to fetch additional blacklist IDs dynamically.

* Must be a `docs.google.com` CSV export link.
* Loaded dynamically when provided in the sidebar.

Example:

```
https://docs.google.com/spreadsheets/d/.../export?format=csv
```

---

## 🧾 Output Example

### Web App Summary:

* Avatar + Roblox profile link
* Instant dismissal or verified result
* Red flags with details
* Expandable lists of user groups and badges
* Downloadable JSON report

### CLI Report:

```
Roblox User Verification Script
==============================
Fetching data for 'Username'...
> Found User: DisplayName (@Username)
> User ID: 123456789
...
Status: ✅ VERIFIED
Total Red Flags: 1
1. Fewer than 13 non-BA groups (10)
```

---

## 🧩 Developer Notes

* APIs used:

  * `https://users.roblox.com/v1/users/`
  * `https://friends.roblox.com/v1/users/{id}/friends/count`
  * `https://groups.roblox.com/v1/users/{id}/groups/roles`
  * `https://badges.roblox.com/v1/users/{id}/badges`
* `app.py` uses caching via `@st.cache_data` for efficiency.
* `.devcontainer/` supports GitHub Codespaces or VS Code Dev Containers with auto-install and launch.

---

## ⚠️ Limitations

* Dependent on Roblox’s public APIs; rate-limited if overused.
* Live blacklist fetching supports only Google Sheets CSV URLs.
* Manual review still recommended for borderline cases.

---

## 📜 License

This project is available under the **MIT License**.
See the [LICENSE](LICENSE) file if present.

---

## 🧩 Maintainer

Developed by **Kapukaso**
GitHub: [Kapukaso/user-verifier](https://github.com/Kapukaso/user-verifier)

---

```

---

**Q3:** Do you want a shorter “user-focused” README (for moderators using the web app only)?
```
