import json
import random
import urllib.request
import math
import re
import subprocess
import sys
from collections import OrderedDict
from collections import defaultdict
from contextlib import contextmanager
from datetime import *
from difflib import SequenceMatcher
from enum import Enum

def percentile(data, p):
    """
    Calculate the p-th percentile of a list of numbers.

    Args:
        data: List of numbers
        p: Percentile (0-100)
    Returns:
        The p-th percentile value

    Example:
        percentile([1,2,3,4,5], 90)  # returns 90th percentile
    """
    if not 0 <= p <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    # Make a copy and sort the data
    sorted_data = sorted(data)
    n = len(sorted_data)

    if n == 0:
        raise ValueError("Cannot calculate percentile of empty list")

    # Convert percentage to decimal
    p = p / 100.0

    # Calculate the index
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        # If k is an integer, return that value
        return sorted_data[int(k)]
    else:
        # Linear interpolation between the two nearest values
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1


EXEC_UTIL_FUNCS = {
    'strptime': lambda date_str, fmt="%Y-%m-%d %H:%M:%S": datetime.strptime(date_str, fmt).timestamp() * 1000,
    'strftime': lambda dt, fmt="%Y-%m-%d %H:%M:%S": datetime.fromtimestamp(dt / 1000).strftime(fmt),
    'perc': percentile,
    'avg': lambda data: sum(data) / len(data),
    'iif': lambda cond, true_val, false_val: true_val if cond else false_val,
    'replace': lambda text, pattern, replacement : re.sub(pattern, replacement, text, flags=re.DOTALL),
    'randint': random.randint
}
BUILTINS = __builtins__
CONCURRENT_THREAD_COUNT = 20

GROUPED_KEY = "_grouped"
LINE_KEY = "_line"
CLUSTER_RATIO_KEY = "_cluster_ratio"


class Colors(Enum):
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


ANSI_COLORS = [
    Colors.CYAN.value,
    Colors.YELLOW.value,
    Colors.MAGENTA.value,
    Colors.GREEN.value,
    Colors.BLUE.value,
    Colors.RED.value
]

