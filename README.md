# Log Analyzer Tool

A powerful command-line tool for advanced log processing and manipulation.

## Overview

Log Analyzer is a versatile tool designed to help you extract, filter, transform, and visualize log data directly from the command line. It provides a rich set of commands for working with log files, making it easy to:

- Extract structured data from unstructured logs
- Filter logs based on complex conditions
- Group and aggregate log data
- Visualize log patterns and trends
- Process multiline log entries
- And much more!

## Setup

### Installation

#### Unix/Linux/macOS

```shell
bash -c "$(curl -fsSL https://github.com/zchandikaz/log-analyzer/raw/refs/heads/master/install.sh)"
```

#### Windows

```powershell
powershell -ExecutionPolicy Bypass -Command "Invoke-Expression (New-Object System.Net.WebClient).DownloadString('https://github.com/zchandikaz/log-analyzer/raw/refs/heads/master/install.ps1')"
```

This will install the `lgx` command-line tool on your system.

## Usage

Log Analyzer is designed to work with command-line pipes, allowing you to chain commands together for complex log processing workflows. It works on both Unix-based systems (using bash pipes) and Windows systems (using PowerShell or Command Prompt pipes).

### Basic Usage Pattern

Unix/Linux/macOS:
```shell
cat your_log_file.log | lgx <command> [options]
```

Windows (PowerShell):
```powershell
Get-Content your_log_file.log | lgx <command> [options]
```

Windows (Command Prompt):
```cmd
type your_log_file.log | lgx <command> [options]
```

### Example Workflows

1. **Extract request IDs and group logs:**
   ```shell
   # Extract request ID from log lines and group all logs with the same ID
   cat server.log | lgx rex "rid=(?P<rid>\d+)" | lgx group rid
   ```

2. **Calculate duration for each group:**
   ```shell
   # For each group, calculate the duration by finding the difference between max and min request IDs
   cat grouped.log | lgx geval "duration = max(ts) - min(ts)"
   ```

3. **Sort the grouped logs by the calculated duration in descending order:**
   ```shell
   # Sort groups by duration in descending order to find the longest-running requests
   cat grouped.log | lgx sort -duration
   ```

4. **Join with user data and create a table:**
   ```shell
   # Enrich logs with user information and display as a formatted table
   cat logs.json | lgx lookup user_id '[{"user_id": 123, "name": "John"}]' | lgx table
   ```

5. **Visualize response times per service:**
   ```shell
   # Create a bar graph showing response times for different services
   # Colors are automatically assigned to different metrics for easy distinction
   cat stats.json | lgx graph service response_time 80
   ```

6. **Extract data while resolving multiline logs:**
   ```shell
   # Combine multiline log entries, then extract and display only the log level and message
   cat raw.log | lgx mul "^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]" | lgx rex "(?P<level>[A-Z]+)" | lgx fields level message
   ```

7. **Cluster log messages for similarity detection:**
   ```shell
   # Group similar log messages with 75% similarity threshold and display as a table
   cat logs.json | lgx cluster message -t=0.75 | lgx table
   ```

8. **Generate test data:**
   ```shell
   # Create 10 sample log entries with sequential IDs
   lgx gen "[{'id':i} for i in range(10)]"
   ```

## Command Reference

### 1. match \<regex\>
- Filters logs that match the given regular expression.
- Example:
  ```shell
  cat server.log | lgx match "Access"
  ```

### 2. rex \<regex\> [-i=field_name]
- Extracts fields from log lines using a named-group regular expression and appends these fields as JSON.
- The -i parameter allows you to apply the regex to a specific field in the JSON data instead of the entire line.
- Example:
  ```shell
  cat server.log | lgx rex "(?P<url>[A-Z]+ \S+)"
  ```
- Extract fields from specific input field in JSON data:
  ```shell
  cat server.log | lgx rex "(?P<method>[A-Z]+)" -i=request
  ```

### 3. where \<expression\>
- Filters logs based on the provided Python expression.
- The expression has access to all fields in the JSON data and can use Python built-in functions.
- Example:
  ```shell
  cat server.log | lgx where "'GET' in url"
  ```
- Filter logs by numerical comparison:
  ```shell
  cat server.log | lgx where "response_time > 200"
  ```

### 4. group \<fields\>
- Groups logs by the specified keys, storing all grouped logs under a _grouped key.
- Multiple fields can be specified for multi-level grouping.
- Example:
  ```shell
  cat server.log | lgx rex "(?P<rid>\d+)" | lgx group rid
  ```

### 5. eval \<expression\>
- Executes a Python statement on each log line's JSON representation. Updates the log data accordingly.
- Useful for adding new fields or modifying existing ones.
- Example:
  ```shell
  cat grouped.log | lgx eval "total_errors = len(_grouped)"
  ```
- Add a new field calculation:
  ```shell
  cat logs.json | lgx eval "status_code_group = status_code // 100"
  ```

### 6. geval \<expression\>
- Similar to eval, but specifically designed to work on grouped data.
- Provides access to aggregated data across all items in a group.
- Can perform calculations using all values of a field across the group (min, max, sum, etc.).
- Example:
  ```shell
  cat grouped.log | lgx geval "duration = max(rid) - min(rid)"
  ```
