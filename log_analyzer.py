import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher

EXEC_UTIL_FUNCS = {
    'strptime': lambda date_str, fmt="%Y-%m-%d %H:%M:%S,%f": datetime.strptime(date_str, fmt).timestamp() * 1000
}
BUILTINS = __builtins__
CONCURRENT_THREAD_COUNT = 20

GROUPED_KEY = "_grouped"
LINE_KEY = "_line"
CLUSTER_RATIO_KEY = "_cluster_ratio"

ANSI_COLORS = [
    "\033[36m",  # cyan
    "\033[33m",  # yellow
    "\033[35m",  # magenta
    "\033[32m",  # green
    "\033[34m",  # blue
    "\033[31m"  # red
]
RESET = "\033[0m"

documentation = r"""
Log Analyzer Tool - Command Line Documentation

This tool allows advanced log processing and manipulation using various commands. Below is an overview of the available functionality with examples.

Commands:
---------

1. match <regex>
   - Filters logs that match the given regular expression.
   - Example:
     cat server.log | lgx match "Access"

2. rex <regex>
   - Extracts fields from log lines using a named-group regular expression and appends these fields as JSON.
   - Example:
     cat server.log | lgx rex "(?P<url>[A-Z]+ \S+)"
   - Extract fields from specific input data:
     cat server.log | lgx rex "(?P<method>[A-Z]+)" --input_field=request

3. where <expression>
   - Filters logs based on the provided Python expression.
   - Example:
     cat server.log | lgx where "'GET' in url"
   - Filter logs by numerical comparison:
     cat server.log | lgx where "response_time > 200"

4. group <fields>
   - Groups logs by the specified keys, storing all grouped logs under a _grouped key.
   - Example:
     cat server.log | lgx rex "(?P<rid>\d+)" | lgx group rid

5. eval <expression>
   - Executes a Python statement on each log line's JSON representation. Updates the log data accordingly.
   - Example:
     cat grouped.log | lgx eval "total_errors = len(_grouped)"
   - Add a new field calculation:
     cat logs.json | lgx eval "status_code_group = status_code // 100"

6. geval <expression>
   - Like eval, but works on grouped data 
   - Example:
     cat grouped.log | lgx geval "duration = max(rid) - min(rid)"

7. sort <options>
   - Sorts logs by specified fields. Use + for ascending (default) and - for descending sorting.
   - Example:
     cat logs.json | lgx sort -duration
   - Sort by multiple fields:
     cat grouped.log | lgx sort -duration +status_code

8. reverse
   - Reverses the order of logs.
   - Example:
     cat sorted.log | lgx reverse

9. count
   - Outputs the total count of log entries.
   - Example:
     cat server.log | lgx count

10. show <fields>
    - Displays only the specified fields from each log.
    - Example:
      cat server.log | lgx show rid duration
    - Display specific fields with missing values as None:
      cat server.log | lgx show url response_time

11. table
    - Outputs logs in a human-readable table format.
    - Example:
      cat server.log | lgx table

12. json
    - Outputs the log data as a single JSON array.
    - Example:
      cat server.log | lgx json

13. lookup <field> <lookup_data> [join_type]
    - Joins log data with lookup data based on a common field.
    - Join types: left (default), right, inner, outer
    - Example:
      cat logs.json | lgx lookup user_id '[{"user_id": 123, "name": "John"}]'

14. graph <x_fields> <y_fields> [width]
    - Creates an ASCII bar graph visualization of the data.
    - Example:
      cat stats.json | lgx graph timestamp,service response_time 80

15. cluster <field> [-t=threshold]
    - Group similar logs based on the similarity of the specified field.
    - Example:
      cat logs.json | lgx cluster message -t=0.8

16. resolve_multiline <regex>
    - Resolves multiline log entries based on a starting line pattern.
    - Example:
      cat app.log | lgx resolve_multiline "^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]"

17. gen <expression>
    - Generates data from Python expression and outputs as JSON lines.
    - Example:
      lgx gen "[{'id':i, 'value':i*2} for i in range(5)]"

Examples:
---------

Example Workflow:
-----------------
1. Extract request IDs and group logs:
   cat server.log | lgx rex "(?P<rid>\d+)" | lgx group rid

2. Calculate duration for each group:
   cat grouped.log | lgx geval "duration = max(rid) - min(rid)"

3. Sort the grouped logs by the calculated duration in descending order:
   cat grouped.log | lgx sort -duration

4. Join with user data and create a table:
   cat logs.json | lgx lookup user_id '[{"user_id": 123, "name": "John"}]' | lgx table

5. Visualize response times per service:
   cat stats.json | lgx graph service response_time 80

6. Extract data while resolving multiline logs:
   cat raw.log | lgx resolve_multiline "^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]" | lgx rex "(?P<level>[A-Z]+)" | lgx show level message

7. Cluster log messages for similarity detection:
   cat logs.json | lgx cluster message -t=0.75 | lgx table

8. Generate test data:
   lgx gen "[{'id':i} for i in range(10)]"

"""