documentation = r"""
Log Analyzer Tool - Command Line Documentation

This tool allows advanced log processing and manipulation using various commands. Below is an overview of the available functionality with examples.

Commands:
---------

1. match <regex>
   - Filters logs that match the given regular expression.
   - Example:
     cat server.log | lgx match "Access"

2. rex <regex> [-i=field_name]
   - Extracts fields from log lines using a named-group regular expression and appends these fields as JSON.
   - The -i parameter allows you to apply the regex to a specific field in the JSON data instead of the entire line.
   - Example:
     cat server.log | lgx rex "(?P<url>[A-Z]+ \S+)"
   - Extract fields from specific input field in JSON data:
     cat server.log | lgx rex "(?P<method>[A-Z]+)" -i=request

3. where <expression>
   - Filters logs based on the provided Python expression.
   - The expression has access to all fields in the JSON data and can use Python built-in functions.
   - Example:
     cat server.log | lgx where "'GET' in url"
   - Filter logs by numerical comparison:
     cat server.log | lgx where "response_time > 200"

4. group <fields>
   - Groups logs by the specified keys, storing all grouped logs under a _grouped key.
   - Multiple fields can be specified for multi-level grouping.
   - Example:
     cat server.log | lgx rex "(?P<rid>\d+)" | lgx group rid

5. eval <expression>
   - Executes a Python statement on each log line's JSON representation. Updates the log data accordingly.
   - Useful for adding new fields or modifying existing ones.
   - Example:
     cat grouped.log | lgx eval "total_errors = len(_grouped)"
   - Add a new field calculation:
     cat logs.json | lgx eval "status_code_group = status_code // 100"

6. geval <expression>
   - Similar to eval, but specifically designed to work on grouped data.
   - Provides access to aggregated data across all items in a group.
   - Can perform calculations using all values of a field across the group (min, max, sum, etc.).
   - Example:
     cat grouped.log | lgx geval "duration = max(rid) - min(rid)"
   - Calculate average response time:
     cat grouped.log | lgx geval "avg_response_time = sum(response_time) / len(response_time)"

7. sort <options>
   - Sorts logs by specified fields. Use + for ascending (default) and - for descending sorting.
   - Multiple sort fields can be specified for multi-level sorting.
   - Example:
     cat logs.json | lgx sort -duration
   - Sort by multiple fields:
     cat grouped.log | lgx sort -duration +status_code

8. reverse
   - Reverses the order of logs.
   - Useful after a sort operation to get the opposite order.
   - Example:
     cat sorted.log | lgx reverse

9. count
   - Outputs the total count of log entries.
   - Example:
     cat server.log | lgx count

10. fields <fields>
    - Displays only the specified fields from each log.
    - Fields not present in the log will be shown as null.
    - Example:
      cat server.log | lgx fields rid duration
    - Display specific fields with missing values as None:
      cat server.log | lgx fields url response_time

11. table
    - Outputs logs in a human-readable table format.
    - Automatically adjusts column widths based on content.
    - Example:
      cat server.log | lgx table

12. json
    - Outputs the log data as a single JSON array.
    - Useful for further processing with other JSON tools.
    - Example:
      cat server.log | lgx json

13. lookup <field> <lookup_data_command> [join_type]
    - Joins log data with lookup data based on a common field.
    - The lookup_data_command is executed to retrieve the lookup data (must output valid JSON).
    - Join types: left (default), right, inner, outer
    - Example:
      cat logs.json | lgx lookup user_id 'echo "[{\"user_id\": 123, \"name\": \"John\"}]"'
    - Using a command to generate lookup data:
      cat logs.json | lgx lookup user_id 'cat users.json'
    - Using different join types:
      cat logs.json | lgx lookup user_id 'echo "[{\"user_id\": 123, \"name\": \"John\"}]"' inner

14. graph <x_fields> <y_fields> [width]
    - Creates an ASCII bar graph visualization of the data.
    - Multiple x_fields and y_fields can be specified as comma-separated values.
    - Different y_fields are displayed with different colors for easy distinction.
    - The optional width parameter controls the maximum width of the bars.
    - Example:
      cat stats.json | lgx graph timestamp,service response_time 80
    - Multiple y-fields with color coding:
      cat stats.json | lgx graph service errors,warnings,info 100

15. cluster <field> [-t=threshold]
    - Groups similar logs based on the similarity of the specified field.
    - The threshold parameter (between 0.0 and 1.0) controls how similar logs must be to be grouped together.
    - Higher threshold values (closer to 1.0) require greater similarity.
    - Each cluster includes a _cluster_ratio field indicating the similarity score.
    - Example:
      cat logs.json | lgx cluster message -t=0.8
    - Lower threshold for more inclusive clustering:
      cat logs.json | lgx cluster message -t=0.6

16. mul <regex>
    - Resolves multiline log entries based on a starting line pattern.
    - Combines lines that don't match the pattern with the previous matching line.
    - Example:
      cat app.log | lgx mul "^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]"
    - Process Java stack traces:
      cat java.log | lgx mul "^[0-9]{4}-[0-9]{2}-[0-9]{2}"

17. gen <expression>
    - Generates data from Python expression and outputs as JSON lines.
    - Useful for creating test data or sample inputs.
    - Example:
      lgx gen "[{'id':i, 'value':i*2} for i in range(5)]"
    - Generate more complex test data:
      lgx gen "[{'timestamp': f'2023-01-{i:02d}', 'count': i*10} for i in range(1, 31)]"

18. dedup <fields>
    - Removes duplicate entries based on the specified fields.
    - Keeps only the first occurrence of each unique combination of field values.
    - Example:
      cat logs.json | lgx dedup user_id
    - Deduplicate based on multiple fields:
      cat logs.json | lgx dedup user_id request_path

19. accum <fields>
    - Accumulates values for specified numeric fields across JSON log entries.
    - Maintains a running total for each field and updates each log entry with the accumulated value.
    - Example:
      cat metrics.json | lgx accum count
    - Accumulate multiple fields:
      cat metrics.json | lgx accum errors warnings

20. csv
    - Outputs the log data as a CSV file.
    - Automatically includes headers based on all fields present in the data.
    - Properly escapes special characters and handles quoting.
    - Example:
      cat logs.json | lgx csv
    - Process and export data to CSV:
      cat logs.json | lgx where "status_code >= 400" | lgx csv

21. upgrade
    - Updates the log analyzer tool to the latest version from the GitHub repository.
    - This command downloads the latest version of the script and replaces the current installation.
    - Example:
      lgx upgrade

22. highlight <text_list>
    - Highlights specified text in each log line with different colors.
    - Multiple text strings can be provided, each will be highlighted with a different color.
    - Colors cycle through cyan, yellow, magenta, green, blue, and red if more than 6 text strings are provided.
    - Example:
      cat server.log | lgx highlight ERROR WARNING
    - Highlight multiple terms with different colors:
      cat app.log | lgx highlight exception error warning

Examples:
---------

Example Workflow:
-----------------
1. Extract request IDs and group logs:
   # Extract request ID from log lines and group all logs with the same ID
   cat server.log | lgx rex "(?P<rid>\d+)" | lgx group rid

2. Calculate duration for each group:
   # For each group, calculate the duration by finding the difference between max and min request IDs
   cat grouped.log | lgx geval "duration = max(rid) - min(rid)"

3. Sort the grouped logs by the calculated duration in descending order:
   # Sort groups by duration in descending order to find the longest-running requests
   cat grouped.log | lgx sort -duration

4. Join with user data and create a table:
   # Enrich logs with user information and display as a formatted table
   cat logs.json | lgx lookup user_id '[{"user_id": 123, "name": "John"}]' | lgx table

5. Visualize response times per service:
   # Create a bar graph showing response times for different services
   # Colors are automatically assigned to different metrics for easy distinction
   cat stats.json | lgx graph service response_time 80

6. Extract data while resolving multiline logs:
   # Combine multiline log entries, then extract and display only the log level and message
   cat raw.log | lgx mul "^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]" | lgx rex "(?P<level>[A-Z]+)" | lgx fields level message

7. Cluster log messages for similarity detection:
   # Group similar log messages with 75% similarity threshold and display as a table
   cat logs.json | lgx cluster message -t=0.75 | lgx table

8. Generate test data:
   # Create 10 sample log entries with sequential IDs
   lgx gen "[{'id':i} for i in range(10)]"

"""


