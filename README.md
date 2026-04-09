<p align="center">
  <img src="https://raw.githubusercontent.com/atenreiro/opensquat/master/screenshots/openSquat_logo.png" alt="openSquat Logo" width="400"/>
</p>

<h1 align="center">openSquat Core</h1>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://github.com/atenreiro/opensquat/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
  <a href="https://github.com/atenreiro/opensquat/issues"><img src="https://img.shields.io/github/issues/atenreiro/opensquat" alt="GitHub issues"></a>
  <a href="https://github.com/atenreiro/opensquat/stargazers"><img src="https://img.shields.io/github/stars/atenreiro/opensquat" alt="GitHub stars"></a>
</p>

---

## 📑 Table of Contents

- [What is openSquat?](#-what-is-opensquat)
- [Open-Core Model](#-open-core-model)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Requirements](#-requirements)
- [Usage](#-usage)
- [Premium and API Modes](#-premium-and-api-modes)
- [Configuration](#%EF%B8%8F-configuration)
- [Automation](#-automation)
- [CLI Reference](#-cli-reference)
- [Contributing](#-contributing)
- [Author](#-author)
- [License](#-license)

---

## 🎯 What is openSquat?

openSquat is an **Open Source Intelligence (OSINT)** security tool that identifies cyber squatting threats targeting your brand or domains:

| Threat Type | Description |
|-------------|-------------|
| 🎣 **Phishing** | Fraudulent domains mimicking your brand |
| 🔤 **Typosquatting** | Domains with common typos (e.g., `gooogle.com`) |
| 🌐 **IDN Homograph** | Look-alike characters from other alphabets |
| 👥 **Doppelgänger** | Domains containing your brand name |
| 🔀 **Bitsquatting** | Single-bit errors in domain names |

## 🔓 Open-Core Model

openSquat follows an **open-core model**:

- **Core detection engine** — Open source and community-driven
- **Advanced capabilities** — Delivered through commercial intelligence services

This model enables transparency and community collaboration while supporting the scale, reliability, and operational requirements of enterprise use.

---

## ✨ Key Features

- 📅 **Daily NRD feeds** — Automatic newly registered domain updates
- 🔍 **Similarity detection** — Levenshtein distance algorithm
- 🛡️ **VirusTotal integration** — Check domain reputation
- 🌐 **Quad9 DNS validation** — Identify malicious domains
- 📜 **Certificate Transparency** — Monitor SSL/TLS certificates
- 📊 **Multiple output formats** — TXT, JSON, CSV

---

## 🚀 Quick Start

### Install via pip (recommended)

```bash
pip install opensquat
opensquat -k keywords.txt
```

### Or clone the repository

```bash
git clone https://github.com/atenreiro/opensquat
cd opensquat
pip install -r requirements.txt
python opensquat.py -k keywords.txt
```

---

## 📦 Requirements

- **Python 3.10+**
- Dependencies: `confusable_homoglyphs`, `homoglyphs`, `colorama`, `requests`, `dnspython`, `beautifulsoup4`

---

## 📖 Usage

### Basic Commands

```bash
# Default run
opensquat

# Show all options
opensquat -h

# Use custom keywords file
opensquat -k my_keywords.txt
```

### Validation Options

```bash
# DNS validation via Quad9
opensquat --dns

# Check Certificate Transparency logs
opensquat --ct

# Scan for open ports (80/443)
opensquat --portcheck

# Cross-reference phishing databases
opensquat --phishing results.txt
```

### Output Formats

```bash
# Save as JSON
opensquat -o results.json -t json

# Save as CSV
opensquat -o results.csv -t csv
```

### Confidence Levels

| Level | Flag | Description |
|-------|------|-------------|
| 0 | `-c 0` | Very high (fewer results, high accuracy) |
| 1 | `-c 1` | High (default) |
| 2 | `-c 2` | Medium |
| 3 | `-c 3` | Low |
| 4 | `-c 4` | Very low (more results, more false positives) |

---

## 💎 Premium and API Modes

openSquat supports three modes. The default (community) is unchanged - existing users need no flags.

| Mode | Flag | What it does |
|------|------|--------------|
| **Community** (default) | _(none)_ | Downloads the free NRD feed (~100k domains/day) and runs local Levenshtein detection. |
| **Premium** | `--premium` | Downloads the paid NRD feed (`nrd-lite`, much larger) using your openSquat API key, then runs local Levenshtein detection. |
| **API** | `--api` | Skips local feed download. Queries the openSquat lookalike REST API per keyword and returns server-side matches. |

### Get an API key

Sign up at [opensquat.com](https://opensquat.com) to get a key. The same key works for both `--premium` and `--api`.

### Provide the API key (priority order)

1. `--api-key YOUR_KEY` on the command line
2. `OPENSQUAT_API_KEY` environment variable
3. `opensquat_key.txt` in the current directory (one key per file, `#` comments allowed)

> The CLI flag is visible in `ps` output. Prefer the env var or key file in shared environments.

### Examples

```bash
# Premium feed - same local pipeline, larger feed
export OPENSQUAT_API_KEY=os_xxxxxxxxxxxx
opensquat -k keywords.txt --premium

# API mode - server-side detection per keyword
opensquat -k keywords.txt --api

# API mode + DNS reputation check on each returned domain
opensquat -k keywords.txt --api --dns

# API mode with JSON output grouped by keyword
opensquat -k keywords.txt --api -t json -o results.json

# Tune the API search
opensquat -k keywords.txt --api --api-fuzziness high --api-history-days 7 --api-max-results 200
```

In API mode, the run summary reports the active mode, the number of API calls made, and your remaining balance. Quota exhaustion (HTTP 429) returns partial results gracefully; auth errors (401) and plan errors (403) abort with a clear message.

`-c/--confidence` is auto-mapped to API fuzziness (0→exact, 1→low, 2→auto, 3→high, 4→high). Note that the API currently exposes four fuzziness levels, so `-c 3` and `-c 4` both map to `high` — if you need finer control than that, use `--api-fuzziness` to override.

`--api` is incompatible with `--doppelganger` and `-d/--domains`.

---

## ⚙️ Configuration

### Keywords File (`keywords.txt`)

```text
# Lines starting with # are comments
mycompany
mybrand
myproduct
```

### VirusTotal API Key (`vt_key.txt`)

To use `--vt` or `--subdomains`, add your API key:
```text
# Get your free API key at https://www.virustotal.com
your_api_key_here
```

---

## 🤖 Automation

Run daily via crontab:

```bash
# Every day at 8 AM (feeds update ~7:30 AM UTC)
0 8 * * * /path/to/opensquat/opensquat.py -k keywords.txt -o results.json -t json
```

---

## 📋 CLI Reference

| Argument | Default | Description |
|----------|---------|-------------|
| `-k, --keywords` | `keywords.txt` | Keywords file to search |
| `-o, --output` | `results.txt` | Output filename |
| `-t, --type` | `txt` | Output format: `txt`, `json`, `csv` |
| `-c, --confidence` | `1` | Confidence level (0-4) |
| `-d, --domains` | — | Use local domain file instead of downloading |
| `-u, --url` | opensquat feed | URL to download domain feed |
| `--dns` | — | Enable Quad9 DNS validation |
| `--doppelganger` | — | Doppelganger-only mode (keyword in domain + reachability check) |
| `--ct` | — | Search Certificate Transparency logs |
| `--phishing` | — | Cross-reference phishing database |
| `--subdomains` | — | Fetch subdomains via VirusTotal |
| `--portcheck` | — | Check for open ports 80/443 |
| `--vt` | — | Validate against VirusTotal |
| `--premium` | — | Use the paid NRD feed (requires openSquat API key) |
| `--api` | — | Query the openSquat lookalike REST API per keyword (no local feed) |
| `--api-key` | — | openSquat API key (or set `$OPENSQUAT_API_KEY`, or use `opensquat_key.txt`) |
| `--api-fuzziness` | _(from `-c`)_ | API mode: `exact`, `low`, `high`, or `auto` |
| `--api-history-days` | — | API mode: NRD history window in days (clipped to plan cap) |
| `--api-max-results` | — | API mode: max results per keyword (clipped to plan cap) |

---

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

- 🐛 **Report bugs** via [GitHub Issues](https://github.com/atenreiro/opensquat/issues)
- 💡 **Request features** by opening an issue
- 🔧 **Submit PRs** for bug fixes or enhancements

---

## 👤 Author

**Andre Tenreiro** — [LinkedIn](https://www.linkedin.com/in/andretenreiro/) · [PGP Key](https://mail-api.proton.me/pks/lookup?op=get&search=andre@opensquat.com)

---

## 📜 License

This project is licensed under the [GNU GPL v3](LICENSE).
