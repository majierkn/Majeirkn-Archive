from bot.core.cache import TTLCache
def test_cache(): c=TTLCache(1,100); c.set('a',1); assert c.get('a')==1; c.set('b',2); assert c.get('a') is None
