from datetime import datetime

start_time = '2023-01-14T23-08-25'
start = datetime.strptime(start_time + ' +0700', '%Y-%m-%dT%H-%M-%S %z')
timestamp_start = datetime.strftime(start, '%Y-%m-%d %H:%M:%S')

print('start_time=', start_time)
print('timestamp_start=', timestamp_start)