# region : utils
def match_line_with_regex(line, regex):
    return re.search(regex, line) is not None


def input_lines(strip=True):
    while True:
        try:
            if strip:
                yield input().strip()
            else:
                yield input()
        except EOFError:
            return


def regex_extract(line, regex):
    match = re.search(regex, line)
    if match:
        groups = match.groupdict() if match.groupdict() else {i: g for i, g in enumerate(match.groups(), start=1)}
        return groups
    return {}


def out_write(line):
    try:
        sys.stdout.write(line + "\n")
    except OSError:
        raise InterruptedError


def err_write(line):
    try:
        sys.stderr.write(line + "\n")
    except OSError:
        raise InterruptedError


class DefaultDict(dict):

    def __init__(self, original_dict, grouped=False):
        self.original_dict = original_dict
        self.grouped = grouped
        if grouped:
            self.keys_in_grouped_lines = set()
            for line in original_dict.get(GROUPED_KEY, []):
                self.keys_in_grouped_lines.update(line.keys())
        super().__init__(original_dict)

    def __setitem__(self, __key, __value):
        self.original_dict[__key] = __value
        super().__setitem__(__key, __value)

    def __missing__(self, key):
        if isinstance(BUILTINS, dict):
            if key in BUILTINS:
                return BUILTINS[key]
        else:
            if key in dir(__builtins__):
                return getattr(__builtins__, key)
        if key in EXEC_UTIL_FUNCS:
            return EXEC_UTIL_FUNCS[key]
        if self.grouped and key in self.keys_in_grouped_lines:
            return [line[key] for line in self.original_dict.get(GROUPED_KEY, [])]
        return None


def safe_exec(expr: str, context, grouped=False):
    return exec(expr, DefaultDict(context, grouped))


def safe_eval(expr: str, context):
    return eval(expr, DefaultDict(context))


def join_dict_lists(
        left, right, on, join_type='inner'
):
    from collections import defaultdict

    right_lookup = defaultdict(list)
    for r in right:
        right_lookup[r.get(on)].append(r)

    results = []

    used_left = set()
    used_right = set()

    for lidx, l in enumerate(left):
        key = l.get(on)
        matches = right_lookup.get(key, [])
        if matches:
            for ridx, r in enumerate(matches):
                res = {**l, **r}
                results.append(res)
                used_left.add(lidx)
                used_right.add((key, ridx))
        elif join_type in ('left', 'outer'):
            results.append({**l})

    if join_type in ('right', 'outer'):
        for ridx, r in enumerate(right):
            key = r.get(on)
            matched = any(
                (key == l.get(on))
                for l in left
            )
            if not matched:
                results.append({**r})

    return results


class NullSafeDict(dict):
    def __missing__(self, key):
        return None


# endregion

# region : cmd
def cmd_rex(regex, input_field=None):
    for line in input_lines():
        try:
            if input_field is not None:
                data = json.loads(line)
                extracted_fields = regex_extract(extracted_fields[input_field], regex)
                data.update(extracted_fields)
                out_write(json.dumps(data))
            else:
                extracted_fields = regex_extract(line, regex)
                extracted_fields[LINE_KEY] = line
                out_write(json.dumps(extracted_fields))
        except (InterruptedError, KeyboardInterrupt) as e:
            raise e
        except Exception as e:
            err_write("Error while processing rex\n" + line + "\n" + str(e))
            exit(1)


def cmd_match(regex):
    for line in input_lines():
        if match_line_with_regex(line, regex):
            out_write(line)


def cmd_where(expr):
    for line in input_lines():
        try:
            if safe_eval(expr, json.loads(line)):
                out_write(line)
        except (InterruptedError, KeyboardInterrupt) as e:
            raise e
        except Exception as e:
            err_write("Error while processing where\n" + line + "\n" + str(e))
            exit(1)


def cmd_eval(expr):
    for line in input_lines():
        try:
            data = json.loads(line)
            safe_exec(expr, data)
            out_write(json.dumps(data))
        except (InterruptedError, KeyboardInterrupt) as e:
            raise e
        except Exception as e:
            err_write("Error while processing eval\n" + line + "\n" + str(e))
            exit(1)


