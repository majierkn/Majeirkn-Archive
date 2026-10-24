import discord

def is_admin(interaction): return isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild

def in_voice(interaction): return isinstance(interaction.user, discord.Member) and interaction.user.voice and interaction.user.voice.channel
