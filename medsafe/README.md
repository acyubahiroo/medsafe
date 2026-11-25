# MedSafe CLI

A command-line tool that checks **FDA drug recalls** and the **most commonly reported side effects** for any medicine.

## Problem it solves

Recalled or contaminated medicines are a real public-health risk, yet pharmacists, clinic staff and ordinary people have no quick way to check them. MedSafe lets you type a drug name and instantly see:

- Official FDA recalls: date, severity class, recalling company and reason
- The 10 most frequently reported adverse reactions, with report counts

## Features

- Recall lookup by generic drug name
- Filter by recall class: `--class I | II | III`
- Sort by date (newest first) or class: `--sort date | class`
- Keyword search inside recall reasons: `--search contamination`
- Limit the number of results (default 20, max 100): `--limit 50`
- Input cleaning, so special characters cannot break the query
- Error handling for timeouts, no internet, rate limits (429), no results (404) and bad responses
- API key stored in `.env`, which is never committed

## API used

**openFDA** (U.S. Food and Drug Administration), free public API.

- Drug recalls: `https://api.fda.gov/drug/enforcement.json`
- Adverse events: `https://api.fda.gov/drug/event.json`
- Documentation: https://open.fda.gov/apis/
- Get a free key: https://open.fda.gov/apis/authentication/

Data provided by openFDA. This tool is for information only and is not medical advice.

## Run locally

Requires Python 3.9+ and Git.

```bash
git clone https://github.com/acyubahiroo/medsafe.git
cd medsafe
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a file named `.env` in the project folder:

```
FDA_API_KEY=your_key_here
```

Examples:

```bash
python medsafe.py ibuprofen
python medsafe.py ibuprofen --class II --sort class
python medsafe.py metformin --search contamination
python medsafe.py ibuprofen --limit 50
python medsafe.py --help
```

## Deployment

The app is a CLI, so it is served in the browser with **ttyd** (a web terminal). It runs on two web servers (`web-01`, `web-02`) behind an **HAProxy** load balancer (`lb-01`). The servers are Docker containers, and I opened a root shell in each with `docker exec -it -u root <name> bash`.

### Web servers (repeat on web-01 and web-02)

```bash
apt update && apt install -y python3 python3-venv git wget
wget -O /usr/local/bin/ttyd https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64
chmod +x /usr/local/bin/ttyd

cd ~
git clone https://github.com/acyubahiroo/medsafe.git
cd medsafe
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "FDA_API_KEY=<your_key>" > .env
```

Launcher script `run.sh` (shows which server answered):

```bash
#!/bin/bash
cd ~/medsafe && source venv/bin/activate
echo "Server: $(hostname)"
echo "Try: python medsafe.py ibuprofen"
exec bash
```

```bash
chmod +x run.sh
nohup ttyd -W -p 80 ./run.sh > ttyd.log 2>&1 &
```

Direct access: web-01 at `http://localhost:8080`, web-02 at `http://localhost:8081`.

### Load balancer (lb-01)

```bash
apt update && apt install -y haproxy
```

Appended to `/etc/haproxy/haproxy.cfg`:

```
frontend http_in
    bind *:80
    default_backend webapps

backend webapps
    balance roundrobin
    timeout tunnel 1h
    server web01 web-01:80 check
    server web02 web-02:80 check
```

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
service haproxy restart
```

`balance roundrobin` alternates requests between servers, `check` removes a dead server automatically, and `timeout tunnel 1h` keeps the terminal websocket from closing.

### Testing

1. Open the load balancer at `http://localhost:8082` in several incognito windows. The `Server:` line alternates between `web-01` and `web-02`.
2. Run `python medsafe.py ibuprofen` through the load balancer on both servers.
3. Failover: stop ttyd on one server (`pkill ttyd`). The load balancer keeps serving through the other one.

## Links

- **Demo video (under 2 min):** <<paste YouTube link>>
- **Load balancer URL:** <<http://localhost:8082>>
- **Login details / API key:** provided in the Canvas submission comment

## Challenges and how I solved them

| Challenge | Solution |
|---|---|
| PowerShell blocked virtual environment activation | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| App rejected every drug name | A regex typo (`\W` instead of `\w`) deleted all letters; fixed the character class |
| `--class` returned nothing | The API uses `Class II` with a space; fixed the comparison string |
| API returns 404 when nothing matches | Treated 404 as an empty result instead of an error |
| SSH key would not authenticate | The private key was created inside a container; generated a new RSA pair on my laptop and registered the public key |
| `sudo` asked for an unknown password | Used `docker exec -u root` for a root shell |
| `git push` failed with a 400 error | A placeholder (`<username>`) was left in the remote URL; replaced it with the real one |
| Repo cloned as `medsafe/medsafe` | Moved files to the repo root and re-cloned from the home folder |
| Blank terminal on one server | ttyd was still pointing at a deleted folder; restarted it from the new `~/medsafe` |
| API key visible in a screenshot | Requested a new key and cropped keys out of screenshots |

## NB: About the CodeVibe report

- **AI assistance:** I was given permission to use AI assistance on this assignment but with a threshold and limit.h
- **Extension crashes:** The CodeVibe extension crashed repeatedly while I was working, and I had to restart it several times.
- **Inconsistent metrics:** I got different metrics each time I checked. The numbers in the generated report did not match what I saw on the CodeVibe dashboard.
- **Classification:** Code that I typed and edited myself was often still classified as AI-authored, even though the ownership score showed 100%.
- **Tracking gap:** The extension was activated on 25 November, so the report shows a tracking gap for the days before that.

I kept the original exported reports in `codevibe-reports/` unedited. I can walk through the code and explain how every part works in person.

## Credits

- [openFDA](https://open.fda.gov/) for the drug recall and adverse-event data
- [ttyd](https://github.com/tsl0922/ttyd) for the web terminal
- [HAProxy](https://www.haproxy.org/) for load balancing
- Python libraries: [requests](https://requests.readthedocs.io/) and [python-dotenv](https://github.com/theskumar/python-dotenv)