# region : utils

def match_line_with_regex(line, regex):
    return re.search(regex, line, re.DOTALL) is not None


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
    match = re.search(regex, line, re.DOTALL)
    if match:
        groups = match.groupdict() if match.groupdict() else {i: g for i, g in enumerate(match.groups(), start=1)}
        return groups
    return {}


def out_write(line):
    try:
        sys.stdout.write(line + "\n")
    except OSError:
        raise InterruptedError


def err_write(line, color=None):
    try:
        if sys.stderr.isatty() and color and isinstance(color, Colors):
            sys.stderr.write(color.value + line + Colors.RESET.value + "\n")
        else:
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


def execute_command(command):
    try:
        # Run the command and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,  # Capture both stdout and stderr
            text=True,  # Return strings rather than bytes
            check=True  # Raise exception if command fails
        )
        return {
            'success': True,
            'output': result.stdout,
            'error': None,
            'return_code': result.returncode
        }
    except subprocess.CalledProcessError as e:
        # Handle command execution errors
        return {
            'success': False,
            'output': e.stdout,
            'error': e.stderr,
            'return_code': e.returncode
        }
    except Exception as e:
        # Handle other exceptions
        return {
            'success': False,
            'output': None,
            'error': str(e),
            'return_code': -1
        }


@contextmanager
def error_handler(operation_name, context_info={}):
    try:
        yield context_info
    except (InterruptedError, KeyboardInterrupt):
        sys.stderr.close()
    except Exception as e:
        error_msg = f"""
{Colors.RED.value}Error while processing command {operation_name.upper()} {Colors.RESET.value}
{Colors.YELLOW.value}Error: {Colors.RESET.value}{str(e)}"""
        for context_key, context_value in context_info.items():
            context_value = str(context_value)
            if "\n" in context_value:
                context_value = "\n" + context_value
            error_msg += f"\n{Colors.YELLOW.value}{context_key}: {Colors.RESET.value} {context_value}"
        err_write(error_msg)
        exit(1)


