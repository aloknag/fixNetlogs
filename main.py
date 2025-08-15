import json
import argparse
import os
import re
from json.decoder import JSONDecodeError


def complete_json_structure(incomplete_text, open_char, close_char, missing_count):
    """
    Complete an incomplete JSON structure by adding missing closing brackets/braces
    and handling incomplete strings and objects.
    """
    text = incomplete_text.rstrip()
    
    # If the text ends with an incomplete string, try to close it
    if text.count('"') % 2 == 1:  # Odd number of quotes means unterminated string
        # Find the last quote and check if it's escaped
        last_quote_pos = text.rfind('"')
        if last_quote_pos > 0 and text[last_quote_pos - 1] != '\\':
            text += '"'
            print("⚠️  Completed unterminated string")
    
    # If the text ends with a comma and incomplete structure, try to remove trailing comma
    text = text.rstrip(' \t\n\r,')
    
    # Add missing closing brackets/braces
    text += close_char * missing_count
    
    return text


def complete_incomplete_event(event_text):
    """
    Try to complete an incomplete JSON event by filling in missing fields and brackets.
    """
    event_text = event_text.strip().rstrip(',').strip()
    
    # Count unmatched braces
    open_braces = event_text.count('{')
    close_braces = event_text.count('}')
    missing_braces = open_braces - close_braces
    
    # If the event text is not empty and has unmatched braces
    if event_text and (missing_braces > 0 or event_text.count('"') % 2 == 1):
        # Check if we have an unterminated string
        quote_count = event_text.count('"')
        if quote_count % 2 == 1:  # Unterminated string
            event_text += '"'
        
        # Add missing closing braces
        if missing_braces > 0:
            event_text += '}' * missing_braces
        
        # Fix key with no value, e.g. "foo": } -> "foo": null }
        event_text = re.sub(r'":\s*([,}])', r'": null\1', event_text)

        try:
            # Try to parse the completed event
            event = json.loads(event_text)
            
            # Validate that it has the basic structure of a netlog event
            if isinstance(event, dict):
                # Add missing required fields if they don't exist
                if 'time' not in event:
                    event['time'] = "0"
                if 'type' not in event:
                    event['type'] = 0
                if 'phase' not in event:
                    event['phase'] = 0
                if 'source' not in event:
                    event['source'] = {"id": 0, "type": 0, "start_time": "0"}
                    
                return event
        except json.JSONDecodeError:
            pass
    
    return None


def extract_json_section(text, key):
    """
    Extract the JSON object or array associated with a given key.
    Example: extract 'events': [ ... ]
    """
    match = re.search(rf'"{key}"\s*:\s*([\[\{{])', text)
    if not match:
        return None, None

    start_char = match.group(1)
    close_char = '}' if start_char == '{' else ']'
    start = match.end(1) - 1
    end = start
    open_count = 1

    while end < len(text) - 1:
        end += 1
        char = text[end]
        if char == start_char:
            open_count += 1
        elif char == close_char:
            open_count -= 1
            if open_count == 0:
                return text[start:end + 1], (match.start(), end + 1)

    # If we reach here, the section is incomplete
    # Complete it by adding missing closing brackets/braces
    incomplete_section = text[start:end + 1]
    completed_section = complete_json_structure(incomplete_section, start_char, close_char, open_count)
    print(f"⚠️  Warning: Incomplete {key} section detected - added {open_count} missing '{close_char}'")
    return completed_section, (match.start(), len(completed_section))


def parse_events_array_robust(events_text):
    """
    Robustly parse the events array using raw_decode, and try to complete the final event if truncated.
    """
    events = []
    decoder = json.JSONDecoder()

    # Clean up the events text by removing the outer brackets
    if events_text.startswith('['):
        events_text = events_text[1:]
    if events_text.endswith(']'):
        events_text = events_text[:-1]
    
    events_text = events_text.strip()
    
    pos = 0
    while pos < len(events_text):
        # Skip over leading commas and whitespace from the previous iteration
        new_pos = pos
        for i in range(pos, len(events_text)):
            if events_text[i] in ' \t\n\r,':
                new_pos += 1
            else:
                break
        pos = new_pos
        if pos >= len(events_text):
            break

        try:
            # Use raw_decode to parse one object from the current position
            obj, pos = decoder.raw_decode(events_text, pos)
            events.append(obj)
        except json.JSONDecodeError:
            # The rest of the string is the broken part
            broken_part = events_text[pos:]
            print(f"⚠️  Incomplete event found. Attempting to recover...")
            
            completed_event = complete_incomplete_event(broken_part)
            if completed_event:
                events.append(completed_event)
                print(f"✅  Successfully recovered and completed the final event.")
            else:
                print(f"❌  Could not recover the final event. Discarding.")
            
            # Stop processing after the first error, as we've handled the remainder
            break
            
    return events


def fix_netlog(input_path, output_path):
    with open(input_path, 'r') as f:
        raw = f.read()

    # Try to complete the entire JSON file first
    completed_json = complete_entire_json_file(raw)
    
    # Try to parse the completed JSON
    try:
        netlog_data = json.loads(completed_json)
        print("✅ Successfully parsed completed JSON")
        
        # Ensure we have the basic structure
        if 'constants' not in netlog_data:
            netlog_data['constants'] = {}
        if 'events' not in netlog_data:
            netlog_data['events'] = []
            
    except json.JSONDecodeError:
        print("⚠️  Fallback to section-by-section recovery")
        # Fallback to the original approach
        constants_str, _ = extract_json_section(raw, "constants")
        events_str, _ = extract_json_section(raw, "events")

        if not constants_str or not events_str:
            print("❌ Could not locate 'constants' or 'events' in the file.")
            return

        try:
            constants = json.loads(constants_str)
        except json.JSONDecodeError:
            print("⚠️ 'constants' block is malformed. Using empty dict.")
            constants = {}

        events = parse_events_array_robust(events_str)
        
        netlog_data = {
            "constants": constants,
            "events": events
        }

    with open(output_path, 'w') as f:
        json.dump(netlog_data, f, indent=2)

    event_count = len(netlog_data.get('events', []))
    print(f"✅ Fixed NetLog saved to: {output_path}")
    print(f"✔️  Recovered {event_count} event(s).")


def complete_entire_json_file(raw_content):
    """
    Try to complete the entire JSON file by adding missing brackets, braces, and fields.
    """
    content = raw_content.strip()
    
    # Check if content starts with opening brace
    if not content.startswith('{'):
        content = '{' + content
    
    # Count unmatched braces and brackets
    open_braces = content.count('{')
    close_braces = content.count('}')
    open_brackets = content.count('[')
    close_brackets = content.count(']')
    
    # Handle unterminated strings
    quote_count = content.count('"')
    if quote_count % 2 == 1:
        # Find the last unescaped quote
        last_quote_pos = content.rfind('"')
        if last_quote_pos > 0 and content[last_quote_pos - 1] != '\\':
            content += '"'
            print("⚠️  Completed unterminated string in file")
    
    # Remove trailing commas before adding closing brackets
    content = re.sub(r',(\s*)$', r'\1', content)
    
    # Add missing closing brackets for arrays
    missing_brackets = open_brackets - close_brackets
    if missing_brackets > 0:
        content += ']' * missing_brackets
        print(f"⚠️  Added {missing_brackets} missing closing bracket(s)")
    
    # Add missing closing braces for objects
    missing_braces = open_braces - close_braces
    if missing_braces > 0:
        content += '}' * missing_braces
        print(f"⚠️  Added {missing_braces} missing closing brace(s)")
    
    return content


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
