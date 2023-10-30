# discord bot that play music when /play command is used

import discord
from discord.utils import get
from youtube_search import YoutubeSearch as ytSearch
import yt_dlp
import requests as rq
import time

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

ytdl = yt_dlp.YoutubeDL(ydl_opts)

successColor = 0x00ff00
errorColor = 0xff0000
infoColor = 0x057cfc

queueOfGuilds = {}
playerMessagesOfGuilds = {}
volumeOfGuilds = {}
logs = open('logs.txt', 'w', encoding='utf-8')


def printOn(out: str):
    timeStr = time.strftime("[%d-%m-%Y, %H:%M:%S]", time.localtime())
    print(f"{timeStr}{out}")
    # rout = out + '\n'
    # logs.write(rout)


async def inputC():
    command_input = input()
    if command_input == 'list':
        for guild in queueOfGuilds.keys():
            queue_list = queueOfGuilds[guild]
            for video in queue_list:
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
    printOn("[cleaning] : start")
    channels = bot.get_all_channels()
    for channel in channels:
        if channel.type.name == 'text':
            printOn(f"[cleaning][{channel.guild}] : {channel.name}")
            number = await cleanMessages(channel)
            printOn(f"      [cleaning][{channel.guild}] : cleaned {number} on {channel.name}")
    printOn("[cleaning] : end")


async def cleanMessages(channel):
    messages = await channel.history(limit=300).flatten()
    i = 0
    for message in messages:
        # if message.clean_content.startswith("/") or message.clean_content.startswith("!") or message.clean_content.startswith(">") or message.clean_content.startswith("\\") or message.clean_content.startswith("."):
        #     i += 1
        #     await message.delete()
        if message.author.id == botId:
            i += 1
            await message.delete()
    return i


@bot.command(desctiption='This command search and add music to queue', response_timeout=60)
async def play(ctx, query: str):
    printOn(f"[/play][{ctx.guild}] : {query}")
    if ctx.author.voice is not None:
        if ctx.author.voice.channel is not None:
            await ctx.respond(embed=buildMessageEmbed("🔎 Searching"), delete_after=5)
            await playCommand(ctx=ctx, query=query)
            return

    await ctx.respond(embed=buildErrorEmbed("You must be connected to a voice channel"), delete_after=5)


