def parse_duration(value):
    if isinstance(value,int): return value
    parts=[int(x) for x in str(value).split(':')]
    if len(parts)==1:return parts[0]
    if len(parts)==2:return parts[0]*60+parts[1]
    return parts[-1]+parts[-2]*60+parts[-3]*3600
def format_duration(seconds):
    h,r=divmod(int(seconds),3600); m,s=divmod(r,60); return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
def format_timestamp(seconds): return format_duration(seconds)
