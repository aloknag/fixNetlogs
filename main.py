import json
import argparse
import os
import re
from json.decoder import JSONDecodeError


def extract_json_section(text, key):
    """
    Extract the JSON object or array associated with a given key.
    Example: extract 'events': [ ... ]
    """
    match = re.search(rf'"{key}"\s*:\s*([\[\{{])', text)
    if not match:
        return None, None

    start_char = match.group(1)
    start = match.end(1) - 1
    end = start
    open_count = 1

    while end < len(text) - 1:
        end += 1
        char = text[end]
        if char == start_char:
            open_count += 1
        elif (start_char == '{' and char == '}') or (start_char == '[' and char == ']'):
            open_count -= 1
            if open_count == 0:
                return text[start:end + 1], (match.start(), end + 1)

    return None, None  # Incomplete section


def parse_events_array(events_text):
    """
    Parse the events array manually, stopping at the first malformed entry.
    """
    events = []
    decoder = json.JSONDecoder()
    idx = 0

    while idx < len(events_text):
        try:
            event, next_idx = decoder.raw_decode(events_text[idx:])
            events.append(event)
            idx += next_idx
            while idx < len(events_text) and events_text[idx] in ", \r\n\t":
                idx += 1
        except JSONDecodeError:
            break  # Stop at the first malformed entry

    return events


def fix_netlog(input_path, output_path):
    with open(input_path, 'r') as f:
        raw = f.read()

    constants_str, _ = extract_json_section(raw, "constants")
    events_str, _ = extract_json_section(raw, "events")

    if not constants_str or not events_str:
        print("❌ Could not locate 'constants' or 'events' in the file.")
        return

    try:
        constants = json.loads(constants_str)
    except JSONDecodeError:
        print("⚠️ 'constants' block is malformed. Using empty dict.")
        constants = {}

    events = parse_events_array(events_str)

    cleaned = {
        "constants": constants,
        "events": events
    }

    with open(output_path, 'w') as f:
        json.dump(cleaned, f, indent=2)

    print(f"✅ Fixed NetLog saved to: {output_path}")
    print(f"✔️  Recovered {len(events)} event(s).")


def main():
    parser = argparse.ArgumentParser(
        description="Fix incomplete Chromium NetLog JSON files."
    )
    parser.add_argument(
        "filename",
        help="Path to the incomplete NetLog file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Optional output file name (.json)"
    )
    args = parser.parse_args()

    input_file = args.filename
    if not os.path.isfile(input_file):
        print(f"❌ File not found: {input_file}")
        return

    base_name = os.path.splitext(input_file)[0]
    output_file = args.output or (base_name + ".json")

    fix_netlog(input_file, output_file)


if __name__ == "__main__":
    main()
