# discord bot that play music when /play command is used
import discord
from discord.utils import get
import youtube_dl
from youtube_search import YoutubeSearch as ytSearch

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
ytdl = youtube_dl.YoutubeDL(ydl_opts)

successColor = 0x00ff00
errorColor = 0xff0000

queueOfGuilds = {}
playerMessagesOfGuilds = {}
logs = open('logs.txt', 'w', encoding='utf-8')


def printOn(out: str):
    print(out)
    # rout = out + '\n'
    # logs.write(rout)


async def inputC():
    command_input = input()
    if command_input == 'list':
        for guild in queueOfGuilds.keys():
            queue = queueOfGuilds[guild]
            for video in queue:
                print(video['title'])
    return command_input


async def CLI():
    command_input = ""
    while command_input != 'exit':
        print('Command: ')
        command_input = await inputC()


@bot.event
async def on_ready():
    printOn('Bot is ready.')


@bot.command(desctiption='This command plays music', response_timeout=60)
async def play(ctx, query: str):
    printOn(f"[/play][{ctx.guild}] : {query}")
    if ctx.author.voice.channel is not None:
        await ctx.respond(embed=buildRespondEmbed("Searching"), delete_after=5)
        await playCommand(ctx=ctx, query=query)
    else:
        await ctx.respond(embed=buildErrorEmbed("You must be connected to a voice channel"), delete_after=5)


