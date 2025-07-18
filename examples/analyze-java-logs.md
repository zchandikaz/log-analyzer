# Analyze Java Logs

First I've attached sample access log file, you can find it in the logs folder.

## Extract Fields
Before you do anything, you have to extract the important data from logs. You can use a regex to do it. This follows regex syntaxes that work in python.


```shell
cat sample_java_app.log \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>.+)'
```

## Handle Multiline Logs

You might have noticed exception stacktrace lines are considered as different log lines. But in reality those are part of a single line. We need to correct it. You can do it using mul command.

In rex command, since now we are not parsing a raw line, you have to provide input field using -i param.

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line
```

## Filter logs 

Filter logs by level

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx where 'level=="INFO"'
```

Filter logs with stacktraces

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx where 'stacktrace!=""'
```

## Group logs by similarity

Group similar log, I need to consider both message and stacktrace for this, So I'm concatenating them

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx eval 'full_msg=message + (("\n" + stacktrace) if stacktrace!="" else "")' \
|lgx cluster full_msg -t=0.9
```

Get count of each similar log type and removing extra fields.

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx eval 'full_msg=message + (("\n" + stacktrace) if stacktrace!="" else "")' \
|lgx cluster full_msg -t=0.9 \
|lgx geval 'count=len(_line)' \
|lgx sort -count \
|lgx fields full_msg count
```

## Get the logs in different timezone time

Let's assume time in log in UTC, you want to see them in IST. 

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx eval "date_time_ist=strftime(strptime(date+' '+time)+5.5*60*60*1000)" \
|lgx table date_time_ist message
```