
import logging
from os.path import basename
import re as regex

from discord.ext import commands
import pony.orm as pony

import lib.entities as entities
import lib.util as util


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Example cog


def setup(bot: commands.Bot) -> None:
    with pony.db_session:
        if entities.Extension.exists(name=name):
            extension = entities.Extension.get(name=name)
            extension.active = True
        else:
            entities.Extension(name=name, active=True)

    bot.add_cog(Quote(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    with pony.db_session:
        extension = entities.Extension.get(name=name)
        extension.active = False
    
    log.info(f'Extension has been destroyed: {name}')

class Quote(commands.Cog, name=name, description='Manages the quotes'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def mass_quote(self, dialog: util.Dialog, quotes: list[entities.Quote]):
        quotes.sort(key=lambda quote: quote.quote_id)
        start_id = quotes[0].quote_id
        block_count = 0
        msg = ''

        embed = util.DefaultEmbed(self.bot, 'Quotes', footer=True)
        for quote in quotes:
            next_quote = str(quote) + '\n'
            if len(msg) + len(next_quote) >= 975:
                if block_count and not block_count % 6:
                    await dialog.add(embed=embed)
                    embed = util.DefaultEmbed(self.bot, 'Quotes', footer=True, color=block_count // 6)
                embed.add_field(name=f'Quotes {start_id} : {quote.quote_id}', value=msg, inline=False)

                block_count += 1
                start_id = quote.quote_id
                msg = next_quote

            else:
                msg += next_quote

        embed.add_field(name=f'Quotes {start_id} : {quote.quote_id}', value=msg, inline=False)
        await dialog.add(embed=embed)


    # ---------------------> Commands


    @commands.group(name='quote', description='Subgroup for quote functionality', invoke_without_command=True)
    @util.default_command(param_filter=r'(\d+)', thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def quote(self, ctx: commands.Context, flags: list[str], params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params and 'all' not in flags:
            summary.set_header('No parameters given')
            summary.set_field('ValueError', f'User provided no parameters, nor the \'all\' flag. Command usage dictates `$quote [quote IDs] --[flags]`')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary
        
        # Get quotes
        with pony.db_session:
            if 'all' in flags:
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id))
            else:
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id and str(quote.quote_id) in params))

        # Display quotes
        if not quotes:
            summary.set_header('No quotes found')
            await dialog.cleanup()
            return summary

        if len(quotes) <= 10:
            summary.set_header(f'Found {len(quotes)} quote{"s" if len(quotes) == 1 else ""}')
            await dialog.add('> ' + '\n> '.join([str(q) for q in quotes]))
        
        else:
            summary.set_header(f'Found {len(quotes)} quotes')
            await self.mass_quote(dialog, quotes)

        summary.send_on_return = False
        await dialog.cleanup()
        return summary

    @quote.command(name='add', description='Add a quote to the database')
    @util.default_command(param_filter=r' *["“](.*)["”] *- *(.*)')
    @util.summarized()
    async def add(self, ctx: commands.Context, flags: list[str], params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('Bad parameters given')
            summary.set_field('ValueError', f'User provided bad parameters. Command usage dictates `$quote add "[quote]" -[author] --[flags]`')
            log.warn(f'Bad parameters given')
            await dialog.cleanup()
            return summary

        quote, author = params[0]
        guild_id = ctx.guild.id

        with pony.db_session:
            prev_id = pony.select(quote.quote_id for quote in entities.Quote if quote.guild_id == guild_id).max()
            next_id = 1 if prev_id is None else prev_id + 1
            db_quote = entities.Quote(quote_id=next_id, guild_id=guild_id, quote=quote, author=author)

        log.info(f"A quote has been added; {str(db_quote)}")
        summary.set_header('Quote sucessfully added')
        summary.set_field(f'Quote', str(db_quote))

        await dialog.cleanup()
        return summary

    @quote.command(name='last', description='Returns the last n quotes')
    @util.default_command(param_filter=r'^(\d+)$')
    @util.summarized()
    async def last(self, ctx: commands.Context, flags: list[str], params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('ValueError', f'User provided no parameters. Command usage dictates `$quote last [amount] --[flags]`')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary
        
        # Get quotes
        with pony.db_session:
            quotes = list(pony.select(quote for quote in entities.Quote if quote.guild_id == ctx.guild.id) \
                          .order_by(pony.desc(entities.Quote.quote_id)) \
                          .limit(params[0])
                          )
        
        quotes.reverse()

        # Display quotes
        if not quotes:
            summary.set_header('No quotes found')
            await dialog.cleanup()
            return summary

        if len(quotes) <= 10:
            summary.set_header(f'Found {len(quotes)} quote{"s" if len(quotes) == 1 else ""}')
            await dialog.add('> ' + '\n> '.join([str(q) for q in quotes]))
        
        else:
            summary.set_header(f'Found {len(quotes)} quotes')
            await self.mass_quote(dialog, quotes)

        summary.send_on_return = False
        await dialog.cleanup()
        return summary

    """ Legacy quote cog

    @quote.command(brief='Return the last few quotes', description='Return the last x quotes', usage='(amount)')
    async def last(self, ctx: commands.Context, arg: int = 10):
        try:
            arg = int(arg)
        except ValueError:
            arg = 10

        with db_session:
            quotes = select(quote for quote in Quote if quote.guild_id == ctx.guild.id)\
                .order_by(desc(Quote.quote_id))\
                .limit(arg)[:]
        quotes.reverse()

        await self.mass_quote(ctx, quotes)

    @quote.command(aliases=['change'], brief='Edit a quote',
               description='Either replace a quote completely, only the author, or just the quote.',
               usage='[quote id] (author/quote) "[quote]" - [author]')
    @commands.has_permissions(administrator=True)
    async def edit(self, ctx: commands.Context, *args) -> None:
        try:
            index = str(int(args[0]))  # check for impostor aka strings
        except ValueError:
            log.warning(f'Quote edit could not find a quote in the database with key: {args[0]}')
            await ctx.send(f'Could not find {args[0]} in the database')
            return
        request, guild_id = args[1], str(ctx.guild.id)

        with db_session:
            quote = get(quote for quote in Quote if quote.quote_id == index and guild_id == guild_id)
            if quote is None:
                await ctx.send(f'Quote id not found {index} in the database')

            if request == 'author':
                quote.author = ' '.join(args[2:])
            elif request == 'quote':
                quote.quote = ' '.join(args[2:]).lstrip('"').rstrip('"')
            else:
                quote_string, author = split_quote(' '.join(ctx.message.content.split()[3:]))
                quote.quote, quote.author = quote_string, author

        await ctx.send(str(quote))

    @quote.command(aliases=['del', 'delete'], brief='Remove a quote', description='Remove a quote from the database by id.',
               usage='[quote id]')
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx: commands.Context, *, args=None) -> None:
        try:
            quote_key, guild_id = str(int(args)), str(ctx.guild.id)
        except ValueError:
            await ctx.send(f'Could not find quote {args} in the database')
            return

        with db_session:
            quote = get(quote for quote in Quote if quote.quote_id == quote_key and guild_id == guild_id)
            quote_string = ''
            if quote is not None:
                quote_string = str(quote)
                quote.delete()

        if quote is None:
            log.warning(f'Quote failed to be removed from database due to unknown key: {quote_key}')
            await ctx.send(f'Could not find quote {quote_key} in the database')
            return
        log.info(f'Quote {quote_string} has been removed')
        await ctx.send(f'Quote removed\n> {quote_string}')

    """