def json_loads(line, description=None):
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        if description:
            raise Exception(f"Invalid {description} format, Expected JSON format. | {str(e)}")
        else:
            raise Exception(f"Invalid data format, Expected JSON format. | {str(e)}")


# endregion

# region : cmd
def cmd_rex(regex, input_field=None):
    for line in input_lines():
        with error_handler("rex", {"Regex": regex, "Line": line}):
            if input_field is not None:
                data = json_loads(line)
                extracted_fields = regex_extract(data[input_field] if input_field in data else '', regex)
                data.update(extracted_fields)
                out_write(json.dumps(data))
            else:
                extracted_fields = regex_extract(line, regex)
                extracted_fields[LINE_KEY] = line
                out_write(json.dumps(extracted_fields))


def cmd_match(regex):
    for line in input_lines():
        with error_handler("match", {"Regex": regex, "Line": line}):
            if match_line_with_regex(line, regex):
                out_write(line)


def cmd_where(expr):
    for line in input_lines():
        with error_handler("where", {"Expression": expr, "Line": line}):
            if safe_eval(expr, json_loads(line)):
                out_write(line)


def cmd_eval(expr):
    for line in input_lines():
        with error_handler("eval", {"Expression": expr, "Line": line}):
            data = json_loads(line)
            safe_exec(expr, data)
            out_write(json.dumps(data))


def cmd_sort(sort_option_exprs, limit=None):
    lines = [NullSafeDict(json_loads(line)) for line in input_lines()]
    sort_options = []
    with error_handler("sort", {"Options": " ".join(sort_option_exprs)}):
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
                        raise Exception("negative sort key for non-numeric value not supported: " + field_name + "")
                else:
                    key.append(line_data.get(field_name))
            return tuple(key)

        lines.sort(key=sort_key)

        count = 0
        for line in lines:
            count += 1
            if limit is not None and count > limit:
                break
            out_write(json.dumps(line))


def cmd_group_eval(expr):
    for line in input_lines():
        with error_handler("geval", {"Expression": expr, "Line": line}):
            data = json_loads(line)
            safe_exec(expr, data, True)
            out_write(json.dumps(data))


def cmd_reverse():
    with error_handler("reverse", {}):
        lines = [line for line in input_lines()]

        lines.reverse()

        for line in lines:
            out_write(line)


def cmd_help():
    out_write(documentation)


def cmd_table(fields=[]):
    with error_handler("table", {"Fields": " ".join(fields)}):
        data = [NullSafeDict(json_loads(line)) for line in input_lines()]
        if not data:
            return

        # If fields are specified, use them as headers and filter data
        if fields and len(fields) > 0:
            headers = fields
            # Filter out unwanted fields from each row
            for d in data:
                keys_to_remove = [k for k in d.keys() if k not in fields]
                for k in keys_to_remove:
                    del d[k]
        else:
            # If no fields specified, use all keys from first row as headers
            headers = list(data[0].keys())

        # Calculate column widths based on data and headers
        col_widths = []
        for header in headers:
            # Get max width of header and all values in this column
            width = len(str(header))
            for row in data:
                cell_value = str(row.get(header, ''))
                width = max(width, len(cell_value))
            col_widths.append(width)

        # Write header row
        header_row = " | ".join(header.ljust(width) for header, width in zip(headers, col_widths))
        out_write(header_row)
        out_write("-" * len(header_row))

        # Write data rows
        for row in data:
            row_str = " | ".join(str(row.get(key, '')).ljust(width) for key, width in zip(headers, col_widths))
            out_write(row_str)