- Calculate average response time:
  ```shell
  cat grouped.log | lgx geval "avg_response_time = sum(response_time) / len(response_time)"
  ```

### 7. sort \<options\>
- Sorts logs by specified fields. Use + for ascending (default) and - for descending sorting.
- Multiple sort fields can be specified for multi-level sorting.
- Example:
  ```shell
  cat logs.json | lgx sort -duration
  ```
- Sort by multiple fields:
  ```shell
  cat grouped.log | lgx sort -duration +status_code
  ```

### 8. reverse
- Reverses the order of logs.
- Useful after a sort operation to get the opposite order.
- Example:
  ```shell
  cat sorted.log | lgx reverse
  ```

### 9. count
- Outputs the total count of log entries.
- Example:
  ```shell
  cat server.log | lgx count
  ```

### 10. fields \<fields\>
- Displays only the specified fields from each log.
- Fields not present in the log will be shown as null.
- Example:
  ```shell
  cat server.log | lgx fields rid duration
  ```
- Display specific fields with missing values as None:
  ```shell
  cat server.log | lgx fields url response_time
  ```

### 11. table
- Outputs logs in a human-readable table format.
- Automatically adjusts column widths based on content.
- Example:
  ```shell
  cat server.log | lgx table
  ```

### 12. json
- Outputs the log data as a single JSON array.
- Useful for further processing with other JSON tools.
- Example:
  ```shell
  cat server.log | lgx json
  ```

### 13. lookup \<field\> \<lookup_data_command\> [join_type]
- Joins log data with lookup data based on a common field.
- The lookup_data_command is executed to retrieve the lookup data (must output valid JSON).
- Join types: left (default), right, inner, outer
- Example:
  ```shell
  cat logs.json | lgx lookup user_id 'echo "[{\"user_id\": 123, \"name\": \"John\"}]"'
  ```
- Using a command to generate lookup data:
  ```shell
  cat logs.json | lgx lookup user_id 'cat users.json'
  ```
- Using different join types:
  ```shell
  cat logs.json | lgx lookup user_id 'echo "[{\"user_id\": 123, \"name\": \"John\"}]"' inner
  ```

### 14. graph \<x_fields\> \<y_fields\> [width]
- Creates an ASCII bar graph visualization of the data.
- Multiple x_fields and y_fields can be specified as comma-separated values.
- Different y_fields are displayed with different colors for easy distinction.
- The optional width parameter controls the maximum width of the bars.
- Example:
  ```shell
  cat stats.json | lgx graph timestamp,service response_time 80
  ```
- Multiple y-fields with color coding:
  ```shell
  cat stats.json | lgx graph service errors,warnings,info 100
  ```

### 15. cluster \<field\> [-t=threshold]
- Groups similar logs based on the similarity of the specified field.
- The threshold parameter (between 0.0 and 1.0) controls how similar logs must be to be grouped together.
- Higher threshold values (closer to 1.0) require greater similarity.
- Each cluster includes a _cluster_ratio field indicating the similarity score.
- Example:
  ```shell
  cat logs.json | lgx cluster message -t=0.8
  ```
- Lower threshold for more inclusive clustering:
  ```shell
  cat logs.json | lgx cluster message -t=0.6
  ```

### 16. mul \<regex\>
- Resolves multiline log entries based on a starting line pattern.
- Combines lines that don't match the pattern with the previous matching line.
- Example:
  ```shell
  cat app.log | lgx mul "^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]"
  ```
- Process Java stack traces:
  ```shell
  cat java.log | lgx mul "^[0-9]{4}-[0-9]{2}-[0-9]{2}"
  ```

### 17. gen \<expression\>
- Generates data from Python expression and outputs as JSON lines.
- Useful for creating test data or sample inputs.
- Example:
  ```shell
  lgx gen "[{'id':i, 'value':i*2} for i in range(5)]"
  ```
- Generate more complex test data:
  ```shell
  lgx gen "[{'timestamp': f'2023-01-{i:02d}', 'count': i*10} for i in range(1, 31)]"
  ```

### 18. dedup \<fields\>
- Removes duplicate entries based on the specified fields.
- Keeps only the first occurrence of each unique combination of field values.
- Example:
  ```shell
  cat logs.json | lgx dedup user_id
  ```
- Deduplicate based on multiple fields:
  ```shell
  cat logs.json | lgx dedup user_id request_path
  ```

### 19. csv
- Outputs the log data as a CSV file.
- Automatically includes headers based on all fields present in the data.
- Properly escapes special characters and handles quoting.
- Example:
  ```shell
  cat logs.json | lgx csv
  ```
- Process and export data to CSV:
  ```shell
  cat logs.json | lgx where "status_code >= 400" | lgx csv
  ```

## Examples

The repository includes detailed examples demonstrating how to use Log Analyzer for different types of logs:

- [Access Log Analysis](examples/analyze-access-logs.md)
- [Java Application Log Analysis](examples/analyze-java-logs.md)

Sample log files are provided in the `examples/logs/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