# skip command
@bot.command(description='This command skips the current song')
async def skip(ctx):
    printOn(f"[/skip][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildRespondEmbed("Skipping track"), delete_after=5)
        stopPlayer(ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


# stop command
@bot.command(description='This command stops the music and clears the queue')
async def stop(ctx):
    printOn(f"[/stop][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildRespondEmbed("Stopping player"), delete_after=5)
        await stopCommand(guild=ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


# pause command
@bot.command(description='This command pauses the music')
async def pause(ctx):
    printOn(f"[/pause][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildRespondEmbed("Pausing player"), delete_after=5)
        pauseCommand(guild=ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


@bot.command(description='This command resumes the music')
async def resume(ctx):
    printOn(f"[/resume][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildRespondEmbed("Resuming player"), delete_after=5)
        resumeCommand(guild=ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


# queue command
@bot.command(description='This command shows the current queue')
async def queue(ctx):
    printOn(f"[/queue][{ctx.guild}]")
    await queueCommand(ctx=ctx)


@bot.command(description='This command moves tracks position in queue')
async def move(ctx, from_pos: int, to_pos: int):
    printOn(f"[/move][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        embed = moveCommand(guild=ctx.guild, ind_from=from_pos, ind_to=to_pos)
        await ctx.respond(embed=embed, delete_after=10)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


@bot.command(description='This command disconnects bot from voice channel')
async def disconnect(ctx):
    printOn(f"[/disconnect][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await disconnectCommand(guild=ctx.guild)
        await ctx.respond(embed=buildRespondEmbed("Bye Bye 👋🏼"), delete_after=10)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


@bot.command(description='This command connects bot to your voice channel')
async def join(ctx):
    printOn(f"[/join][{ctx.guild}]")
    embed = await tryConnect(ctx=ctx)
    await ctx.respond(embed=embed, delete_after=10)


@bot.command(description='This command removes a track from queue')
async def remove(ctx, pos: int):
    printOn(f"[/remove][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        embed = removeCommand(guild=ctx.guild, pos=pos)
        await ctx.respond(embed=embed, delete_after=10)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


@bot.command(description="This command clears the queue")
async def clear(ctx):
    printOn(f"[/clear][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        embed = cleanQueue(guild=ctx.guild)
        await ctx.respond(embed=embed, delete_after=10)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


@bot.event
async def on_reaction_add(reaction, user):
    if checkOwnership(guild=reaction.message.guild, author=user):
        await handleCommand(reaction, user)


@bot.event
async def on_reaction_remove(reaction, user):
    if checkOwnership(guild=reaction.message.guild, author=user):
        await handleCommand(reaction, user)


@bot.event
async def on_voice_state_update(member, before, after):
    voice = get(bot.voice_clients, guild=member.guild)
    if voice is not None:
        if before.channel == voice.channel and after.channel is None:
            if len(voice.channel.voice_states) == 1:
                if botId in voice.channel.voice_states:
                    await disconnectCommand(member.guild)


def checkOwnership(guild, author):
    voice = get(bot.voice_clients, guild=guild)
    if voice is not None:
        if voice.channel == author.voice.channel:
            return True
    return False


async def playCommand(ctx, query):
    printOn(f"[playCommand][{ctx.guild}]")
    await tryConnect(ctx=ctx)
    videoDataList = getVideoData(query=query)
    if videoDataList is not None:
        for video in videoDataList:
            video['requestedBy'] = f"<@{ctx.author.id}>"
        embed = updateQueue(guild=ctx.guild, videoDataList=videoDataList)
        await ctx.respond(embed=embed, delete_after=15)
        voice = get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            if voice.is_paused():
                resumePlayer(guild=ctx.guild)
        else:
            videoTrack = popVideoTrack(guild=ctx.guild)
            if videoTrack is not None:
                playPlayer(guild=ctx.guild, video_data=videoTrack)
                await updatePlayerMessage(guild=ctx.guild, video_data=videoTrack, channelId=ctx.channel_id)
            else:
                printOn(f"    [playCommand][{ctx.guild}] : Get None VideoTrack")
    else:
        printOn(f"    [playCommand][{ctx.guild}] : VideoData not found")


async def skipCommand(guild):
    printOn(f"[skipCommand][{guild}]")
    voice = get(bot.voice_clients, guild=guild)
    if voice.is_playing:
        stopPlayer(guild=guild)
    else:
        printOn(f"    [skipCommand][{guild}] : Already stopped")


def songEnd(guild):
    printOn(f"[/songEnd][{guild}]")
    bot.loop.create_task(onSongEnd(guild=guild))
    pass


async def onSongEnd(guild):
    if isQueueEmpty(guild=guild):
        await deletePlayerMessage(guild=guild)
    else:
        videoTrack = popVideoTrack(guild=guild)
        if videoTrack is not None:
            playPlayer(guild=guild, video_data=videoTrack)
            try:
                message = playerMessagesOfGuilds[guild]
                await updatePlayerMessage(guild=guild, video_data=videoTrack, channelId=message.channel.id)
            except KeyError:
                printOn(f"    [skipCommand][{guild}] : Unable to update player, playerMessage not found")
        else:
            printOn(f"    [skipCommand][{guild}] : Get None VideoTrack")


async def stopCommand(guild):
    printOn(f"[stopCommand][{guild}]")
    stopPlayer(guild=guild)
    cleanQueue(guild=guild)
    await deletePlayerMessage(guild=guild)


def pauseCommand(guild):
    printOn(f"[pauseCommand][{guild}]")
    voice = get(bot.voice_clients, guild=guild)
    if not voice.is_paused():
        pausePlayer(guild=guild)


def resumeCommand(guild):
    printOn(f"[resumeCommand][{guild}]")
    voice = get(bot.voice_clients, guild=guild)
    if voice.is_paused():
        resumePlayer(guild)


def removeCommand(guild, pos):
    return removeItemFromQueue(guild=guild, pos=pos)


def moveCommand(guild, ind_from, ind_to):
    return moveItemsOfQueue(guild=guild, ind_from=ind_from, ind_to=ind_to)


async def disconnectCommand(guild):
    await deletePlayerMessage(guild=guild)
    cleanQueue(guild=guild)
    stopPlayer(guild=guild)
    await disconnectVoice(guild=guild)


async def queueCommand(ctx):
    guild_queue = getQueue(guild=ctx.guild)
    embeds = buildQueueEmbeds(guild_queue=guild_queue)
    await ctx.respond(embeds=embeds, delete_after=30)


def popVideoTrack(guild):
    printOn(f"[popVideoTrack][{guild}]")
    try:
        return queueOfGuilds[guild].pop(0)
    except IndexError:
        printOn(f"    [popVideoTrack][{guild}] : QueueEmpty")
    except KeyError:
        printOn(f"    [popVideoTrack][{guild}] : Guild not in dict")
    return None


async def deletePlayerMessage(guild):
    printOn(f"[deletePlayer][{guild}]")
    try:
        await playerMessagesOfGuilds[guild].delete()
    except KeyError:
        printOn(f"    [deletePlayer][{guild}] : Player not in dict")
    except discord.NotFound:
        printOn(f"    [deletePlayer][{guild}] : Player not found")
    except discord.HTTPException:
        printOn(f"    [deletePlayer][{guild}] : HttpException")


def playPlayer(guild, video_data):
    printOn(f"[playPlayer][{guild}]")
    try:
        voice = get(bot.voice_clients, guild=guild)
        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(video_data['url'])),
                   after=lambda e: songEnd(guild))
        voice.source = discord.PCMVolumeTransformer(voice.source, volume=0.07)
    except discord.ClientException:
        printOn(f"    [playPlayer][{guild}] : Already playing audio or not connected")
    except TypeError:
        printOn(f"    [playPlayer][{guild}] : Source is not a AudioSource or 'after' is not a callable")
    except:
        printOn(f"    [playPlayer][{guild}] : Other Exception")
    pass


async def updatePlayerMessage(guild, video_data, channelId):
    printOn(f"[updatePlayerMessage][{guild}]")
    await deletePlayerMessage(guild)
    try:
        message = await bot.get_channel(channelId).send(embed=buildPlayerEmbeds(video_data))
        await message.add_reaction("⏸")
        await message.add_reaction("▶️")  # Play/Pause button
        await message.add_reaction("⏭️")  # Skip button
        await message.add_reaction("⏹️")  # Stop button
        playerMessagesOfGuilds[guild] = message
    except:
        pass


async def tryConnect(ctx):
    printOn(f"[tryConnect][{ctx.guild}]")
    try:
        await ctx.author.voice.channel.connect()
        return buildRespondEmbed("Hello 👋🏼")
    except discord.ClientException:
        printOn(f"    [tryConnect][{ctx.guild}] : Already in this voice channel")
        return buildErrorEmbed("I'm already here 🙌🏼")
    except AttributeError:
        printOn(f"    [tryConnect][{ctx.guild}] : Voice channel not existing")
        return buildErrorEmbed("You must be connected to a voice channel")


def getVideoData(query):
    if not query.startswith('http'):
        return [search_youtube(query)]
    else:
        try:
            return is_playlist(query)
        except youtube_dl.utils.DownloadError as etc:
            if etc.args[0].__contains__("ERROR: Incomplete YouTube ID"):
                return None
    return None


def updateQueue(guild, videoDataList):
    printOn(f"[udpateQueue][{guild}]")
    tempQueue = []
    try:
        tempQueue = queueOfGuilds[guild]
    except KeyError:
        printOn(f"    [udpateQueue][{guild}] : Queue not in dict")

    tempQueue.extend(videoDataList)
    queueOfGuilds[guild] = tempQueue

    if len(videoDataList) > 1:
        printOn(f"    [updateQueue][{guild}] : playlist added")
        embed = buildQueuePlaylistAddEmbed(videoDataList)
    else:
        printOn(f"    [updateQueue][{guild}] : song added")
        embed = buildQueueSongAddEmbed(videoDataList[0])
    return embed


def resumePlayer(guild):
    printOn(f"[resumePlayer][{guild}]")
    try:
        voice = get(bot.voice_clients, guild=guild)
        voice.resume()
    except:
        printOn(f"    [resumePlayer][{guild}] : Generic error while resuming")
    pass


def stopPlayer(guild):
    printOn(f"[stopPlayer][{guild}]")
    try:
        voice = get(bot.voice_clients, guild=guild)
        voice.stop()
    except:
        printOn(f"    [stopPlayer][{guild}] : Generic error while stopping")
    pass


def cleanQueue(guild):
    printOn(f"[cleanQueue][{guild}]")
    try:
        tempQueue = queueOfGuilds.pop(guild)
        del tempQueue
        return buildRespondEmbed("Queue cleared")
    except KeyError:
        printOn(f"    [cleanQueue][{guild}] : Queue already cleaned")
        return buildErrorEmbed("Queue already empty")


def pausePlayer(guild):
    printOn(f"[pausePlayer][{guild}]")
    try:
        voice = get(bot.voice_clients, guild=guild)
        voice.pause()
    except:
        printOn(f"    [pausePlayer][{guild}] : Generic error while pausing")
    pass


def removeItemFromQueue(guild, pos: int):
    printOn(f"[removeItemsOfQueue][{guild}]")
    try:
        queue = queueOfGuilds[guild]
        if 1 <= pos <= len(queue):
            videotrack = queue.pop(pos - 1)
            embed = discord.Embed(title="Removed",
                                  description=f"[{videotrack['title']}]({videotrack['webpage_url']})",
                                  color=successColor)
            embed.set_thumbnail(url=videotrack['thumbnail'])
            return embed
        else:
            printOn(f"  [removeItemsOfQueue][{guild}] : Out of queue bounds")
            return buildErrorEmbed("Position out of queue bounds")
    except KeyError:
        printOn(f"  [removeItemsOfQueue][{guild}] : Queue not in dict")
        return buildErrorEmbed("Error while removing")


def moveItemsOfQueue(guild, ind_from: int, ind_to: int):
    printOn(f"[moveItemsOfQueue][{guild}]")
    try:
        queue = queueOfGuilds[guild]
        if len(queue) >= ind_to >= 1 and len(queue) >= ind_from >= 1 and ind_to != ind_from:
            videoTrack = queue.pop(ind_from - 1)
            queue.insert(ind_to - 1, videoTrack)
            queueOfGuilds[guild] = queue
            embed = discord.Embed(title="Moved",
                                  description=f"[{videoTrack['title']}]({videoTrack['webpage_url']})",
                                  color=successColor)
            embed.set_thumbnail(url=videoTrack['thumbnail'])
            embed.add_field(name="From", value=f"{ind_from}")
            embed.add_field(name="To", value=f"{ind_to}")
            return embed
        else:
            printOn(f"   [moveItemsOfQueue][{guild}] : Valori sbagliati")
            return buildErrorEmbed("Indexes out of queue bounds")
    except Exception as e:
        print(e)
        printOn(f"   [moveItemsOfQueue][{guild}] : Errore generico")
    return buildErrorEmbed("Error while moving")


async def disconnectVoice(guild):
    printOn(f"[disconnectVoice][{guild}]")
    try:
        voice = get(bot.voice_clients, guild=guild)
        await voice.disconnect(force=True)
    except:
        printOn(f"    [disconnectVoice][{guild}] : Generic error while disconnecting")
    pass


def getQueue(guild):
    printOn(f"[getQueue][{guild}]")
    try:
        return queueOfGuilds[guild]
    except KeyError:
        printOn(f"    [getQueue][{guild}] : Queue not exists")
        return []


def isQueueEmpty(guild):
    printOn(f"[isQueueEmpty][{guild}]")
    try:
        tempQueue = queueOfGuilds[guild]
        return len(tempQueue) == 0
    except KeyError:
        printOn(f"    [isQueueEmpty][{guild}] : Queue not in dict")
    return True


async def handleCommand(reaction, user):
    guild = reaction.message.guild
    if user.id != botId:  # Only consider reactions added by the user who sent the command
        if str(reaction.emoji) == "▶️":  # Play/Pause button
            resumeCommand(guild)
        elif str(reaction.emoji) == "⏸":
            pauseCommand(guild)
        elif str(reaction.emoji) == "⏭️":  # Skip button
            # Implement the skip functionality here7
            await skipCommand(guild)
            pass
        elif str(reaction.emoji) == "⏹️":  # Stop button
            # Implement the stop functionality here
            await stopCommand(guild)
            pass


def buildErrorEmbed(errorMessage):
    return discord.Embed(title="Error", colour=errorColor, description=errorMessage)


def buildRespondEmbed(respondMessage):
    return discord.Embed(title=respondMessage, colour=successColor)


def buildQueuePlaylistAddEmbed(video_datas):
    i = 1
    embed = discord.Embed(title=f"Added {len(video_datas)} to queue", color=successColor)
    for video_data in video_datas:
        videoSecPrefix = ""
        if video_data['duration'] % 60 < 10:
            videoSecPrefix = '0'
        embed.add_field(name=f"{i} - {video_data['title']}",
                        value=f"[Duration: {int(video_data['duration'] / 60)}:{videoSecPrefix}{video_data['duration'] % 60}]({video_data['webpage_url']})",
                        inline=False)
        i += 1
    return embed


def buildQueueEmbeds(guild_queue):
    if len(guild_queue) > 0:
        nextTrack = guild_queue[0]
        videoSecPrefix = ""
        if nextTrack['duration'] % 60 < 10:
            videoSecPrefix = '0'
        nextTrackEmbed = discord.Embed(title="Next track:",
                                       description=f"[{nextTrack['title']}]({nextTrack['webpage_url']})",
                                       color=0x00ff00)
        nextTrackEmbed.add_field(name='Duration',
                                 value=f"{int(nextTrack['duration'] / 60)}:{videoSecPrefix}{nextTrack['duration'] % 60}")
        nextTrackEmbed.add_field(name='Requested by',
                                 value=f"{nextTrack['requestedBy']}")
        nextTrackEmbed.set_thumbnail(url=nextTrack["thumbnail"])

        if len(guild_queue) > 1:
            embed = discord.Embed(title=f"There are {len(guild_queue)} more elements in queue",
                                  color=successColor)
            for ind in range(1, len(guild_queue)):
                videoSecPrefix = ""
                if guild_queue[ind]['duration'] % 60 < 10:
                    videoSecPrefix = '0'
                embed.add_field(name=f"{ind + 1}° - {guild_queue[ind]['title']}",
                                value=f"[Duration: {int(guild_queue[ind]['duration'] / 60)}:{videoSecPrefix}{guild_queue[ind]['duration'] % 60}]({guild_queue[ind]['webpage_url']})\n"
                                      f"Requested by : {guild_queue[ind]['requestedBy']}",
                                inline=False)
            return [nextTrackEmbed, embed]
        return [nextTrackEmbed]
    else:
        return [discord.Embed(title="Queue is empty", color=successColor)]


def buildQueueSongAddEmbed(video_data):
    embed = discord.Embed(title=f"Add video to queue",
                          description='[' + video_data['title'] + '](' + video_data['webpage_url'] + ')',
                          color=successColor)
    embed.add_field(name="Requested by", value=video_data['requestedBy'])
    videoSecPrefix = ""
    if video_data['duration'] % 60 < 10:
        videoSecPrefix = '0'
    embed.add_field(name="Duration",
                    value=f"{int(video_data['duration']/60)}:{videoSecPrefix}{video_data['duration']%60}")
    embed.set_thumbnail(url=video_data['thumbnail'])
    return embed


def buildPlayerEmbeds(video_data):
    embed = discord.Embed(description=f"[{video_data['title']}]({video_data['webpage_url']})", color=0x00ff00)
    embed.set_author(name="Now Playing:",
                     icon_url="https://images-ext-1.discordapp.net/external/hC4kckSAAbI8WbaB8ROQkTV4"
                              "-7qxwK8GDg8PqGTK0aI/https/media.tenor.com/IAWKXaW_52sAAAAd/rickroll.gif")
    embed.set_thumbnail(url=video_data['thumbnail'])
    embed.add_field(name="Requested by", value=video_data['requestedBy'])
    videoSecPrefix = ""
    if video_data['duration'] % 60 < 10:
        videoSecPrefix = '0'
    embed.add_field(name="Duration",
                    value=f"{int(video_data['duration'] / 60)}:{videoSecPrefix}{video_data['duration'] % 60}")
    embed.add_field(name="Controls:", value="[Pause] [Play] [Skip] [Stop]", inline=False)
    return embed


def buildNotOwnerEmbed():
    return buildErrorEmbed("You must be connected to the same voice channel to use this command")


def search_youtube(query):
    search_results = ytSearch(query, max_results=5).to_dict()
    for result in search_results:
        if result['url_suffix'].startswith("/watch"):
            # Extract the URL from the attribute value
            # Decode the URL-encoded characters in the URL
            # check if the URL is valid
            try:
                return ytdl.extract_info(f"https://youtube.com/{result['url_suffix']}", download=False)
            except:
                pass
    # Send a GET request to the search URL and extract the HTML page
    # Return None if no URL is found
    return None


# Define a function that checks if a YouTube video is a playlist
def is_playlist(url):
    # Use youtube_dl to extract the video info
    try:
        info = ytdl.extract_info(url, download=False)
        if "entries" in info:
            return info['entries']
        else:
            return [info]
    except:
        printOn("    [isPlaylist] : Error while fetching video_data")
        return None


def get_videos_from_playlist(url):
    # Use youtube_dl to extract the playlist info
    playlist_info = ytdl.extract_info(url, download=False)
    # Extract the URLs of the videos in the queue
    video_urls = [video['webpage_url'] for video in playlist_info['entries']]
    # Return the list of video URLs
    return video_urls


# read token from file token.txt
with open('token.txt', 'r') as f:
    token = f.readline().replace('\n', '')
    t_token = f"***{token[len(token) - 15:len(token)]}"
    printOn(f"This is token : {t_token}")
    botIdStr = f.readline()
    botId = int(botIdStr)
    printOn(f"This is BotId : {botId}")

if __name__ == '__main__':
    bot.run(token)
