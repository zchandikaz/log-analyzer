# Analyze Java Logs

A sample Java application log file is provided in the logs folder for you to work with.

## Extract Fields
Before analyzing logs, you need to extract the important data from them. You can use a regular expression (regex) to parse the log entries. The following examples use regex syntax compatible with Python:

```shell
cat sample_java_app.log \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>.+)'
```

## Handle Multiline Logs

Java logs often contain exception stacktraces that span multiple lines. Although these appear as separate lines in the log file, they should be treated as part of a single log entry. You can use the `mul` command to handle multiline logs properly.

When using the `rex` command after `mul`, you need to specify the input field using the `-i` parameter since you're no longer parsing raw lines:

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line
```

## Filter Logs 

### Filter by Log Level

You can filter logs to show only entries with a specific log level, such as INFO:

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx where 'level=="INFO"'
```

### Filter Logs with Stacktraces

To focus on error logs that include stacktraces:

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx where 'stacktrace!=""'
```

## Group Logs by Similarity

### Identify Similar Log Patterns

When analyzing large log files, it's helpful to group similar log entries. To do this effectively, consider both the message and stacktrace by concatenating them:

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx eval 'full_msg=message + (("\n" + stacktrace) if stacktrace!="" else "")' \
|lgx cluster full_msg -t=0.9
```

### Count Similar Log Types

To get a count of each similar log type and focus on the most frequent patterns:

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

## Convert Timestamps to Different Timezones

If your log timestamps are in UTC and you want to view them in a different timezone (such as IST, which is UTC+5:30):

```shell
cat sample_java_app.log \
|lgx mul '^\d{4}-\d{2}-\d{2}.*' \
|lgx rex '(?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2})\s(?P<level>\w+)\s\[(?P<thread>[^\]]+)\]\s-\s(?P<message>[^\n]+)(?P<stacktrace>(?:\n\t.*)*)?' -i=_line \
|lgx eval "date_time_ist=strftime(strptime(date+' '+time)+5.5*60*60*1000)" \
|lgx table date_time_ist message
```
