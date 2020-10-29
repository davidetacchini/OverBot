import time
import platform
import itertools

import distro
import psutil
import pygit2
import discord
from discord.ext import commands


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["pong", "latency"])
    async def ping(self, ctx):
        """Displays the bot's current websocket latency."""
        embed = discord.Embed(color=self.bot.color)
        embed.title = "Pinging..."
        start = time.monotonic()
        msg = await ctx.send(embed=embed)
        embed.title = None
        ack = round((time.monotonic() - start) * 1000)
        embed.add_field(name="Heartbeat", value=f"{self.bot.ping}ms")
        embed.add_field(name="ACK", value=f"{ack}ms")
        await msg.edit(embed=embed)

    @commands.command(aliases=["feed"])
    @commands.cooldown(1, 60.0, commands.BucketType.user)
    async def feedback(self, ctx, *, message: str):
        """Leave a feedback about the bot (you can leave a feedback once a minute)."""
        channel = self.bot.get_channel(self.bot.config.feedback_channel)

        if not channel:
            return

        embed = discord.Embed(color=self.bot.color)
        embed.description = ctx.message.content
        embed.timestamp = ctx.message.created_at
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        await channel.send(embed=embed)
        await ctx.send(
            f"{str(ctx.author)}, your feedback has been successfully sent, thanks!"
        )

    @staticmethod
    def format_commit(commit):
        return f"[`{commit.hex[:6]}`](https://github.com/davidetacchini/overbot/commit/{commit.hex}) {commit.message}"

    def get_latest_commits(self, count=3):
        repo = pygit2.Repository(".git")
        commits = list(
            itertools.islice(
                repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count
            )
        )
        # since the commits are already formatted, just join them to an empty string
        return "".join(self.format_commit(c) for c in commits)

    # Inspired by RoboDanny (Rapptz)
    # https://github.com/Rapptz/RoboDanny/blob/df340e6cd89f32cd1d96a6b86dfb21419308066b/cogs/stats.py#L217
    @commands.command()
    @commands.guild_only()
    async def about(self, ctx):
        """Displays the bot information."""
        async with ctx.typing():
            commits = self.get_latest_commits()
            embed = discord.Embed(color=self.bot.color)
            embed.title = "Official Website"
            embed.description = f"Latest Commits:\n{commits}"
            embed.url = self.bot.config.website
            embed.timestamp = self.bot.timestamp

            owner = self.bot.get_user(self.bot.config.owner_id)

            embed.set_author(
                name=str(owner),
                url=self.bot.config.github["profile"],
                icon_url=owner.avatar_url,
            )

            activity = (
                f"{psutil.cpu_percent()}% CPU\n" f"{psutil.virtual_memory()[2]}% RAM\n"
            )

            os_name = distro.linux_distribution()[0]
            os_version = distro.linux_distribution()[1]
            host = f"{os_name} {os_version}\n" f"Python {platform.python_version()}"

            total_commands = await self.bot.pool.fetchval("SELECT total FROM command;")
            total_members = 0

            text = 0
            voice = 0
            guilds = 0
            for guild in self.bot.guilds:
                guilds += 1
                total_members += guild.member_count
                for channel in guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        text += 1
                    elif isinstance(channel, discord.VoiceChannel):
                        voice += 1

            embed.add_field(name="Activity Monitor", value=activity)
            embed.add_field(name="Host Statistics", value=host)
            embed.add_field(
                name="Channels",
                value=f"{text + voice} total\n{text} text\n{voice} voice",
            )
            embed.add_field(name="Members", value=total_members)
            embed.add_field(name="Servers", value=len(self.bot.guilds))
            embed.add_field(
                name="Shards",
                value=f"{ctx.guild.shard_id + 1}/{self.bot.shard_count}",
            )
            embed.add_field(name="Commands Runned", value=total_commands)
            embed.add_field(name="Lines of code", value=self.bot.total_lines)
            embed.add_field(name="Uptime", value=self.bot.uptime)
            embed.set_footer(
                text=f"Made with discord.py v{discord.__version__}",
                icon_url=self.bot.config.python_logo,
            )
            await ctx.send(embed=embed)

    @staticmethod
    def format_overbot_status(n, s):
        status = s.lower()
        if status == "operational":
            return f"<:online:648186001361076243> {n}: {s}"
        elif status == "under maintenance":
            return f":tools: {n}: {s}"
        elif status == "degraded Performance" or status == "partial outage":
            return f"<:idle:648185977717915650> {n}: {s}"
        return f"<:dnd:648185968209428490> {n}: {s}"

    @staticmethod
    def format_overwatch_status(s):
        if s == "No problems at Overwatch":
            return f"<:online:648186001361076243> {s}"
        return f"<:dnd:648185968209428490> {s}"

    @commands.command()
    @commands.cooldown(1, 60.0, commands.BucketType.user)
    async def status(self, ctx):
        """Returns both OverBot and Overwatch servers status."""
        embed = discord.Embed(color=discord.Color.blue())
        embed.title = "Status"
        embed.timestamp = self.bot.timestamp
        try:
            overwatch = await self.bot.get_overwatch_status()
            names, statuses = await self.bot.get_overbot_status()
        except Exception:
            embed.description = (
                f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
            )
        else:
            embed.description = f'[Overwatch]({self.bot.config.overwatch["status"]}) · [OverBot](https://overbot.statuspage.io/)'
            fmt = ""
            for name, status in zip(names, statuses):
                fmt += f"{self.format_overbot_status(str(name).strip(), str(status).strip())}\n"
            embed.add_field(name="OverBot", value=fmt)
            embed.add_field(
                name="Overwatch",
                value=self.format_overwatch_status(str(overwatch).strip()),
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def news(self, ctx):
        """Returns the latest Overwatch news."""
        async with ctx.typing():
            pages = []
            try:
                titles, links, imgs, dates = await self.bot.get_overwatch_news()
            except Exception:
                embed = discord.Embed(color=self.bot.color)
                embed.title = "Latest Overwatch News"
                embed.description = f"[Click here]({self.bot.config.overwatch['news']})"
                await ctx.send(embed=embed)
            else:
                for i, (title, link, img, date) in enumerate(
                    zip(titles, links, imgs, dates), start=1
                ):
                    embed = discord.Embed()
                    embed.set_author(name="Blizzard Entertainment")
                    embed.title = title
                    embed.url = link
                    embed.set_image(url=f"https:{img}")
                    embed.set_footer(text=f"News {i}/{len(titles)} - {date}")
                    pages.append(embed)
                await self.bot.paginator.Paginator(extras=pages).paginate(ctx)

    @commands.command()
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def patch(self, ctx):
        """Returns the most recent Overwatch patch note."""
        embed = discord.Embed(color=self.bot.color)
        embed.title = "Overwatch Patch Notes"
        embed.add_field(
            name="Live",
            value=f"[Click here to view **live** patch notes]({self.bot.config.overwatch['patch'].format('live')})",
            inline=False,
        )
        embed.add_field(
            name="Ptr",
            value=f"[Click here to view **ptr** patch notes]({self.bot.config.overwatch['patch'].format('ptr')})",
            inline=False,
        )
        embed.add_field(
            name="Experimental",
            value=f"[Click here to view **experimental** patch notes]({self.bot.config.overwatch['patch'].format('experimental')})",
            inline=False,
        )
        await ctx.send(embed=embed)

    @staticmethod
    def get_placement(place):
        placements = {
            1: "<:top500:632281138832080926>",
            2: "<:grandmaster:632281128966946826>",
            3: "<:master:632281117394993163>",
            4: "<:diamond:632281105571119105>",
            5: "<:platinum:632281092875091998>",
        }
        return placements[place]

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def leaderboard(self, ctx):
        """Displays a leaderboard of the 5 most active servers (based on commands runned)."""
        async with ctx.typing():
            guilds = await self.bot.pool.fetch(
                "SELECT id, commands_runned FROM server ORDER BY commands_runned DESC LIMIT 5;"
            )
            embed = discord.Embed()
            embed.title = "Five Most Active Servers"

            board = ""
            for i, guild in enumerate(guilds, start=1):
                g = self.bot.get_guild(guild["id"])
                board += (
                    f"{self.get_placement(i)} **{str(g)}**"
                    f" runned a total of **{guild['commands_runned']}** commands\n"
                    f"Joined on: **{str(g.me.joined_at).split(' ')[0]}**\n"
                )
                if i < 5:
                    board += "-----------\n"
            embed.description = board
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
