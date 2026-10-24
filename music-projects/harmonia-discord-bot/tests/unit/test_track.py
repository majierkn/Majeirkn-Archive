from bot.player.track import Track
def test_track(): t=Track.from_ytdlp_info({'webpage_url':'u','title':'x','duration':62}); assert t.duration_formatted=='1:02'
