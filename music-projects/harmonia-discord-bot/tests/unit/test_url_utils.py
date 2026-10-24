from bot.utils.url_utils import is_url,is_spotify_url,is_youtube_playlist
def test_urls(): assert is_url('https://youtube.com/watch?v=x'); assert is_spotify_url('https://open.spotify.com/track/x'); assert is_youtube_playlist('https://youtube.com/playlist?list=x')
