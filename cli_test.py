from model import Event
from util import avg_created_diff
from datetime import datetime, timedelta


nowtime = datetime.now()

event_list = [
    Event(created_at=nowtime - timedelta(seconds=5)),
    Event(created_at=nowtime - timedelta(seconds=6)),
    Event(created_at=nowtime - timedelta(seconds=7)),
    Event(created_at=nowtime - timedelta(seconds=8)),
    Event(created_at=nowtime - timedelta(seconds=10)),
    Event(created_at=nowtime - timedelta(seconds=12)),
    Event(created_at=nowtime - timedelta(seconds=14)),
]

print(avg_created_diff(event_list))
