import discord
def now_playing(track): return discord.Embed(title='🎵 Tocando agora',description=f'**{track.title}**\n{track.uploader}\n`{track.duration_formatted}`',color=discord.Color.blurple(),url=track.webpage_url)
def queue_embed(player): return discord.Embed(title='📋 Fila',description='\n'.join(f'`{i}.` {t.title}' for i,t in enumerate(player.queue,1)) or 'A fila está vazia.',color=discord.Color.blurple())
