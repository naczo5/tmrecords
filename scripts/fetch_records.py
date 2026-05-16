#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv


LIVE_BASE_URL = "https://live-services.trackmania.nadeo.live"
CORE_BASE_URL = "https://prod.trackmania.core.nadeo.online"
TM_API_BASE_URL = "https://api.trackmania.com"
UBI_APP_ID = "86263886-327a-4328-ac69-527f0d20a237"
DEFAULT_USER_AGENT = "TM Records Tracker / https://github.com/naczo5/tmrecords"
RELEVANT_CHANGE_DAYS = 1095


class FetchWarning:
    def __init__(self):
        self.messages = []

    def add(self, message):
        self.messages.append(message)
        print(f"warning: {message}", file=sys.stderr)


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def isoformat_z(value):
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def strip_mania_codes(text):
    if not text:
        return text
    return re.sub(r"\$[a-z0-9]{1,3}", "", text, flags=re.IGNORECASE).strip()


def read_json(path, default):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default


def write_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def chunked(values, size):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class TrackmaniaClient:
    def __init__(self, warnings):
        self.warnings = warnings
        self.session = requests.Session()
        self.user_agent = os.getenv("TM_USER_AGENT") or DEFAULT_USER_AGENT
        self.session.headers.update({"User-Agent": self.user_agent})
        self.nadeo_token = None
        self.oauth_token = None

    def request(self, method, url, *, expected=(200,), **kwargs):
        timeout = kwargs.pop("timeout", 30)
        max_attempts = kwargs.pop("max_attempts", 3)
        response = None

        for attempt in range(1, max_attempts + 1):
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == max_attempts:
                break

            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay = min(int(retry_after), 120)
            else:
                delay = min(10 * attempt, 60)
            print(f"{method} {url} returned {response.status_code}; retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)

        if response.status_code not in expected:
            body = response.text[:500].replace("\n", " ")
            raise RuntimeError(f"{method} {url} returned {response.status_code}: {body}")
        return response

    def authenticate(self):
        client_id = require_env("TM_CLIENT_ID")
        client_secret = require_env("TM_CLIENT_SECRET")

        dedi_login = os.getenv("TM_DEDI_LOGIN")
        dedi_password = os.getenv("TM_DEDI_PASSWORD")
        if dedi_login and dedi_password:
            self.authenticate_nadeo_with_dedicated_server(dedi_login, dedi_password)
        else:
            self.authenticate_nadeo_with_ubisoft()

        oauth_response = self.request(
            "POST",
            f"{TM_API_BASE_URL}/api/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=20,
        )
        self.oauth_token = oauth_response.json().get("access_token")
        if not self.oauth_token:
            raise RuntimeError("Trackmania OAuth response did not include an access_token")

    def authenticate_nadeo_with_dedicated_server(self, login, password):
        basic = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("ascii")
        response = self.request(
            "POST",
            f"{CORE_BASE_URL}/v2/authentication/token/basic",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
            json={"audience": "NadeoLiveServices"},
            timeout=20,
        )
        self.nadeo_token = response.json().get("accessToken")
        if not self.nadeo_token:
            raise RuntimeError("Dedicated server authentication response did not include an accessToken")

        print("authenticated to Nadeo Live with dedicated server credentials")

    def authenticate_nadeo_with_ubisoft(self):
        ubi_email = require_env("UBI_EMAIL")
        ubi_password = require_env("UBI_PASS")
        basic = base64.b64encode(f"{ubi_email}:{ubi_password}".encode("utf-8")).decode("ascii")
        ubi_response = self.request(
            "POST",
            "https://public-ubiservices.ubi.com/v3/profiles/sessions",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/json",
                "Ubi-AppId": UBI_APP_ID,
                "Ubi-RequestedPlatformType": "uplay",
                "User-Agent": self.user_agent,
            },
            json={},
            timeout=20,
        )
        ubi_ticket = ubi_response.json().get("ticket")
        if not ubi_ticket:
            raise RuntimeError("Ubisoft session response did not include a ticket")

        nadeo_response = self.request(
            "POST",
            f"{CORE_BASE_URL}/v2/authentication/token/ubiservices",
            headers={
                "Authorization": f"ubi_v1 t={ubi_ticket}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
            json={"audience": "NadeoLiveServices"},
            timeout=20,
        )
        self.nadeo_token = nadeo_response.json().get("accessToken")
        if not self.nadeo_token:
            raise RuntimeError("Nadeo authentication response did not include an accessToken")

        print("authenticated to Nadeo Live with Ubisoft credentials")

    def live_headers(self):
        return {
            "Authorization": f"nadeo_v1 t={self.nadeo_token}",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }

    def oauth_headers(self):
        return {
            "Authorization": f"Bearer {self.oauth_token}",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }

    def get_json(self, url, *, auth="live", expected=(200,)):
        headers = self.live_headers() if auth == "live" else self.oauth_headers()
        return self.request("GET", url, headers=headers, expected=expected).json()

    def fetch_campaign_maps(self):
        payload = self.get_json(f"{LIVE_BASE_URL}/api/campaign/official?offset=0&length=100")
        campaigns = payload.get("campaignList", [])
        map_campaigns = {}

        for campaign in campaigns:
            campaign_name = strip_mania_codes(campaign.get("name", "Official campaign"))
            for item in campaign.get("playlist", []):
                map_uid = item.get("mapUid")
                if map_uid:
                    map_campaigns[map_uid] = campaign_name

        print(f"loaded {len(campaigns)} official campaigns")
        return map_campaigns

    def fetch_totd_maps(self):
        first_month = dt.date(2020, 7, 1)
        today = utc_now().date()
        month_count = (today.year - first_month.year) * 12 + (today.month - first_month.month) + 1
        map_campaigns = {}

        for offset in range(month_count):
            url = f"{LIVE_BASE_URL}/api/token/campaign/month?{urlencode({'length': 1, 'offset': offset, 'royal': 'false'})}"
            try:
                payload = self.get_json(url)
            except Exception as exc:
                self.warnings.add(f"TOTD month offset {offset} failed: {exc}")
                continue

            month_list = payload.get("monthList", [])
            if not month_list:
                continue

            month = month_list[0]
            campaign_name = f"TOTD {int(month.get('year', 0)):04d}-{int(month.get('month', 0)):02d}"
            for day in month.get("days", []):
                map_uid = day.get("mapUid")
                if map_uid:
                    map_campaigns[map_uid] = campaign_name

        print(f"loaded {len(map_campaigns)} Track of the Day maps")
        return map_campaigns

    def fetch_world_record(self, map_uid):
        url = (
            f"{LIVE_BASE_URL}/api/token/leaderboard/group/Personal_Best/map/"
            f"{map_uid}/top?onlyWorld=true&length=1&offset=0"
        )
        response = self.session.get(url, headers=self.live_headers(), timeout=30)
        if response.status_code != 200:
            self.warnings.add(f"leaderboard request failed for {map_uid}: {response.status_code}")
            return None

        try:
            payload = response.json()
        except ValueError:
            self.warnings.add(f"leaderboard response was not JSON for {map_uid}")
            return None

        tops = payload.get("tops", [])
        if not tops or not tops[0].get("top"):
            return None

        top = tops[0]["top"][0]
        if not top.get("timestamp") or top.get("score") in (None, -1):
            return None
        return top

    def fetch_map_names(self, map_uids):
        names = {}
        for batch in chunked(map_uids, 100):
            url = f"{LIVE_BASE_URL}/api/token/map/get-multiple?mapUidList={','.join(batch)}"
            try:
                payload = self.get_json(url)
            except Exception as exc:
                self.warnings.add(f"map info batch failed: {exc}")
                continue

            for item in payload.get("mapList", []):
                uid = item.get("uid")
                if uid:
                    names[uid] = strip_mania_codes(item.get("name", uid))

        return names

    def fetch_player_names(self, account_ids):
        names = {}
        for batch in chunked(account_ids, 50):
            query = urlencode([("accountId[]", account_id) for account_id in batch])
            url = f"{TM_API_BASE_URL}/api/display-names?{query}"
            try:
                payload = self.get_json(url, auth="oauth")
            except Exception as exc:
                self.warnings.add(f"display name batch failed: {exc}")
                continue

            if isinstance(payload, dict):
                names.update(payload)

        return names


def collect_records(client):
    campaign_maps = client.fetch_campaign_maps()
    totd_maps = client.fetch_totd_maps()
    map_campaigns = {**campaign_maps, **totd_maps}
    map_uids = list(dict.fromkeys(uid for uid in map_campaigns if uid and uid.strip()))

    records = []
    now_timestamp = utc_now().timestamp()
    print(f"fetching world records for {len(map_uids)} maps")

    for index, uid in enumerate(map_uids, start=1):
        if index == 1 or index % 100 == 0:
            print(f"processed {index - 1}/{len(map_uids)} maps")

        top = client.fetch_world_record(uid)
        if not top:
            continue

        set_timestamp = int(top["timestamp"])
        score = int(top["score"])
        records.append({
            "mapUid": uid,
            "mapName": uid,
            "player": top.get("accountId", ""),
            "scoreMs": score,
            "date": isoformat_z(dt.datetime.fromtimestamp(set_timestamp, dt.timezone.utc)),
            "ageDays": int((now_timestamp - set_timestamp) / 86400),
            "campaign": map_campaigns.get(uid, ""),
            "link": f"https://trackmania.io/#/leaderboard/{uid}",
            "timeSec": round(score / 1000, 3),
        })

    print(f"resolving {len(records)} records")
    map_names = client.fetch_map_names(list(dict.fromkeys(record["mapUid"] for record in records)))
    player_names = client.fetch_player_names(list(dict.fromkeys(record["player"] for record in records if record["player"])))

    for record in records:
        record["mapName"] = map_names.get(record["mapUid"], record["mapUid"])
        record["player"] = player_names.get(record["player"], record["player"])

    records.sort(key=lambda record: record["ageDays"], reverse=True)
    return records


def build_recent_changes(previous_records, new_records, existing_changes):
    old_by_uid = {record.get("mapUid"): record for record in previous_records if record.get("mapUid")}
    changes = []
    now = isoformat_z(utc_now())

    for record in new_records:
        old = old_by_uid.get(record.get("mapUid"))
        if not old:
            continue
        if int(old.get("ageDays", 0)) < RELEVANT_CHANGE_DAYS:
            continue
        if int(record.get("scoreMs", 0)) >= int(old.get("scoreMs", 0)):
            continue

        change = dict(record)
        change["previousTime"] = old.get("scoreMs")
        change["previousPlayer"] = old.get("player")
        change["daysStanding"] = old.get("ageDays")
        change["improvement"] = int(old.get("scoreMs", 0)) - int(record.get("scoreMs", 0))
        change["changeDate"] = now
        changes.append(change)

    merged = changes + existing_changes
    seen = set()
    deduped = []
    for item in merged:
        key = (item.get("mapUid"), item.get("previousTime"), item.get("scoreMs"), item.get("changeDate"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda item: item.get("changeDate") or item.get("date") or "", reverse=True)
    return deduped[:100]


def main():
    parser = argparse.ArgumentParser(description="Fetch Trackmania records and write static JSON data.")
    parser.add_argument("--out", default="site/data", help="Output directory for generated JSON files.")
    parser.add_argument("--previous", default=None, help="Previous records JSON path for change detection.")
    args = parser.parse_args()

    start_time = time.monotonic()
    load_dotenv()
    warnings = FetchWarning()
    output_dir = Path(args.out)
    records_path = output_dir / "records.json"
    recent_changes_path = output_dir / "recent_changes.json"
    metadata_path = output_dir / "metadata.json"
    previous_path = Path(args.previous) if args.previous else records_path

    previous_records = read_json(previous_path, [])
    existing_changes = read_json(recent_changes_path, [])

    client = TrackmaniaClient(warnings)
    client.authenticate()
    records = collect_records(client)
    recent_changes = build_recent_changes(previous_records, records, existing_changes)

    metadata = {
        "lastUpdate": isoformat_z(utc_now()),
        "recordCount": len(records),
        "recentChangeCount": len(recent_changes),
        "warningCount": len(warnings.messages),
        "warnings": warnings.messages[:25],
        "durationSeconds": round(time.monotonic() - start_time, 2),
        "generatedBy": "scripts/fetch_records.py",
    }

    write_json(records_path, records)
    write_json(recent_changes_path, recent_changes)
    write_json(metadata_path, metadata)

    print(f"wrote {len(records)} records to {records_path}")
    print(f"wrote {len(recent_changes)} recent changes to {recent_changes_path}")


if __name__ == "__main__":
    main()
