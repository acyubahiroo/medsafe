import argparse
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.fda.gov/drug/"

def fetch(endpoint, **params):
    api_key = os.getenv("FDA_API_KEY")
    if api_key:
        params["api_key"] = api_key

    try:
        response = requests.get(
            f"{BASE}{endpoint}",
            params=params,
            timeout=10,
        )

        if response.status_code == 404:
            return[]
        if response.status_code == 429:
            sys.exit("Rate limited. Wait a minute and retry again.")

        response.raise_for_status()
        return response.json()["results"] 
    except requests.Timeout:
        sys.exit("Request timed out. API may be slow")
    except requests.ConnectionError:
        sys.exit("Can not reach FDA API. Check your internet connection.")
    except (requests.RequestException, ValueError, KeyError) as error:
        sys.exit(f"API error: {error}")


#This is a section for creating a parser to pass all the arguments

parser = argparse.ArgumentParser(
    description="Medsafe: FDA and side-effects and after-symptoms lookup"
)
parser.add_argument("drug", help="generic drug name, e.g. paracetamol")
parser.add_argument(
    "--class",
    dest="cls",
    choices=["I","II","III"],
    help="filter by recall class",
)                   
parser.add_argument("--sort", choices=["date", "class"], default="date")
parser.add_argument("--search", help="keyword to find in the recall reason")
parser.add_argument("--limit", type=int, default=20)

a = parser.parse_args()

d = re.sub(r"[^\w\s-]", "", a.drug).strip()
if not d:
    sys.exit("Please input a valid drug name.")

rec = fetch(
    "enforcement.json",
    limit=min(a.limit, 100),
    search=f'openfda.generic_name:"{d}" OR product_description:"{d}"',
)

#the following section is for generating classes for searchm sorting and filtering.

if a.cls:
    target_class = f"Class {a.cls}"
    rec = [item for item in rec if item.get("classification") == target_class]

if a.search:
    keyword = a.search.casefold()
    rec = [
        item for item in rec
        if keyword in item.get("reason_for_recall", "").casefold()
    ]

rec.sort(
    key=lambda item: (
        item.get("report_date", "")
        if a.sort == "date"
        else item.get("classification", "")
    ),
    reverse=(a.sort == "date")
)

print(f"\nRECALLS for '{d}':{len(rec)} found")
print(f"{'DATE':<10} {'CLASS':<10} {'COMPANY':<25} REASON")

#this will show the company report dates as well as reasons for recall

for item in rec:
    date = item.get("report_date", "")
    classification = item.get("classification", "")
    company = item.get("recalling_firm", "")[:24]
    reason = item.get("reason_for_recall", "")[:60]

    print(f"{date:<10} {classification:<10} {company:<25} {reason}")

ev = fetch(
    "event.json",
    search=f'patient.drug.openfda.generic_name:"{d}"',
    count="patient.reaction.reactionmeddrapt.exact",
)[:10]

#this section is for reactions of the medecine

print(f"\nTOP REPORTED REACTIONS for '{d}'")
for event in ev:
    print(f"{event['term']:<35} {event['count']}")

if not rec and not ev:
    print("No data found. Try the generic name (e.g 'acetaminophen').")    