import argparse, os, re, sys

import requests

from dotenv import load_dotenv

load_dotenv()

FDA_BASE_URL = "https://api.fda.gov/drug/"

def query_fda(dataset, **query_params):
    fda_key = os.getenv("FDA_API_KEY")
    if fda_key:
        query_params["api_key"] = fda_key
   
    try:
        reply = requests.get(
            f"{FDA_BASE_URL}{dataset}",
            params=query_params,
            timeout=10,
        )   

        if reply.status_code == 404:
            return[]
        if reply.status_code == 429:
            sys.exit("Rate limited. Wait a minute and retry again.")

        reply.raise_for_status()
        return reply.json()["results"]
    except requests.Timeout:
        sys.exit("Request timed out. API may be slow.")
    except requests.ConnectionError:
        sys.exit("Can not reach FDA API. Check your internet connection.")
    except (requests.RequestException, ValueError, KeyError) as problem:
        sys.exit(f"API error: {problem}")

cli = argparse.ArgumentParser(
    description="Medsafe: FDA recall and side-effects lookup"
)
cli.add_argument("drug", help="generic drug name, e.g. paracetamol")
cli.add_argument(
    "--class",
    dest="recall_class",
    choices=["I","II","III"],
    help="filter by recall class",
)                   
cli.add_argument("--sort", choices=["date", "class"], default="date")
cli.add_argument("--search", help="keyword to find in the recall reason")
cli.add_argument("--limit", type=int, default=20)

options = cli.parse_args()

drug_name = re.sub(r"[^\w\s-]", "", options.drug).strip()
if not drug_name:
    sys.exit("Please input a valid drug name.")

recalls = query_fda(
    "enforcement.json",
    limit=min(options.limit, 100),
    search=f'openfda.generic_name:"{drug_name}" OR product_description:"{drug_name}"',
)



if options.recall_class:
    wanted_class = f"Class {options.recall_class}"
    recalls = [recall for recall in recalls if recall.get("classification") == wanted_class]

if options.search:
    search_word = options.search.casefold()
    recalls = [
        recall for recall in recalls
        if search_word in recall.get("reason_for_recall", "").casefold()
    ]


recalls.sort(
    key=lambda recall: (
        recall.get("report_date", "")
        if options.sort == "date"
        else recall.get("classification", "")
    ),
    reverse=(options.sort == "date")
)

print(f"\nRECALLS for '{drug_name}':{len(recalls)} found")
print(f"{'DATE':<10} {'CLASS':<10} {'COMPANY':<25} REASON")

for recall in recalls:
    date = recall.get("report_date", "")
    classification = recall.get("classification", "")
    company = recall.get("recalling_firm", "")[:24]
    reason = recall.get("reason_for_recall", "")[:60]

    print(f"{date:<10} {classification:<10} {company:<25} {reason}")

reactions = query_fda(
    "event.json",
    search=f'patient.drug.openfda.generic_name:"{drug_name}"',
    count="patient.reaction.reactionmeddrapt.exact",
)[:10]    



print(f"\nTOP REPORTED REACTIONS for '{drug_name}'")
for reaction in reactions:
    print(f"{reaction['term']:<35} {reaction['count']}")

if not recalls and not reactions:
    print("No Data found. Try the generic name (e.g 'acetaminophen').")  