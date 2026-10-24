import discord
from bot.core.errors import UserNotInVoiceError
def require_voice(interaction):
    if not isinstance(interaction.user,discord.Member) or not interaction.user.voice: raise UserNotInVoiceError()
    return interaction.user.voice.channel