def cmd_json():
    with error_handler("json", {}):
        out_write(json.dumps([json_loads(line) for line in input_lines()]))


def cmd_csv():
    with error_handler("csv", {}):
        # Collect all lines and their fields
        data = [json_loads(line) for line in input_lines()]
        if not data:
            return

        # Get all unique fields across all records
        fields = set()
        for item in data:
            fields.update(item.keys())
        fields = sorted(list(fields))  # Sort fields for consistent column order

        # Write header
        out_write(','.join(f'"{field}"' for field in fields))

        # Write data rows
        for item in data:
            row = []
            for field in fields:
                value = item.get(field, '')
                # Escape quotes and special characters
                if isinstance(value, str):
                    value = f'"{value.replace("`", "``")}"'
                elif value is None:
                    value = '""'
                else:
                    value = str(value)
                row.append(value)
            out_write(','.join(row))


def cmd_lookup(field, lookup_data_command, join_type="left"):
    if not field:
        err_write("No lookup field specified", Colors.RED)
        exit(1)

    common_err_context_info = {"Join Type": join_type, "Lookup Data Retrieval Command": lookup_data_command}
    with error_handler("lookup", {**common_err_context_info}) as err_context_info:
        result = execute_command(lookup_data_command)
        if not result['success']:
            raise Exception("Error in the lookup command: " + str(result['error']))

        lookup_data = result['output']
        err_context_info['Lookup Data'] = lookup_data
        right_data = json_loads(lookup_data, description="lookup data")
        if not right_data:
            raise Exception("Empty lookup data.")

    if join_type == "right" or join_type == "outer":
        with error_handler("lookup", {**common_err_context_info}):
            left_data = [json_loads(line) for line in input_lines()]
            joined_data = join_dict_lists(left_data, right_data, field, join_type)
            for line in joined_data:
                out_write(json.dumps(line))
    else:
        with error_handler("lookup", {**common_err_context_info}):
            right_lookup = defaultdict(list)
            for r in right_data:
                right_lookup[r.get(field)].append(r)

            for lidx, l in enumerate(input_lines()):
                with error_handler("lookup", {**common_err_context_info, "Line": l}):
                    l = json_loads(l)
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
        with error_handler("group", {"Group Keys": group_keys, "Line": line}):
            line_data = NullSafeDict(json_loads(line))
            key = tuple(line_data[k] for k in group_keys)
            # Extract the rest of the fields
            remainder = {k: v for k, v in line_data.items() if k not in group_keys}
            grouped[key].append(remainder)

    result = []
    with error_handler("group", {"Group Keys": group_keys}):
        for key, group_items in grouped.items():
            grouped_entry = dict(zip(group_keys, key))
            grouped_entry[GROUPED_KEY] = group_items
            result.append(grouped_entry)

        for r in result:
            out_write(json.dumps(r))


def cmd_cluster(field, threshold):
    with error_handler("cluster", {"Field": field, "Threshold": threshold}):
        groups = defaultdict(list)
        data = []
        for line in input_lines():
            if field is None:
                data.append({LINE_KEY: line})
            else:
                data.append(json_loads(line))
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
    with error_handler("count"):
        c = 0
        for _ in input_lines():
            c += 1
        out_write(str(c))


def cmd_fields(fields):
    for line in input_lines():
        with error_handler("fields", {"Line": line, "Fields": fields}):
            line = json_loads(line)
            filtered_data = {}
            for field in fields:
                filtered_data[field] = line[field] if field in line else None
            out_write(json.dumps(filtered_data))


