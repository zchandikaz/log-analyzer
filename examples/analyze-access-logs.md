# Analyze Access Logs

First I've attached sample access log file, you can find it in the logs folder.

## Extract Fields
Before you do anything, you have to extract the important data from logs. You can use a regex to do it. This follows regex syntaxes that work in python.

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"'
```

## Table

Let's see extracted data as a table

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"'\
|lgx table timestamp method path status bytes
```
## Sort 

Let's sort by method

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"'\
|lgx sort method \
|lgx table timestamp method path status bytes
```

Let's sort by response size descending, But before you sort by a numeric field, make sure to convert into numeric if it is not already

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'bytes=int(bytes)' \
|lgx sort -bytes \
|lgx table timestamp method path status bytes
```

## Create custom fields

I need to group by request. I mean method + path here.
I need to create a one field with name request. We can use eval command for that. 

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'request=method+" "+path' \
|lgx table request
```

## Group

Now I need to see the request count per each request type. You can use group command to do that, once you group, you can use geval command to person actions with grouped values. 

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'request=method+" "+path' \
|lgx group request \
|lgx geval 'count=len(_line)' \
|lgx table request count
```

Now I want to see count per request and ip


```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'request=method+" "+path' \
|lgx group ip request \
|lgx geval 'count=len(_line)' \
|lgx table ip request count
```

I want to see max response size of each as well

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'res_size_kb=int(bytes)/1024; request=method+" "+path' \
|lgx group ip request \
|lgx geval 'count=len(_line); max_response_size_kb=max(res_size_kb)' \
|lgx sort -count \
|lgx table ip request max_response_size_kb count 
```

## Filter using fields

I need to find if we got more than one request from same ip for same request type. We can use where command here.

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

## Generate Graph

Let's turn this in to a bar chart, Let's get count per http status.

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx group status \
|lgx geval 'count=len(_line)' \
|lgx graph status count
```

Let's get the max response size and count per status 

```shell
cat sample_access.log \
|lgx rex '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>GET|POST|PUT|DELETE)\s+(?P<path>[^\s]+)\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<user_agent>[^"]+)"' \
|lgx eval 'res_size_kb=int(bytes)/1024' \
|lgx group status \
|lgx geval 'count=len(_line); max_response_size_kb=max(res_size_kb)' \
|lgx graph status max_response_size_kb,count
```

Let's get the max response size and count per status and request type 

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

## Lookup data

I need to get the server name of ip from another source. We can do that using lookup command. 

But lookup command only need a json. But we have the server names in a csv files. So let's transform the csv file in to a json

```shell
cat ip_name.csv \
|lgx rex '"(?P<ip>([^"]+))","(?P<server_name>([^"]+))"' \
|lgx where 'ip!="ip"' \
|lgx fields ip server_name \
|lgx json
```

Now let's join with our access logs data

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

