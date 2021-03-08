from datetime import datetime, timedelta, timezone
import time
import string

"""
print(string)
now = datetime.now()
print("now", now)
seconds = 10
then = datetime(year=2022, month=1, day=1)
seconds_to_2021 = (then - now).total_seconds()
adding_again = timedelta(seconds=seconds_to_2021)
print("New year date", now + adding_again)
"""
"""
now = datetime.now()
print("Now ",now)
then = now  + timedelta(hours=1)
print("Then ",then)

print(now>then)
"""


print(datetime.now() + timedelta(seconds=1615152699 - datetime.now().timestamp()))