def cmd_mul(line_pattern):
    previous_line = None
    for line in input_lines(strip=False):
        with error_handler("fields", {"Line": line}):
            if re.search(line_pattern, line, re.DOTALL):
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
    with error_handler("graph", {"X Fields": x_fields, "Y Fields": y_fields, "Width": width}):
        x_fields = x_fields.split(",")
        y_fields = y_fields.split(",")

        data = [json_loads(line) for line in input_lines()]

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
                # Only write the label on the first y_field row per label group
                label_to_write = label if i == 0 else ' ' * longest_label
                out_write(
                    f"{label_to_write:>{longest_label}} | {y_field:>{y_field_name_len}}: {color}{bar}{Colors.RESET.value} ({value})")


def cmd_gen(expr):
    with error_handler("gen", {"Expression": expr}):
        data = safe_eval(expr, {})
        if isinstance(data, list):
            for line in data:
                out_write(json.dumps(line))
        else:
            out_write(json.dumps(data))


def cmd_dedup(fields):
    known_lines = []
    for line in input_lines():
        with error_handler("dedup", {"Line": line, "Fields": fields}):
            data = NullSafeDict(json_loads(line))
            key_data = ",".join([str(data[f]) for f in fields])
            if key_data not in known_lines:
                known_lines.append(key_data)
                out_write(line)

def cmd_accum(fields):
    accum_data={}
    for line in input_lines():
        with error_handler("accum", {"Line": line, "Fields": fields}):
            data = NullSafeDict(json_loads(line))
            for f in fields:
                current_value = accum_data[f] if f in accum_data else 0
                data[f] = current_value + data[f]
                accum_data[f] = data[f]
            out_write(json.dumps(data))

def cmd_highlight(text_list):
    for line in input_lines():
        with error_handler("highlight", {"Text List": text_list}):
            for i in range(len(text_list)):
                text = text_list[i]
                color = ANSI_COLORS[i%len(ANSI_COLORS)]
                line = line.replace(text, f"{color}{text}{Colors.RESET.value}")
            out_write(line)

def cmd_upgrade():
    with error_handler("upgrade"):
        url = "https://raw.githubusercontent.com/zchandikaz/log-analyzer/main/log_analyzer.py"
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')

        with open(__file__, 'w') as f:
            f.write(content)

        out_write("Successfully upgraded.")

# endregion


sys.stdout.reconfigure(line_buffering=True)

if __name__ == '__main__':
    args = sys.argv[1:]
    action = args[0] if len(args) > 0 else "help"
    with error_handler(action, {"Parameters": args[1:]}) as err_context_info:
        if action == "help":
            cmd_help()
        elif action == "rex":
            regex = args[1]
            input_field = None
            for arg in args[2:]:
                if arg.startswith("-i="):
                    input_field = arg.split("=", 1)[1]
                    break
                elif arg.startswith("--input_field="):  # For backward compatibility
                    input_field = arg.split("=", 1)[1]
                    break
            cmd_rex(regex, input_field)
        elif action == "mul":
            line_pattern = args[1]
            cmd_mul(line_pattern)
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
            limit = None
            for arg in args[1:]:
                if arg.startswith("-l=") or arg.startswith("--limit="):
                    limit = int(arg.split("=")[1])
                    args.remove(arg)
                    break

            cmd_sort(args[1:], limit)
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
        elif action == "fields":
            cmd_fields(args[1:])
        elif action == "table":
            cmd_table(args[1:])
        elif action == "dedup":
            cmd_dedup(args[1:])
        elif action == "accum":
            cmd_accum(args[1:])
        elif action == "highlight":
            cmd_highlight(args[1:])
        elif action == "json":
            cmd_json()
        elif action == "csv":
            cmd_csv()
        elif action == "lookup":
            cmd_lookup(args[1], args[2], args[3] if len(args) > 3 else "left")
        elif action == "graph":
            cmd_graph(args[1], args[2], int(args[3]) if len(args) > 3 else 100)
        elif action == "gen":
            expr = args[1]
            cmd_gen(expr)
        elif action == "upgrade":
            cmd_upgrade()
        else:
            raise Exception("Unknown command.")
