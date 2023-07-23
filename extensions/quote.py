
import asyncio
import logging
from os import getenv
from os.path import basename
import re as regex

import dotenv
import discord
from discord.ext import commands
import pony.orm as pony

import lib.entities as entities
import lib.util as util


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Environment setup


dotenv.load_dotenv()


# ---------------------> UI components


class VerifyDeleteAll(discord.ui.View):
    def __init__(self, authorised_user: discord.User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.authorised_user = authorised_user
        self.responded = asyncio.Event()
        self.result = None

    async def await_response(self) -> None:
        await self.responded.wait()
        self.disable_all_items()

    @discord.ui.button(label='Delete All', style=discord.ButtonStyle.red, emoji='🗑️')
    async def override(self, _, interaction: discord.Interaction) -> None:
        # Only authorised users can interact
        if interaction.user != self.authorised_user:
            return

        await interaction.response.defer()
        self.result = True
        self.responded.set()

    @discord.ui.button(label='Abort', style=discord.ButtonStyle.gray, emoji='👶')
    async def abort(self, _, interaction: discord.Interaction) -> None:
        # Only authorised users can interact
        if interaction.user != self.authorised_user:
            return

        await interaction.response.defer()
        self.result = False
        self.responded.set()


# ---------------------> Quote cog


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
    async def quote(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
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
    @util.default_command(param_filter=r' *["“](.+)["”] ?- ?(.+)')
    @util.summarized()
    async def add(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
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
    async def last(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
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

    @quote.command(name='remove', aliases=['del', 'delete'], description='Removes quotes')
    @commands.has_permissions(administrator=True)
    @util.default_command(param_filter=r'(\d+)', thesaurus={'a': 'all', 'q': 'quiet', 'v': 'verbose'})
    @util.summarized()
    async def remove(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params and 'all' not in flags:
            summary.set_header('No parameters given')
            summary.set_field('ValueError', f'User provided no parameters, nor the \'all\' flag. Command usage dictates `$quote remove [quote IDs] --[flags]`')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary
        
        # Get quotes
        with pony.db_session:
            if 'all' in flags:
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id))
            else:
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id and str(quote.quote_id) in params))
        
            # Check query
            if not quotes:
                summary.set_header('No quotes found')
                summary.set_field('Invalid parameters', f'The given quote IDs ({" ,".join(params)}) don\'t exist!')
                log.warn(f'The given quote IDs ({" ,".join(params)}) don\'t exist, and can\'t be removed from the database')
                await dialog.cleanup()
                return summary

            # Bulk delete
            if len(quotes) >= 10:
                
                # Only developers can bulk delete
                if str(ctx.author.id) not in getenv('DEVELOPER_IDS'):
                    summary.set_header('Only developers can bulk delete')
                    summary.set_field('Aborted', f'User `{ctx.author.name}` ({ctx.author.id}) is not a developer, thus can\'t bulk delete.')
                    log.info('Bulk delete is cancelled ')
                    await dialog.cleanup()
                    return summary

                # Verify bulk delete
                log.warn(f'User `{ctx.author.name}` ({ctx.author.id}) is about to delete {len(quotes)} quotes')
                view = VerifyDeleteAll(ctx.author)
                await dialog.set(f'You are about to delete {len(quotes)} quotes. Are you really fucking sure?', view=view)
                await view.await_response()

                if not view.result:
                    summary.set_header('Bulk delete has been aborted')
                    summary.set_field('Aborted', f'User `{ctx.author.name}` ({ctx.author.id}) doesn\'t have permission to delete {len(quotes)}.')
                    log.info('Bulk delete has been aborted due to lack of permissions')
                    await dialog.cleanup()
                    return summary

            # Delete quotes
            msg = ''
            count = 0
            for quote in quotes:
                count += 1
                msg += f'Quote {str(quote)}\n'
                log.info(f'Quote {quote.quote_id} from guild {quote.guild_id} has been removed')
                quote.delete()
        
        summary.set_header(f'Sucessfully removed {count} quote{"" if count == 1 else "s"}')
        if count < 20:
            summary.set_field('Removed quotes', msg)
        await dialog.cleanup()
        return summary
            
    @quote.command(name='edit', description='Edits quotes')
    @commands.has_permissions(administrator=True)
    @util.default_command(param_filter=r'^(\d+)$')
    @util.summarized()
    async def edit(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('No parameters given')
            summary.set_field('ValueError', f'User provided no parameters. Command usage dictates `$quote edit [quote ID] (--content="[content]") (--author="[author]") --[flags]`')
            log.warn(f'No parameters given')
            await dialog.cleanup()
            return summary
        
        with pony.db_session:

            # Get quote
            db_quote = entities.Quote.get(quote_id=params[0])
            if not db_quote:
                summary.set_header('Quote not found')
                summary.set_field('ValueError', f'User provided bad parameters. No quote with ID ({params[0]}) Found')
                log.warn(f'Quote not found')
                await dialog.cleanup()
                return summary
                            
            # Edit content
            if 'content' in vars:
                db_quote.quote = vars['content']
                log.info(f'Content of quote ({db_quote.quote_id}) edited to "{vars["content"]}"')
            if 'author' in vars:
                db_quote.author = vars['author']
                log.info(f'Author of quote ({db_quote.quote_id}) edited to "{vars["author"]}"')

        summary.set_header('Succesfully edited quote')
        summary.set_field('New quote', str(db_quote))
        await dialog.cleanup()
        return summary
