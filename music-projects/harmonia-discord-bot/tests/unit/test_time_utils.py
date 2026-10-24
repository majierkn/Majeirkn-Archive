from bot.utils.time_utils import parse_duration,format_duration
def test_time(): assert parse_duration('1:02:03')==3723; assert format_duration(62)=='1:02'
