from urllib.parse import urlparse
def is_spotify_url(value): return urlparse(value).netloc.endswith('spotify.com')
async def resolve_spotify_to_query(value): raise ValueError('Links Spotify exigem resolução item a item; use o nome da música.')