@bot.command(description='This command skips the current song')
async def skip(ctx):
    printOn(f"[/skip][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildMessageEmbed("Skipping track"), delete_after=5)
        stopPlayer(ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


# stop command
@bot.command(description='This command stops the music and clears the queue')
async def stop(ctx):
    printOn(f"[/stop][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildMessageEmbed("Stopping player"), delete_after=5)
        await stopCommand(guild=ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


# pause command
@bot.command(description='This command pauses the music')
async def pause(ctx):
    printOn(f"[/pause][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildMessageEmbed("Pausing player"), delete_after=5)
        pauseCommand(guild=ctx.guild)
    else:
        await ctx.respond(embed=buildNotOwnerEmbed(),
                          delete_after=5)


@bot.command(description='This command resumes the music')
async def resume(ctx):
    printOn(f"[/resume][{ctx.guild}]")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        await ctx.respond(embed=buildMessageEmbed("Resuming player"), delete_after=5)
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
        await ctx.respond(embed=buildMessageEmbed("Bye Bye 👋🏼"), delete_after=10)
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


@bot.command(description="This command put music on top of the queue and skip the current song")
async def playnow(ctx, query: str):
    printOn(f"[/playNow][{ctx.guild}] : {query}")
    if ctx.author.voice is not None:
        if ctx.author.voice.channel is not None:
            await ctx.respond(embed=buildMessageEmbed("🔎 Searching"), delete_after=5)
            await playNowCommand(ctx=ctx, query=query)
            return

    await ctx.respond(embed=buildErrorEmbed("You must be connected to a voice channel"), delete_after=5)


@bot.command(description="This command modify the volume of the player, be careful")
async def volume(ctx, val: int):
    printOn(f"[/volume][{ctx.guild}] : {val}")
    if checkOwnership(guild=ctx.guild, author=ctx.author):
        embed = await volumeCommand(ctx.guild, val)
        await ctx.respond(embed=embed, delete_after=5)
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
                    printOn(f'[/aloneInChannel][{member.guild}]')
                    await disconnectCommand(member.guild)


def checkOwnership(guild, author):
    voice = get(bot.voice_clients, guild=guild)
    if voice is not None:
        if voice.channel == author.voice.channel:
            return True
    return False


async def volumeCommand(guild, val):
    if 150 >= val >= 0:
        voice = get(bot.voice_clients, guild=guild)
        if voice is not None:
            if voice.source is not None:
                volumeOfGuilds[guild] = val
                voice.source.volume = (0.002 * val)
                if guild in playerMessagesOfGuilds:
                    message = playerMessagesOfGuilds[guild]
                    embed = message.embeds[0]
                    embed.fields[-1].value = f"`{val}%`"
                    await message.edit(embeds=[embed])
            return buildSuccessEmbed("Volume set for this channel")
        else:
            return buildErrorEmbed("There are no song currently playing")
    else:
        return buildErrorEmbed("Volume must be between 150 and 0")


async def playCommand(ctx, query):
    printOn(f"[playCommand][{ctx.guild}]")
    await tryConnect(ctx=ctx)
    videoDataList = getVideoData(query=query, guildId=ctx.guild.id, authorId=ctx.author.id)
    if videoDataList is not None:
        embed = updateQueue(guild=ctx.guild, videoDataList=videoDataList, onTop=False)
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


async def playNowCommand(ctx, query):
    printOn(f"[playNowCommand][{ctx.guild}]")
    await tryConnect(ctx=ctx)
    videoDataList = getVideoData(query=query, guildId=ctx.guild.id, authorId=ctx.author.id)
    if videoDataList is not None:
        embed = updateQueue(guild=ctx.guild, videoDataList=videoDataList, onTop=True)
        await ctx.respond(embed=embed, delete_after=15)
        voice = get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            await skipCommand(guild=ctx.guild)
        else:
            videoTrack = popVideoTrack(guild=ctx.guild)
            if videoTrack is not None:
                playPlayer(guild=ctx.guild, video_data=videoTrack)
                await updatePlayerMessage(guild=ctx.guild, video_data=videoTrack, channelId=ctx.channel_id)
            else:
                printOn(f"    [playNowCommand][{ctx.guild}] : Get None VideoTrack")
    else:
        printOn(f"    [playNowCommand][{ctx.guild}] : VideoData not found")


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
        volume_val = 0.10
        if guild in volumeOfGuilds:
            volume_val = 0.002 * volumeOfGuilds[guild]
            printOn(f"      [playPlayer][{guild}] : Use set volume : {volume_val}")
        voice = get(bot.voice_clients, guild=guild)
        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(video_data['url'],before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")),
                   after=lambda e: songEnd(guild))
        voice.source = discord.PCMVolumeTransformer(voice.source, volume=volume_val)
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
        volume_val = 50
        if guild in volumeOfGuilds:
            volume_val = volumeOfGuilds[guild]
        message = await bot.get_channel(channelId).send(embed=buildPlayerEmbeds(video_data, int(volume_val)))
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
        return buildMessageEmbed("Hello 👋🏼")
    except discord.ClientException:
        printOn(f"    [tryConnect][{ctx.guild}] : Already in this voice channel")
        return buildMessageEmbed("I'm already here 🙌🏼")
    except AttributeError:
        printOn(f"    [tryConnect][{ctx.guild}] : Voice channel not existing")
        return buildErrorEmbed("You must be connected to a voice channel")


def getVideoData(query, guildId, authorId):
    video_data = None
    if not query.startswith('http'):
        video_data = [search_youtube(query)]
    else:
        try:
            video_data = is_playlist(query)
        except yt_dlp.utils.DownloadError as etc:
            if etc.args[0].__contains__("ERROR: Incomplete YouTube ID"):
                video_data = None

    if video_data is not None:
        for video in video_data:
            if video is not None:
                video['requestedBy'] = authorId
                video['requestedIn'] = guildId
            else:
                video_data.remove(video)
        dataUpload(video_data=video_data)
    if len(video_data) > 0:
        return video_data
    return None


def dataUpload(video_data):
    for video in video_data:
        ris = rq.post(url="http://entir.altervista.org/RadioMom/addRequest.php",
                      data={'guildId': video['requestedIn'], 'authorId': video['requestedBy'], "ytVideoKey": video['id'], "word": dbPassword})
        printOn(ris.text)
        if ris.text.__contains__("KO"):
            printOn(f"[dataUpload] : error while upload")


def updateQueue(guild, videoDataList, onTop: bool):
    printOn(f"[udpateQueue][{guild}]")
    tempQueue = []
    try:
        tempQueue = queueOfGuilds[guild]
    except KeyError:
        printOn(f"    [udpateQueue][{guild}] : Queue not in dict")

    if onTop:
        tempDataList = []
        tempDataList.extend(videoDataList)
        tempDataList.extend(tempQueue)
        tempQueue = tempDataList
    else:
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
        return buildSuccessEmbed("Queue cleared")
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
        queue_list = queueOfGuilds[guild]
        if 1 <= pos <= len(queue_list):
            videoTrack = queue_list.pop(pos - 1)
            embed = discord.Embed(title="Removed",
                                  description=f"[{videoTrack['title']}]({videoTrack['webpage_url']})",
                                  color=successColor)
            embed.set_thumbnail(url=videoTrack['thumbnail'])
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
        queue_list = queueOfGuilds[guild]
        if len(queue_list) >= ind_to >= 1 and len(queue_list) >= ind_from >= 1 and ind_to != ind_from:
            videoTrack = queue_list.pop(ind_from - 1)
            queue_list.insert(ind_to - 1, videoTrack)
            queueOfGuilds[guild] = queue_list
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
        try:
            volumeOfGuilds.pop(guild)
        except KeyError:
            printOn(f"      [disconnectVoice][{guild}] : Set volume to default")
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
    return discord.Embed(title="❗ Error", colour=errorColor, description=errorMessage)


def buildSuccessEmbed(respondMessage):
    return discord.Embed(title="✅", description=respondMessage, colour=successColor)


def buildInfoEmbed(infoMessage):
    return discord.Embed(title="ℹ", description=infoMessage, colour=infoColor)


def buildMessageEmbed(message):
    return discord.Embed(title=message, colour=0xffffff)


def buildQueuePlaylistAddEmbed(video_datas):
    i = 1
    embed = discord.Embed(title=f"Added {len(video_datas)} to queue", color=successColor)
    for video_data in video_datas:
        videoSecPrefix = ""
        if video_data['duration'] % 60 < 10:
            videoSecPrefix = '0'
        embed.add_field(name=f"{i} - {video_data['title']}",
                        value=f">>> `Author: {video_data['channel']}`\n"
                              f"[`Duration: {int(video_data['duration'] / 60)}:{videoSecPrefix}"
                              f"{video_data['duration'] % 60}`]({video_data['webpage_url']})",
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
                                       color=infoColor)
        nextTrackEmbed.add_field(name='Requested by',
                                 value=f"<@{nextTrack['requestedBy']}>")
        nextTrackEmbed.add_field(name="Author", value=f"`{nextTrack['channel']}`")
        nextTrackEmbed.add_field(name='Duration',
                                 value=f"`{int(nextTrack['duration'] / 60)}:{videoSecPrefix}"
                                       f"{nextTrack['duration'] % 60}`")
        nextTrackEmbed.set_thumbnail(url=nextTrack["thumbnail"])

        if len(guild_queue) > 1:
            embed = discord.Embed(title=f"There are {len(guild_queue)-1} more elements in queue",
                                  color=infoColor)
            for ind in range(1, len(guild_queue)):
                videoSecPrefix = ""
                if guild_queue[ind]['duration'] % 60 < 10:
                    videoSecPrefix = '0'
                embed.add_field(name=f"{ind + 1}° - {guild_queue[ind]['title']}",
                                value=f">>> "
                                      f"`Requested by: `<@{guild_queue[ind]['requestedBy']}>\n"
                                      f"`Author: {guild_queue[ind]['channel']}`\n"
                                      f"[`Duration: {int(guild_queue[ind]['duration'] / 60)}:{videoSecPrefix}"
                                      f"{guild_queue[ind]['duration'] % 60}`]({guild_queue[ind]['webpage_url']})",
                                inline=False)
            return [nextTrackEmbed, embed]
        return [nextTrackEmbed]
    else:
        return [buildInfoEmbed("Queue is empty")]


def buildQueueSongAddEmbed(video_data):
    embed = discord.Embed(title=f"Add video to queue",
                          description='[' + video_data['title'] + '](' + video_data['webpage_url'] + ')',
                          color=successColor)
    embed.add_field(name="Requested by", value=f"<@{video_data['requestedBy']}>")
    embed.add_field(name="Author", value=f"`{video_data['channel']}`")
    videoSecPrefix = ""
    if video_data['duration'] % 60 < 10:
        videoSecPrefix = '0'
    embed.add_field(name="Duration",
                    value=f"`{int(video_data['duration'] / 60)}:{videoSecPrefix}{video_data['duration'] % 60}`")
    embed.set_thumbnail(url=video_data['thumbnail'])
    return embed


def buildPlayerEmbeds(video_data, volume_val):
    embed = discord.Embed(title=video_data['title'], url=video_data['webpage_url'], color=infoColor)
    embed.set_author(name="🎵 Now playing:",
                     icon_url="https://images-ext-1.discordapp.net/external/hC4kckSAAbI8WbaB8ROQkTV4"
                              "-7qxwK8GDg8PqGTK0aI/https/media.tenor.com/IAWKXaW_52sAAAAd/rickroll.gif")
    embed.set_thumbnail(url=video_data['thumbnail'])
    embed.add_field(name="❔ Requested by", value=f"<@{video_data['requestedBy']}>", inline=False)
    embed.add_field(name="Author", value=f"`{video_data['channel']}`")
    videoSecPrefix = ""
    if video_data['duration'] % 60 < 10:
        videoSecPrefix = '0'
    embed.add_field(name="🕑 Duration",
                    value=f"`{int(video_data['duration'] / 60)}:{videoSecPrefix}{video_data['duration'] % 60}`")
    embed.add_field(name="🔊 Volume",
                    value=f"`{volume_val}%`")
    return embed


def buildNotOwnerEmbed():
    return buildErrorEmbed("You must be connected to the same voice channel in order to use this command")


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


# read token from file tokenn.txt
with open('token_test.txt', 'r') as f:
    token = f.readline().replace('\n', '')
    t_token = f"***{token[len(token) - 15:len(token)]}"
    printOn(f"This is token : {t_token}")
    botIdStr = f.readline().replace('\n', '')
    botId = int(botIdStr)
    printOn(f"This is BotId : {botId}")
    dbPassword = f.readline().replace('\n', '')
    printOn(f"This is dbPass : *****{dbPassword[len(dbPassword)-5:len(dbPassword)]}")

if __name__ == '__main__':
    bot.run(token)