def cmd_sort(sort_option_exprs):
    lines = [NullSafeDict(json.loads(line)) for line in input_lines()]
    sort_options = []
    for expr in sort_option_exprs:
        flag = expr[0]
        if flag == "-":
            reverse = True
            expr = expr[1:]
        elif flag == "+":
            reverse = False
            expr = expr[1:]
        else:
            reverse = False
        sort_options.append((expr, reverse))

    def sort_key(line_data):
        key = []
        for sort_option in sort_options:
            field_name, reverse = sort_option
            if reverse:
                if isinstance(line_data.get(field_name), (int, float)):
                    key.append(-line_data.get(field_name))
                else:
                    err_write("negative sort key for non-numeric value not supported: " + field_name + "")
                    exit(1)
            else:
                key.append(line_data.get(field_name))
        return tuple(key)

    lines.sort(key=sort_key)

    for line in lines:
        out_write(json.dumps(line))

def cmd_group_eval(expr):
    for line in input_lines():
        try:
            data = json.loads(line)
            safe_exec(expr, data, True)
            out_write(json.dumps(data))
        except InterruptedError as e:
            raise e
        except Exception as e:
            err_write("Error while processing eval\n" + line + "\n" + str(e))
            exit(1)


def cmd_reverse():
    lines = [line for line in input_lines()]

    lines.reverse()

    for line in lines:
        out_write(line)


def cmd_help():
    out_write(documentation)


def cmd_table():
    data = [NullSafeDict(json.loads(line)) for line in input_lines()]
    if not data:
        return

    headers = list(data[0].keys())

    col_widths = [max(len(str(row.get(key, ''))) for row in data) for key in headers]
    col_widths = [max(len(header), width) for header, width in zip(headers, col_widths)]

    header_row = " | ".join(header.ljust(width) for header, width in zip(headers, col_widths))
    print(header_row)
    print("-" * len(header_row))

    for row in data:
        row_str = " | ".join(str(row[key]).ljust(width) for key, width in zip(headers, col_widths))
        print(row_str)


def cmd_json():
    print(json.dumps([json.loads(line) for line in input_lines()]))


def cmd_lookup(field, lookup_data, join_type="left"):
    if not field:
        err_write("No lookup field specified")
        exit(1)
    try:
        right_data = json.loads(lookup_data)
        if not right_data:
            err_write("Empty lookup data")
            exit(1)
    except json.JSONDecodeError:
        err_write("Invalid lookup data format")
        exit(1)

    if join_type == "right" or join_type == "outer":
        left_data = [json.loads(line) for line in input_lines()]
        joined_data = join_dict_lists(left_data, right_data, field, join_type)
        for line in joined_data:
            out_write(json.dumps(line))
    else:
        right_lookup = defaultdict(list)
        for r in right_data:
            right_lookup[r.get(field)].append(r)

        for lidx, l in enumerate(input_lines()):
            l = json.loads(l)
            key = l.get(field)
            matches = right_lookup.get(key, [])
            if matches:
                for ridx, r in enumerate(matches):
                    res = {**l, **r}
                    out_write(json.dumps(res))
            elif join_type == 'left':
                out_write(json.dumps(l))


def cmd_group(group_keys):
    if not group_keys:
        err_write("No group keys specified")
        exit(1)
    grouped = defaultdict(list)
    for line in input_lines():
        line_data = NullSafeDict(json.loads(line))
        key = tuple(line_data[k] for k in group_keys)
        # Extract the rest of the fields
        remainder = {k: v for k, v in line_data.items() if k not in group_keys}
        grouped[key].append(remainder)

    result = []
    for key, group_items in grouped.items():
        grouped_entry = dict(zip(group_keys, key))
        grouped_entry[GROUPED_KEY] = group_items
        result.append(grouped_entry)

    for r in result:
        out_write(json.dumps(r))


def cmd_cluster(field, threshold):
    groups = defaultdict(list)
    data = []
    for line in input_lines():
        if field is None:
            data.append({LINE_KEY: line})
        else:
            data.append(json.loads(line))
    field = field if field is not None else LINE_KEY
    while data:
        base = data.pop(0)
        groups[base[field]].append(base)
        similar = []
        for s in data:
            matcher = SequenceMatcher(None, base[field], s[field])
            if matcher.ratio() > threshold:
                similar.append((s, matcher.ratio()))
        for s in similar:
            s, ratio = s
            s[CLUSTER_RATIO_KEY] = ratio
            groups[base[field]].append(s)
            data.remove(s)
    for key, value in groups.items():
        out_write(json.dumps({field: key, GROUPED_KEY: value}))


