# discord bot that play music when /play command is used
import asyncio
import importlib
import os
import random
import urllib
from typing import List
import bs4

import discord
import requests as requests
from discord.ext import commands
from discord.utils import get
import youtube_dl
# import ffmpeg
import ffmpeg

last_user = None
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)
token = ''
queuelist = []
message = None
commands = {
    'ping': 'Replies with "pong"',
    'play': 'Plays a song',
    'stop': 'Stops playing music',
}


@bot.event
async def on_ready():
    print('Bot is ready.')

#read token from file token.txt
with open('token.txt', 'r') as f:
    token = f.read()


@bot.command(desctiption='This command plays music', response_timeout=60, )
async def play(ctx, url: str):
    user = ctx.author
    global last_user
    last_user = user
    voice_channel = user.voice.channel
    # if url is not a url, search youtube
    voiceChannel = voice_channel
    if voiceChannel is not None and (ctx.voice_client is None or ctx.voice_client.channel != voiceChannel):
        await voiceChannel.connect()
    voice = get(bot.voice_clients, guild=ctx.guild)
    searching_message = await ctx.respond('searching..', delete_after=5)
    if not url.startswith('http'):
        url = search_youtube(url)
    if is_playlist(url):
        video_urls = get_videos_from_playlist(url)
        for video_url in video_urls:
            queuelist.append(video_url)
        await ctx.respond(content=f'Added playlist to queue fist element of playlist is {video_urls[0]}',
                          delete_after=5)
    else:
        # get name of song
        ydl = youtube_dl.YoutubeDL()
        info = ydl.extract_info(url, download=False)
        title = info['title']
        await ctx.respond(content=f'searching..done found {title} at {url}', delete_after=5)
        queuelist.append(url)
    # get name of song if
    if not voice.is_playing():
        url = queuelist.pop(0)
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            audio_data = ydl.extract_info(url, download=False)
        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(audio_data['url'])))
        voice.source = discord.PCMVolumeTransformer(voice.source)
        voice.source.volume = 0.07

        embed = discord.Embed(title="Now Playing:", description=audio_data['title'], color=0x00ff00)
        embed.set_thumbnail(url=audio_data['thumbnail'])
        embed.add_field(name="Controls:", value="[Play/Pause] [Skip] [Stop]", inline=False)
        global message
        # Send the embed message only if the message is not already sent
        if message is None:
            message = await ctx.send(embed=embed)
            # Add reactions to the message for the button controls
            await message.add_reaction("▶️")  # Play/Pause button
            await message.add_reaction("⏭️")  # Skip button
            await message.add_reaction("⏹️")  # Stop button
        else:
            await message.edit(embed=embed)
            # move message to bottom of chat
            await message.delete()
            message = await ctx.send(embed=embed)
            # Add reactions to the message for the button controls
            await message.add_reaction("▶️")  # Play/Pause button
            await message.add_reaction("⏭️")  # Skip button
            await message.add_reaction("⏹️")  # Stop button

        @bot.event
        async def on_reaction_add(reaction, user):
            if user == ctx.author:  # Only consider reactions added by the user who sent the command
                if str(reaction.emoji) == "▶️":  # Play/Pause button
                    # Implement the play/pause functionality here
                    if voice.is_paused():
                        voice.resume()
                    else:
                        voice.pause()

                    print("Play/Pause")
                    pass
                elif str(reaction.emoji) == "⏭️":  # Skip button
                    # Implement the skip functionality here7
                    await skip(ctx)
                    print("Skip")
                    pass
                elif str(reaction.emoji) == "⏹️":  # Stop button
                    # Implement the stop functionality here
                    await stop(ctx)
                    print("Stop")
                    pass

        print('[log] Play command executed successfully')


