# 🛠 NetLog JSON Fixer

**NetLog JSON Fixer** is a Python script that automatically repairs **incomplete or corrupted Chromium NetLog files**.
These `.json` files are often used to diagnose network activity in Chrome, but they can become **truncated** during crashes, power loss, or incomplete writes.

This tool extracts and salvages valid parts of the NetLog, especially focusing on recovering as many `"events"` as possible.

---

## 📌 Features

* ✅ Supports malformed/truncated NetLog files
* ✅ Salvages all valid `events` from partially written JSON
* ✅ Ignores broken/trailing entries gracefully
* ✅ Keeps `"constants"` block if valid
* ✅ Fully CLI-driven using `argparse`
* ✅ PEP8 compliant, all lines < 120 characters
* ✅ Zero dependencies (pure Python)

---

## 🔍 What is a Chromium NetLog?

[NetLog](https://www.chromium.org/developers/design-documents/network-stack/netlog/) is a logging system in Chromium-based browsers
that tracks low-level network events (e.g., socket creation, DNS lookups, URL requests). The output is a large structured JSON file.

A valid NetLog looks like this:

```json
{
  "constants": {
    "logFormatVersion": 1,
    "clientInfo": {
      "name": "Chrome",
      "version": "123.0"
    }
  },
  "events": [
    { "type": "SOCKET", "params": { "source_id": 1 } },
    { "type": "URL_REQUEST", "params": { "url": "https://example.com" } }
  ]
}
```

If truncated, it may look like:

```json
{
  "constants": { ... },
  "events": [
    { "type": "SOCKET", "params": { ... } },
    { "type": "URL_REQUEST"
```

---

## 🚀 Installation

No installation required. Just download the script:

```bash
curl -O https://your-repo-url/fix_netlog.py
```

Or clone the project:

```bash
git clone https://github.com/your-username/netlog-json-fixer.git
cd netlog-json-fixer
```

Ensure Python 3 is installed:

```bash
python3 --version
```

---

## ✅ Usage

```bash
python3 fix_netlog.py <input_file> [-o <output_file.json>]
```

### Arguments

| Argument         | Description                                              |
| ---------------- | -------------------------------------------------------- |
| `<input_file>`   | Path to the incomplete NetLog file                       |
| `-o`, `--output` | (Optional) Output file name (defaults to `<input>.json`) |

### Examples

```bash
# Fix and overwrite original file with .json extension
python3 fix_netlog.py netlog_partial

# Fix and write to custom output file
python3 fix_netlog.py netlog_partial -o fixed_output.json
```

---

## ⚙️ How It Works

1. Reads the raw input file as a string
2. Uses regex to locate and extract the `"constants"` and `"events"` sections
3. Parses `"constants"` if it's a valid JSON object
4. Parses `"events"` manually:

   * Reads one JSON object at a time
   * Stops on the first broken object
   * Silently drops any remaining malformed data
5. Reassembles and saves a valid JSON file

---

## 🧪 Output Example

```json
{
  "constants": {
    "logFormatVersion": 1,
    "clientInfo": { "name": "Chrome", "version": "123.0" }
  },
  "events": [
    { "type": "SOCKET", "params": { "source_id": 1 }, "time": 123456789 },
    { "type": "DNS_LOOKUP", "params": { "hostname": "example.com" } }
  ]
}
```

---

## 🧺 Edge Case Handling

| Case                               | Behavior                 |
| ---------------------------------- | ------------------------ |
| Missing `"constants"`              | Replaces with `{}`       |
| Broken last event in `"events"`    | Silently skipped         |
| Non-JSON garbage after valid block | Ignored                  |
| Completely unparseable input       | Error message, no output |

---

## 🛡️ Best Practices

* Use this tool **only** on Chromium NetLog files
* Run through `jq` or an online JSON validator to visually inspect fixed output
* Always keep the original raw file for forensic/backup purposes

---

## 🧰 Troubleshooting

**Q: I'm getting `Could not locate 'constants' or 'events' in the file.`**
A: Ensure the file is a valid (even if partial) Chromium NetLog and hasn't been heavily modified.

**Q: It only recovers 0 events!**
A: The log may be corrupted early in the `"events"` section. Consider running a full NetLog capture again.

---

## 🪪 License

This project is licensed under the [MIT License](LICENSE)

---


## 📁 Related Tools

* [NetLog Viewer](https://netlog-viewer.appspot.com/) — Official visualizer for Chromium NetLogs
* [jq](https://stedolan.github.io/jq/) — JSON command-line processor

---