def cmd_count():
    c = 0
    for _ in input_lines():
        c += 1
    out_write(str(c))


def cmd_show(fields):
    for line in input_lines():
        line = json.loads(line)
        filtered_data = {}
        for field in fields:
            filtered_data[field] = line[field] if field in line else None
        out_write(json.dumps(filtered_data))


def cmd_resolve_multiline(line_pattern):
    previous_line = None
    for line in input_lines(strip=False):
        if re.search(line_pattern, line):
            if previous_line is not None:
                out_write(json.dumps({LINE_KEY: previous_line}))
            previous_line = line
        else:
            if previous_line is not None:
                previous_line += "\n" + line
            else:
                previous_line = line
    if previous_line is not None:
        out_write(json.dumps({LINE_KEY: previous_line}))


def cmd_graph(x_fields, y_fields, width=100):
    from collections import OrderedDict
    x_fields = x_fields.split(",")
    y_fields = y_fields.split(",")

    data = [json.loads(line) for line in input_lines()]

    value_map = OrderedDict()
    labels = []
    for item in data:
        label = " | ".join(
            str(item.get(field, "null")) if item.get(field) is not None else "null" for field in x_fields)
        if label not in value_map:
            value_map[label] = OrderedDict()
            labels.append(label)
        for y_field in y_fields:
            value_map[label][y_field] = item.get(y_field, 0) or 0

    yfield_color = {}
    for idx, y_field in enumerate(y_fields):
        yfield_color[y_field] = ANSI_COLORS[idx % len(ANSI_COLORS)]

    max_per_field = {y: max((value_map[label][y] for label in labels), default=0) for y in y_fields}
    longest_label = max((len(label) for label in labels), default=0)
    y_field_name_len = max((len(y) for y in y_fields), default=0)

    for label in labels:
        for i, y_field in enumerate(y_fields):
            value = value_map[label][y_field]
            max_value = max_per_field[y_field] or 1  # Avoid division by zero
            bar_len = int((value / max_value) * width) if max_value else 0
            bar = '#' * bar_len
            color = yfield_color[y_field]
            # Only print the label on the first y_field row per label group
            label_to_print = label if i == 0 else ' ' * longest_label
            print(f"{label_to_print:>{longest_label}} | {y_field:>{y_field_name_len}}: {color}{bar}{RESET} ({value})")

    # endregion

def cmd_gen(expr):
    data = safe_eval(expr, {})
    if isinstance(data, list):
        for line in data:
            out_write(json.dumps(line))
    else:
        out_write(json.dumps(data))

sys.stdout.reconfigure(line_buffering=True)

if __name__ == '__main__':
    try:
        args = sys.argv[1:]
        action = args[0] if len(args) > 0 else "help"
        if action == "help":
            cmd_help()
        elif action == "rex":
            regex = args[1]
            cmd_rex(regex)
        elif action == "mul":
            line_pattern = args[1]
            cmd_resolve_multiline(line_pattern)
        elif action == "match":
            regex = args[1]
            cmd_match(regex)
        elif action == "where":
            expr = args[1]
            cmd_where(expr)
        elif action == "eval":
            expr = args[1]
            cmd_eval(expr)
        elif action == "geval":
            expr = args[1]
            cmd_group_eval(expr)
        elif action == "sort":
            options = args[1:]
            cmd_sort(options)
        elif action == "reverse":
            cmd_reverse()
        elif action == "group":
            cmd_group(args[1:])
        elif action == "cluster":
            threshold = 0.7
            for arg in args[1:]:
                if arg.startswith("-t="):
                    threshold = float(arg.split("=", 1)[1])
                    args.remove(arg)
                    break
            cmd_cluster(args[1] if len(args) > 1 else None, threshold)
        elif action == "count":
            cmd_count()
        elif action == "show":
            cmd_show(args[1:])
        elif action == "table":
            cmd_table()
        elif action == "json":
            cmd_json()
        elif action == "lookup":
            cmd_lookup(args[1], args[2], args[3] if len(args) > 3 else "left")
        elif action == "graph":
            cmd_graph(args[1], args[2], int(args[3]) if len(args) > 3 else 100)
        elif action == "gen":
            expr = args[1]
            cmd_gen(expr)
        else:
            err_write("unknown command: " + action)
            exit(1)
    except KeyboardInterrupt:
        err_write("\nInterrupted")
        sys.stderr.close()
    except InterruptedError:
        sys.stderr.close()
