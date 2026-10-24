from urllib.parse import urlparse,parse_qs
def is_url(value): return bool(urlparse(value).scheme and urlparse(value).netloc)
def is_spotify_url(value): return 'spotify.com' in value
def is_youtube_playlist(value): return 'youtube.com' in value and 'list=' in value
