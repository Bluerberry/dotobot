import logging
import re

from entities import Quote
from os.path import basename
from pony.orm import db_session, max as pony_max
from discord.ext import commands

# ---------------------> Logging setup

name = basename(__file__)[:-2]
log = logging.getLogger(name)


# ---------------------> Example cog

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Quotes(bot))
    log.info(f'Extension has been created: {name}')


def teardown(_: commands.Bot) -> None:
    log.info(f'Extension has been destroyed: {name}')


def split_quote(quote: str) -> tuple[str, str]:
    REGEX = r'["“](.*)["”] ?- ?(.*)'
    match = re.search(REGEX, quote)
    return match.group(1), match.group(2)


class Quotes(commands.Cog, name=name, description='Manages the quotes'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.group(aliases=['quote'], brief='Subgroup for quote functionality',
                    description='Subgroup for quote functionality. Use !help q')
    async def q(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            log.info(f'User {ctx.author.name} has passed an invalid quote subcommand: "{ctx.message.content}"')
            # run command as if it was a !q

    @q.command(brief='Add a quote', description='Add a quote to the database', usage='"[quote]" - [author]')
    async def add(self, ctx: commands.Context, *, args=None) -> None:
        guild_id = str(ctx.guild.id)
        quote_string, author = split_quote(args)

        with db_session:
            max_in_table = pony_max(quote.quote_id for quote in Quote if quote.guild_id == guild_id)
            logging.info(max_in_table)
            nextid = 0 if max_in_table is None else max_in_table + 1
            Quote(quote_id=nextid, guild_id=guild_id, quote=quote_string, author=author)

        log.info(f"A quote has been added; {nextid}: \"{quote_string}\" - {author}")
        await ctx.send(f'Quote added. Assigned ID: {nextid}')
