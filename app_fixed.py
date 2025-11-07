# app_fixed.py
"""
Roblox User Verifier - fixed and hardened single-file Streamlit app.
Changes:
- Only config loading is cached.
- Network calls use a requests.Session with retries and sensible timeouts.
- Defensive parsing of API responses and config values.
- No infinite pagination loops (max_pages enforced).
- Safer live blacklist fetch via csv.reader and strict host checks.
- Clear separation: data fetching, checks, UI flow.
- Reduced duplicate API calls; reused results where needed.
"""

import streamlit as st
import requests
import json
import datetime
import re
import csv
import io
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter, Retry

# --------- Configuration ----------
CONFIG_FILE = "config.json"

@st.cache_data(show_spinner=False)
def load_config(path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Load config.json. Return an empty dict if missing but note in UI."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("Config root must be a JSON object.")
            return raw
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

config = load_config()

# Helper to coerce lists/values from config safely
def _to_int_set(value, name: str) -> Set[int]:
    out = set()
    if value is None:
        return out
    if isinstance(value, (list, tuple, set)):
        for v in value:
            try:
                out.add(int(v))
            except Exception:
                # ignore non-int entries
                continue
    else:
        try:
            out.add(int(value))
        except Exception:
            pass
    return out

def _to_str_set(value) -> Set[str]:
    out = set()
    if value is None:
        return out
    if isinstance(value, (list, tuple, set)):
        for v in value:
            try:
                out.add(str(v).lower())
            except Exception:
                continue
    else:
        out.add(str(value).lower())
    return out

# Config-derived constants with safe defaults
FRIENDLY_OWNER_IDS: Set[int] = _to_int_set(config.get("FRIENDLY_OWNER_IDS", []), "FRIENDLY_OWNER_IDS")
BA_UK_GROUP_IDS: Set[int] = _to_int_set(config.get("BA_UK_GROUP_IDS", []), "BA_UK_GROUP_IDS")
BLACKLISTED_GROUP_IDS: Set[int] = _to_int_set(config.get("BLACKLISTED_GROUP_IDS", []), "BLACKLISTED_GROUP_IDS")
BA_BADGE_IDS: Set[int] = _to_int_set(config.get("BA_BADGE_IDS", []), "BA_BADGE_IDS")
IFD_BLACKLIST_IDS: Set[int] = _to_int_set(config.get("IFD_BLACKLIST_IDS", []), "IFD_BLACKLIST_IDS")
BA_BLACKLIST_IDS: Set[int] = _to_int_set(config.get("BA_BLACKLIST_IDS", []), "BA_BLACKLIST_IDS")
NSFW_WORDS: Set[str] = _to_str_set(config.get("NSFW_WORDS", []))
BA_MEMBER_IMPERSONATION_LIST: Set[str] = _to_str_set(config.get("BA_MEMBER_IMPERSONATION_LIST", []))

# Thresholds (config overrides allowed; fallback to hard defaults)
def _get_int_cfg(key: str, default: int) -> int:
    try:
        v = config.get(key, default)
        return int(v)
    except Exception:
        return default

MIN_ACCOUNT_AGE_DAYS = _get_int_cfg("MIN_ACCOUNT_AGE_DAYS", 60)
MIN_FRIEND_COUNT = _get_int_cfg("MIN_FRIEND_COUNT", 30)
MIN_NON_BA_GROUP_COUNT = _get_int_cfg("MIN_NON_BA_GROUP_COUNT", 13)
MIN_BADGE_COUNT = _get_int_cfg("MIN_BADGE_COUNT", 300)
OLDEST_BADGES_TO_CHECK = _get_int_cfg("OLDEST_BADGES_TO_CHECK", 90)
USERNAME_DIGIT_THRESHOLD = _get_int_cfg("USERNAME_DIGIT_THRESHOLD", 4)
MAX_BADGE_PAGES = _get_int_cfg("MAX_BADGE_PAGES", 10)  # prevents infinite loops
REQUEST_TIMEOUT = _get_int_cfg("REQUEST_TIMEOUT_SECONDS", 6)

# --------- Requests session with retries ----------
def make_session(retries: int = 2, backoff_factor: float = 0.3) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"])
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "Roblox-User-Verifier/1.0"})
    return s

