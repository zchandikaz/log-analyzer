# Analyze Access Logs

A sample access log file is provided in the logs folder for you to work with.

## Extract Fields
Before analyzing logs, you need to extract the important data from them. You can use a regular expression (regex) to accomplish this. The following examples use regex syntax compatible with Python.

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"'
```

## Display Data as a Table

You can view the extracted data in a tabular format for better readability:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx table timestamp method path status bytes
```

## Sort Data

### Sort by HTTP Method

You can sort the data by HTTP method:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx sort method \
|lgx table timestamp method path status bytes
```

### Sort by Response Size (Descending)

When sorting by numeric fields, ensure they are converted to the correct data type first:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'bytes=int(bytes)' \
|lgx sort -bytes \
|lgx table timestamp method path status bytes
```

## Create Custom Fields

To analyze requests effectively, it's useful to combine the HTTP method and path into a single field. You can create a custom field called "request" using the `eval` command:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'request=method+" "+path' \
|lgx table request
```

## Group and Aggregate Data

### Count Requests by Type

To see the count of requests per request type, use the `group` command followed by the `geval` command to perform actions on grouped values:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'request=method+" "+path' \
|lgx group request \
|lgx geval 'count=len(_line)' \
|lgx table request count
```

### Count Requests by IP and Request Type

To analyze the distribution of requests by both IP address and request type:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'request=method+" "+path' \
|lgx group ip request \
|lgx geval 'count=len(_line)' \
|lgx table ip request count
```

### Include Maximum Response Size

To include the maximum response size for each IP and request type combination:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'res_size_kb=int(bytes)/1024; request=method+" "+path' \
|lgx group ip request \
|lgx geval 'count=len(_line); max_response_size_kb=max(res_size_kb)' \
|lgx sort -count \
|lgx table ip request max_response_size_kb count 
```

## Filter Data

### Find Repeated Requests from Same IP

To identify cases where the same IP address made multiple requests of the same type, use the `where` command to filter the results:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'res_size_kb=int(bytes)/1024; request=method+" "+path' \
|lgx group ip request \
|lgx geval 'count=len(_line); max_response_size_kb=max(res_size_kb)' \
|lgx where 'count>1' \
|lgx sort -count \
|lgx table ip request max_response_size_kb count
```

## Visualize Data with Graphs

### Count by HTTP Status

Create a bar chart showing the count of requests per HTTP status code:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx group status \
|lgx geval 'count=len(_line)' \
|lgx graph status count
```

### Response Size and Count by Status

Visualize both the maximum response size and count per HTTP status code:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'res_size_kb=int(bytes)/1024' \
|lgx group status \
|lgx geval 'count=len(_line); max_response_size_kb=max(res_size_kb)' \
|lgx graph status max_response_size_kb,count
```

### Multi-dimensional Analysis

Analyze data by both request type and status code:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'res_size_kb=int(bytes)/1024; request=method+" "+path' \
|lgx group request status \
|lgx geval 'count=len(_line); max_response_size_kb=max(res_size_kb)' \
|lgx where 'count>1' \
|lgx sort -count \
|lgx graph request,status max_response_size_kb,count
```

## Enrich Data with External Sources

### Convert CSV to JSON for Lookup

To enrich your log data with server names from an external source, you can use the `lookup` command. First, convert the CSV file containing IP-to-server mappings into JSON format:

```shell
cat ip_name.csv \
|lgx rex '"(?P<ip>([^"]+))","(?P<server_name>([^"]+))"' \
|lgx where 'ip!="ip"' \
|lgx fields ip server_name \
|lgx json
```

### Join with Access Log Data

Now you can join this data with your access logs to add server names to your analysis:

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx group ip \
|lgx geval 'count=len(_line)' \
|lgx fields ip count \
|lgx lookup ip 'cat ip_name.csv |lgx rex '\''"(?P<ip>([^"]+))","(?P<server_name>([^"]+))"'\'' |lgx where '\''ip!="ip"'\'' |lgx fields ip server_name |lgx json' \
|lgx eval "server_name=server_name if server_name else 'N/A'" \
|lgx where 'count>1' \
|lgx table
```

This command:
1. Extracts fields from access logs
2. Groups by IP address
3. Counts requests per IP
4. Looks up server names from the CSV file
5. Handles missing server names by replacing them with 'N/A'
6. Filters to show only IPs with multiple requests
7. Displays the results in a table
