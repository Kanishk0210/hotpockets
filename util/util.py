from datetime import datetime
import zulu

def get_current_tmstmp_str():
    return str(zulu.now().format('%Y-%m-%d %H:%M:%S', tz ='local'))

def get_round_off_dur(dur_in_min):
    m = dur_in_min % 5
    if m < 2.5:
        return dur_in_min - m
    return dur_in_min - m + 5

def get_duration(strt: str, end: str, cancel_t):
    s = datetime.strptime(strt, "%Y-%m-%d %H:%M:%S")
    e = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

    dur = e - s
    dur_in_min = (dur.total_seconds()/60) - cancel_t
    round_off_dur = get_round_off_dur(dur_in_min)
    return round_off_dur

# get_duration("2024-08-29 02:00:00", "2024-08-29 03:00:00")