_session = make_session()

# --------- API helper functions (no caching for user-specific calls) ----------
def get_user_id_from_username(username: str) -> Optional[int]:
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    try:
        r = _session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        uid = data[0].get("id")
        return int(uid) if uid is not None else None
    except Exception:
        return None

def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        r = _session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None

def get_user_avatar_url(user_id: int) -> Optional[str]:
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
    params = {"userIds": user_id, "size": "150x150", "format": "Png", "isCircular": "false"}
    try:
        r = _session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        return data[0].get("imageUrl")
    except Exception:
        return None

def get_friend_count(user_id: int) -> Optional[int]:
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
    try:
        r = _session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        c = r.json().get("count")
        return int(c) if c is not None else None
    except Exception:
        return None

def get_user_groups(user_id: int) -> Optional[List[Dict[str, Any]]]:
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    try:
        r = _session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        d = r.json().get("data", [])
        return d if isinstance(d, list) else []
    except Exception:
        return None

def get_oldest_badges(user_id: int, total_limit: int = OLDEST_BADGES_TO_CHECK) -> List[Dict[str, Any]]:
    badges: List[Dict[str, Any]] = []
    cursor = ""
    page_limit = 100
    base_url = f"https://badges.roblox.com/v1/users/{user_id}/badges"
    seen_cursors = set()
    pages = 0
    while len(badges) < total_limit and pages < MAX_BADGE_PAGES:
        pages += 1
        params = {"limit": page_limit, "sortOrder": "Asc"}
        if cursor:
            params["cursor"] = cursor
        try:
            r = _session.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            new_badges = data.get("data", [])
            if not new_badges:
                break
            badges.extend(new_badges)
            next_cursor = data.get("nextPageCursor") or ""
            # break on repeated cursor to avoid infinite loop
            if next_cursor in seen_cursors:
                break
            if not next_cursor:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        except Exception:
            break
    return badges[:total_limit]

def get_total_badge_count(user_id: int, pass_threshold: int = MIN_BADGE_COUNT) -> int:
    total_badges = 0
    cursor = ""
    page_limit = 100
    base_url = f"https://badges.roblox.com/v1/users/{user_id}/badges"
    seen_cursors = set()
    pages = 0
    while pages < MAX_BADGE_PAGES:
        pages += 1
        params = {"limit": page_limit, "sortOrder": "Desc"}
        if cursor:
            params["cursor"] = cursor
        try:
            r = _session.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            new_badges = data.get("data", [])
            if not new_badges:
                break
            total_badges += len(new_badges)
            if total_badges >= pass_threshold:
                return total_badges
            next_cursor = data.get("nextPageCursor") or ""
            if not next_cursor:
                break
            if next_cursor in seen_cursors:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        except Exception:
            break
    return total_badges