@bot.event
async def on_player_finished(voice_client, server):
    # If the queue is not empty, play the next video in the queue
    try:
        url = queuelist.pop(0)
    except IndexError:
        url = None
    if url is not None:
        # check if the bot is still connected to the right channel from the last user
        if voice_client.channel != last_user.voice.channel or not voice_client.is_connected():
            voice_client = await last_user.voice.channel.connect()
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        global message
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            audio_data = ydl.extract_info(url, download=False)
            # edit the embed message
            embed = discord.Embed(title="Now Playing:", description=audio_data['title'], color=0x00ff00)
            embed.set_thumbnail(url=audio_data['thumbnail'])
            embed.add_field(name="Controls:", value="[Play/Pause] [Skip] [Stop]", inline=False)
            message =await message.edit(embed=embed)
            voice = voice_client
            voice.play(discord.FFmpegPCMAudio(audio_data['url']))
    else:
        await voice_client.disconnect()
        # edit the embed message to show that the queue is empty
        embed = discord.Embed(title="Now Playing:", description="Queue is empty", color=0x00ff00)
        embed.add_field(name="Controls:", value="[Play/Pause] [Skip] [Stop]", inline=False)

        message=await message.edit(embed=embed)  # Stop button


def search_youtube(query):
    # Encode the search query to make it URL-friendly search from duckduckgo youtube query
    query_string = urllib.parse.urlencode({"search_query": "youtube " + query})
    # Construct the duckduckgo URL post request to https://html.duckduckgo.com/html/
    post_body = "q=" + query_string + "&b="
    # Send the request to duckduckgo and get the response
    response = requests.post("https://html.duckduckgo.com/html/", data=post_body, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 12; rv:102.0) Gecko/20100101 Firefox/102.0',
        "Content-Type": "application/x-www-form-urlencoded"})
    # Find the first link that starts with /url?q=https://www.youtube.com/watch
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    search_results = soup.find_all('a', href=True, class_='result__a')
    for result in search_results:

        if result['href'].startswith("https://www.youtube.com/watch"):
            # Extract the URL from the attribute value
            # Decode the URL-encoded characters in the URL
            # check if the URL is valid
            try:
                youtube_dl.YoutubeDL({}).extract_info(result['href'], download=False)
                return result['href']
            except:
                pass
    # Send a GET request to the search URL and extract the HTML page
    # Return None if no URL is found
    return None


# Define a function that checks if a YouTube video is a playlist
def is_playlist(url):
    # Use youtube_dl to extract the video info
    ydl = youtube_dl.YoutubeDL()
    try:
        info = ydl.extract_info(url, download=False)
        return 'entries' in info
    except:
        return False


def get_videos_from_playlist(url):
    # Use youtube_dl to extract the playlist info
    ydl = youtube_dl.YoutubeDL()
    playlist_info = ydl.extract_info(url, download=False)
    # Extract the URLs of the videos in the queue
    video_urls = [video['webpage_url'] for video in playlist_info['entries']]
    # Return the list of video URLs
    return video_urls


# skip command
@bot.command(description='This command skips the current song')
async def skip(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
        await ctx.respond('Skipped the song')
        await on_player_finished(voice, ctx.guild)
        # move message to bottom of chat
        global message
        # extrac embed from message
        embed = message.embeds[-1]
        await message.delete()
        message = await ctx.send(embed=embed)

    else:
        await ctx.respond('No music playing currently')

# stop command
@bot.command(description='This command stops the music and clears the queue')
async def stop(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    voice.stop()
    await ctx.respond('Stopped the music and cleared the queue')
    # move message to bottom of chat
    global message
    # extrac embed from message
    await message.delete()
    queuelist.clear()

# pause command
@bot.command(description='This command pauses the music')
async def pause(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.respond('Paused the music', delete_after=5)
    else:
        await ctx.respond('No music playing currently', delete_after=5)

# resume command
@bot.command(description='This command resumes the music')
async def resume(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
        await ctx.respond('Resumed the music', delete_after=5)
    else:
        await ctx.respond('Music is not paused', delete_after=5)

# queue command
@bot.command(description='This command shows the current queue')
async def queue(ctx):
    global queuelist
    if len(queuelist) == 0:
        await ctx.respond('Queue is empty', delete_after=5)
    else:
        # create embed message
        embed = discord.Embed(title="Queue:", description=" ", color=0x00ff00)
        # add all songs to embed message
        for song in queuelist:
            embed.add_field(name=" ", value=song, inline=False)
        await ctx.respond(embed=embed, delete_after=20)


# Define an event handler for the 'on_ready' event
if __name__ == '__main__':
    bot.run(token)
