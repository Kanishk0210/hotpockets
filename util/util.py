from datetime import datetime
import zulu
import base64


def get_current_tmstmp_str():
    return str(zulu.now().format('%Y-%m-%d %H:%M:%S', tz ='local'))

def get_round_off_x(dur_in_min):
    m = dur_in_min % 5
    if m < 2.5:
        return dur_in_min - m
    return dur_in_min - m + 5

def get_duration(strt: str, end: str, cancel_t):
    s = datetime.strptime(strt, "%Y-%m-%d %H:%M:%S")
    e = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

    dur = e - s
    dur_in_min = round(dur.total_seconds()/60)
    if dur_in_min<cancel_t:
        dur_in_min = 0
    round_off_dur = get_round_off_x(dur_in_min)
    return round_off_dur

# get_duration("2024-08-29 02:00:00", "2024-08-29 03:00:00")


def encode_pass(pass_str: str):
    sample_string = pass_str
    sample_string_bytes = sample_string.encode("ascii")

    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_string = base64_bytes.decode("ascii")

    return base64_string

def decode_pass(pass_str: str):
    base64_string = pass_str
    base64_bytes = base64_string.encode("ascii")

    sample_string_bytes = base64.b64decode(base64_bytes)
    sample_string = sample_string_bytes.decode("ascii")

    return sample_string