# --------- Logic functions ----------
def check_account_age(user_info: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Returns: (is_instant_dismissal, human_message)
    Only dismiss if account clearly younger than MIN_ACCOUNT_AGE_DAYS.
    If cannot parse/verify creation date, do not dismiss; return informative message.
    """
    created_str = user_info.get("created")
    if not created_str:
        return False, "Created date not available. Manual review required."
    try:
        # robust parsing for Z or offset
        if created_str.endswith("Z"):
            created_date = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        else:
            created_date = datetime.datetime.fromisoformat(created_str)
            if created_date.tzinfo is None:
                created_date = created_date.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return False, f"Could not parse creation date: {created_str}"
    age = datetime.datetime.now(datetime.timezone.utc) - created_date
    days_old = age.days
    if days_old < MIN_ACCOUNT_AGE_DAYS:
        return True, f"Account is {days_old} days old (under {MIN_ACCOUNT_AGE_DAYS})."
    return False, f"Account is {days_old} days old."

def check_username(user_info: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """
    Returns (dismissal_reason_or_None, list_of_flag_messages)
    Dismiss only for strong evidence of impersonation or explicit 'alt' etc.
    """
    dismissal = None
    flags: List[str] = []
    username = str(user_info.get("name", "")).lower()
    if "alt" in username:
        # flag as suspicious but not necessarily immediate dismissal
        flags.append("Username contains 'alt'.")
    if username in BA_MEMBER_IMPERSONATION_LIST:
        dismissal = "Username impersonates a BA member."
    for word in NSFW_WORDS:
        if word and word in username:
            dismissal = dismissal or f"Username contains offensive term: '{word}'."
    # numeric username heuristic
    digits = sum(ch.isdigit() for ch in username)
    if digits >= USERNAME_DIGIT_THRESHOLD:
        flags.append(f"Username contains {digits} digits (>= {USERNAME_DIGIT_THRESHOLD}).")
    return dismissal, flags

def check_social_activity(user_id: int, groups: List[Dict[str, Any]]) -> List[str]:
    """
    Produces red-flag messages. Does not perform instant dismissals.
    Reuses API calls locally to avoid duplicates.
    """
    red_flags: List[str] = []
    # friend count
    friend_count = get_friend_count(user_id)
    if friend_count is None:
        red_flags.append("Could not verify friend count.")
    elif friend_count < MIN_FRIEND_COUNT:
        red_flags.append(f"Fewer than {MIN_FRIEND_COUNT} friends ({friend_count}).")

    # groups: ensure groups is list
    groups_list = groups or []
    non_ba_groups = []
    for g in groups_list:
        grp = g.get("group") if isinstance(g, dict) else None
        if not grp:
            continue
        gid = grp.get("id")
        if gid is None:
            continue
        try:
            gid_int = int(gid)
        except Exception:
            continue
        if gid_int not in BA_UK_GROUP_IDS:
            non_ba_groups.append(g)
    non_ba_group_count = len(non_ba_groups)
    if non_ba_group_count < MIN_NON_BA_GROUP_COUNT:
        red_flags.append(f"Fewer than {MIN_NON_BA_GROUP_COUNT} non-BA groups ({non_ba_group_count}).")

    # badges
    badge_count = get_total_badge_count(user_id, MIN_BADGE_COUNT)
    if badge_count < MIN_BADGE_COUNT:
        red_flags.append(f"Fewer than {MIN_BADGE_COUNT} badges ({badge_count} total).")

    # oldest badges check for BA badge IDs
    oldest_badges = get_oldest_badges(user_id, min(OLDEST_BADGES_TO_CHECK, 100))
    for badge in oldest_badges:
        bid = badge.get("id")
        if bid is None:
            continue
        try:
            if int(bid) in BA_BADGE_IDS:
                red_flags.append(f"BA-related badge found among oldest badges (ID: {bid}).")
                break
        except Exception:
            continue

    return red_flags

def check_blacklists(user_id: int, groups: List[Dict[str, Any]], ifd_blacklist: Set[int]) -> List[str]:
    dismissals: List[str] = []
    if user_id in ifd_blacklist:
        dismissals.append("User is on the IFD Blacklist.")
    if user_id in BA_BLACKLIST_IDS:
        dismissals.append("User is on the BA Blacklist.")
    groups_list = groups or []
    for item in groups_list:
        grp = item.get("group") if isinstance(item, dict) else None
        if not isinstance(grp, dict):
            continue
        group_id = grp.get("id")
        group_name = str(grp.get("name", "")).lower()
        owner = grp.get("owner")
        owner_id = None
        if isinstance(owner, dict):
            owner_id = owner.get("userId")
            try:
                owner_id = int(owner_id) if owner_id is not None else None
            except Exception:
                owner_id = None
        try:
            group_id_int = int(group_id) if group_id is not None else None
        except Exception:
            group_id_int = None
        if group_id_int in BLACKLISTED_GROUP_IDS:
            dismissals.append(f"User is in a blacklisted group: {grp.get('name')}.")
        # detect other 'british army' groups not in BA_UK_GROUP_IDS and not owned by known friendly owners
        if "british army" in group_name and (group_id_int not in BA_UK_GROUP_IDS) and (owner_id not in FRIENDLY_OWNER_IDS):
            dismissals.append(f"User is in another British Army group: {grp.get('name')}.")
    return dismissals

# --------- Live blacklist fetch (safer) ----------
def fetch_live_blacklist(sheet_csv_url: str) -> Set[int]:
    """
    Accepts only Google Sheets CSV export URLs hosted at docs.google.com.
    Parses CSV properly via csv.reader.
    Returns set of ints found in the CSV cells.
    """
    ids: Set[int] = set()
    if not sheet_csv_url:
        return ids
    try:
        parsed = urlparse(sheet_csv_url)
        # Require secure scheme and exact host
        if parsed.scheme not in ("https",):
            return ids
        hostname = parsed.hostname or ""
        # Accept docs.google.com only
        if hostname != "docs.google.com":
            return ids
        # Quick sanity: exported CSV URLs often contain '/export?'
        if "export" not in parsed.path and "spreadsheets" not in parsed.path:
            # still allow but conservative
            pass
        r = _session.get(sheet_csv_url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        # parse CSV robustly
        text = r.content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            for col in row:
                s = col.strip()
                if s.isdigit():
                    try:
                        ids.add(int(s))
                    except Exception:
                        continue
    except Exception:
        # silence network/parse errors and return empty set
        return set()
    return ids

# --------- Utilities ----------
def safe_filename(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]", "_", s)
    return s[:200]

# --------- UI ----------
st.set_page_config(page_title="Roblox User Verifier", layout="wide")
st.title("Roblox User Verifier")

st.sidebar.title("Verification Options")
username = st.sidebar.text_input("Roblox username", value="", help="Enter the Roblox username to verify.")
sheet_url = st.sidebar.text_input("Optional: Live blacklist CSV URL (public Google Sheet export URL)", value="", help="Provide CSV export link to include more blacklist IDs.")
run = st.sidebar.button("Run Verification")

st.sidebar.markdown("---")
with st.sidebar.expander("Config summary"):
    st.write(
        {
            "Friendly owner IDs": len(FRIENDLY_OWNER_IDS),
            "BA UK groups": len(BA_UK_GROUP_IDS),
            "Blacklisted groups": len(BLACKLISTED_GROUP_IDS),
            "BA badge IDs": len(BA_BADGE_IDS),
            "IFD blacklist users": len(IFD_BLACKLIST_IDS),
            "BA blacklist users": len(BA_BLACKLIST_IDS),
            "NSFW words": len(NSFW_WORDS),
        }
    )

st.markdown("---")

if run:
    if not username:
        st.error("Provide a username.")
    else:
        clean_username = username.strip()
        if not clean_username:
            st.error("Provide a non-empty username.")
        else:
            with st.spinner("Resolving username to user id..."):
                user_id = get_user_id_from_username(clean_username)
            if not user_id:
                st.error(f"User '{clean_username}' not found.")
            else:
                st.success(f"Found user id: {user_id}")
                with st.spinner("Fetching user info and groups..."):
                    user_info = get_user_info(user_id)
                    groups = get_user_groups(user_id)
                if user_info is None:
                    st.error("Could not fetch user info from Roblox API.")
                elif groups is None:
                    st.error("Could not fetch groups from Roblox API.")
                else:
                    # live blacklist (non-blocking)
                    if sheet_url:
                        with st.spinner("Fetching live blacklist..."):
                            live_ids = fetch_live_blacklist(sheet_url)
                        if live_ids:
                            st.info(f"Loaded {len(live_ids)} IDs from live blacklist. Merging into IFD blacklist for this run.")
                            temp_ifd = set(IFD_BLACKLIST_IDS) | set(live_ids)
                        else:
                            st.warning("Could not load blacklist or no IDs found at provided URL. Using stored IFD blacklist.")
                            temp_ifd = set(IFD_BLACKLIST_IDS)
                    else:
                        temp_ifd = set(IFD_BLACKLIST_IDS)

                    # Run checks
                    instant_dismissals: List[str] = []
                    red_flags: List[str] = []

                    # Account age
                    is_dismissed_age, age_msg = check_account_age(user_info)
                    if is_dismissed_age:
                        instant_dismissals.append(age_msg)
                    else:
                        # if not dismissed, still record informational msg if parsing failed
                        if "Could not parse" in age_msg or "not available" in age_msg:
                            red_flags.append(age_msg)

                    # Username checks
                    dismissal_reason, flag_reasons = check_username(user_info)
                    if dismissal_reason:
                        instant_dismissals.append(dismissal_reason)
                    red_flags.extend(flag_reasons)

                    # Blacklists
                    instant_dismissals.extend(check_blacklists(user_id, groups, temp_ifd))

                    # Instant dismissal UI
                    st.header("Summary")
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        avatar_url = get_user_avatar_url(user_id)
                        if avatar_url:
                            st.image(avatar_url, caption=user_info.get("name"), width=150)
                        else:
                            st.write("No avatar found.")
                    with col2:
                        st.write(f"**Display Name:** {user_info.get('displayName')}")
                        st.write(f"**Username:** @{user_info.get('name')}")
                        st.write(f"**User ID:** {user_id}")
                        st.markdown(f"**[View Profile on Roblox](https://www.roblox.com/users/{user_id}/profile)**")

                    if instant_dismissals:
                        st.error("### ❌ INSTANT DISMISSAL")
                        for i, r in enumerate(instant_dismissals, 1):
                            st.error(f"{i}. {r}")
                        st.stop()

                    # Social checks (friends, badges, groups)
                    with st.spinner("Running social activity checks (friends, groups, badges)..."):
                        activity_flags = check_social_activity(user_id, groups)
                    red_flags.extend(activity_flags)

                    st.subheader("Final Report")
                    st.metric("Total Red Flags", len(red_flags))

                    if len(red_flags) >= 2:
                        st.error("### ❌ DISMISSED (2+ red flags)")
                    else:
                        st.success("### ✅ VERIFIED (fewer than 2 red flags)")

                    if red_flags:
                        st.write("#### Red Flags Found:")
                        for i, r in enumerate(red_flags, 1):
                            st.warning(f"{i}. {r}")
                    else:
                        st.write("No red flags found.")

                    st.info(
                        """
                        ### Manual checks required
                        - Review friends list for suspicious / 'bacon' alts.
                        - Manually inspect groups listed below.
                        """
                    )

                    # Show groups table safely
                    with st.expander("Groups (first 200 shown)"):
                        if groups:
                            groups_display = []
                            for g in groups[:200]:
                                grp = g.get("group") if isinstance(g, dict) else None
                                if not grp:
                                    continue
                                role_obj = g.get("role")
                                role_name = role_obj.get("name") if isinstance(role_obj, dict) else role_obj
                                owner_obj = grp.get("owner")
                                owner_id = owner_obj.get("userId") if isinstance(owner_obj, dict) else None
                                groups_display.append(
                                    {
                                        "group_id": grp.get("id"),
                                        "group_name": grp.get("name"),
                                        "role": role_name,
                                        "owner_id": owner_id,
                                    }
                                )
                            if groups_display:
                                st.table(groups_display)
                            else:
                                st.write("No groups found or no displayable group data.")
                        else:
                            st.write("No groups found or could not fetch groups.")

                    # Oldest badges summary
                    with st.expander("Oldest badges (sample)"):
                        with st.spinner("Fetching oldest badges..."):
                            oldest = get_oldest_badges(user_id, min(30, OLDEST_BADGES_TO_CHECK))
                        if oldest:
                            badges_display = []
                            for b in oldest:
                                awarded = b.get("awarded") or b.get("awardedAt") or b.get("awarded_at")
                                badges_display.append(
                                    {
                                        "id": b.get("id"),
                                        "name": b.get("name"),
                                        "awarded": awarded,
                                    }
                                )
                            st.table(badges_display)
                        else:
                            st.write("No badges or could not fetch badges.")

                    # Downloadable report
                    report = {
                        "user_id": user_id,
                        "displayName": user_info.get("displayName"),
                        "username": user_info.get("name"),
                        "instant_dismissals": instant_dismissals,
                        "red_flags": red_flags,
                        "groups_count": len(groups) if isinstance(groups, list) else 0,
                        "friend_count": get_friend_count(user_id),
                        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    filename = safe_filename(f"report_{user_id}.json")
                    st.download_button(
                        "Download report (JSON)",
                        json.dumps(report, indent=2, ensure_ascii=False),
                        file_name=filename,
                        mime="application/json",
                    )
