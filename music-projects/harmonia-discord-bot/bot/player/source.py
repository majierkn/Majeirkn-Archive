import discord

def build_ffmpeg_options(volume=1.0, seek_seconds=0, filter_chain=None):
    before='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    if seek_seconds: before=f'-ss {seek_seconds} '+before
    filters=f'volume={volume:.2f}'+(','+filter_chain if filter_chain else '')
    return {'before_options':before,'options':f'-vn -filter:a "{filters}"'}
class MusicSource(discord.PCMVolumeTransformer):
    @classmethod
    async def create(cls, stream_url, volume=80, seek_seconds=0, filter_chain=None, executable='ffmpeg'):
        opts=build_ffmpeg_options(volume/100,seek_seconds,filter_chain); src=discord.FFmpegOpusAudio(stream_url,executable=executable,**opts); return cls(src,volume=volume/100)
