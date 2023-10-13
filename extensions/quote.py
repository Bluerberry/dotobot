
import logging
import os
from os.path import basename

import discord
import dotenv
import pony.orm as pony
from discord.ext import commands

import lib.entities as entities
import lib.util as utility


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> Environment setup


dotenv.load_dotenv()


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

class Quote(commands.Cog, name=name, description='Manages the quote database'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def display_quotes(self, dialog: utility.Dialog, summary: utility.Summary, quotes: list[entities.Quote]) -> None:
        if not quotes:
            summary.set_header('No quotes found')

        elif len(quotes) <= 10:
            summary.send_on_return = False
            summary.set_header(f'Found {len(quotes)} quote{"s" if len(quotes) == 1 else ""}')
            await dialog.add('> ' + '\n> '.join([str(q) for q in quotes]))

        else:
            summary.send_on_return = False
            summary.set_header(f'Found {len(quotes)} quotes')
            await self.mass_quote(dialog, quotes)

    async def mass_quote(self, dialog: utility.Dialog, quotes: list[entities.Quote]) -> None:
        start_id = quotes[0].quote_id
        block_count = 0
        msg = ''

        embed = utility.DefaultEmbed(self.bot, 'Quotes', footer=True)
        for quote in quotes:
            next_quote = str(quote) + '\n'

            # Prevent too long of a message block
            if len(msg) + len(next_quote) >= 975:

                # Send embed every 6 message blocks
                if block_count and not block_count % 6:
                    await dialog.add(embed=embed)
                    embed = utility.DefaultEmbed(self.bot, 'Quotes', footer=True, color=block_count // 6)

                embed.add_field(name=f'Quotes {start_id} : {quote.quote_id}', value=msg, inline=False)
                start_id = quote.quote_id
                msg = next_quote
                block_count += 1

            else:
                msg += next_quote

        embed.add_field(name=f'Quotes {start_id} : {quote.quote_id}', value=msg, inline=False)
        await dialog.add(embed=embed)

    def get_highest_id(self, guild_id: int) -> int:
        return pony.select(quote.quote_id for quote in entities.Quote if quote.guild_id == guild_id).max()


    # ---------------------> Commands


    @commands.group(name='quote', aliases=['q'], description='Subgroup for quote functionality', invoke_without_command=True)
    @utility.default_command(param_filter=r'(\d+)', thesaurus={'a': 'all'})
    @utility.summarized()
    async def quote(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> utility.Summary:
        summary = utility.Summary(ctx)
        dialog = utility.Dialog(ctx)

        # Check params
        if not params and 'all' not in flags and 'start' not in vars and 'stop' not in vars:
            summary.set_header('No parameters or apliccable flags or variables given')
            summary.set_field('Usage', f'`{ctx.prefix}quote <quote IDs | --all | [--start=<start ID>] [--stop=<stop ID>]> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No parameters or applicable flags or variables given')
            await dialog.cleanup()
            return summary

        try:
            if 'start' in vars:
                vars['start'] = int(vars['start'])
            if 'stop' in vars:
                vars['stop'] = int(vars['stop'])

        except ValueError:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            summary.set_header('Bad variables given')
            summary.set_field('ValueError', f'User provided non-numeric variables: {variables}')
            summary.set_field('Usage', f'`{ctx.prefix}quote <quote IDs | --all | [--start=<start ID>] [--stop=<stop ID>]> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warning(f'Bad variables given: {variables}. Expected numeric values')
            await dialog.cleanup()
            return summary

        # Get quotes
        with pony.db_session:
            if 'all' in flags:
                log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id))

            else:
                if 'start' in vars or 'stop' in vars:
                    log.debug(f'Following --start/stop branch for {ctx.prefix}{ctx.command}')
                    highest_id = self.get_highest_id(ctx.guild.id)
                    start, stop = 0, highest_id

                    if 'start' in vars:
                        start = vars['start'] if vars['start'] >= 0 else highest_id + vars['start']
                    if 'stop' in vars:
                        stop = vars['stop'] if vars['stop'] >= 0 else highest_id + vars['stop']

                    quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id and start <= quote.quote_id and quote.quote_id <= stop))

                else:
                    log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id and str(quote.quote_id) in params))

        # Display quotes
        await self.display_quotes(dialog, summary, quotes)
        await dialog.cleanup()
        return summary

    @quote.command(name='add', description='Add a quote to the database')
    @utility.default_command(param_filter=r'^ *["“] *(.+?) *["”] ?- *(.+?) *$')
    @utility.summarized()
    async def add(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> utility.Summary:
        summary = utility.Summary(ctx)
        dialog = utility.Dialog(ctx)

        # Check params
        if not params:
            summary.set_header('Bad parameters given')
            summary.set_field('Usage', f'`{ctx.prefix}quote add "<content>" - <author> [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'Bad parameters given')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Add quote
        content, author = params[0]
        with pony.db_session:
            prev_id = self.get_highest_id(ctx.guild.id)
            next_id = 1 if prev_id is None else prev_id + 1
            db_quote = entities.Quote(quote_id=next_id, guild_id=ctx.guild.id, content=content, author=author)

        log.info(f'A quote has been added; {str(db_quote)}')
        summary.set_header('Quote sucessfully added')
        summary.set_field(f'Quote', str(db_quote))
        await dialog.cleanup()
        return summary

    @quote.command(name='search', description='Searches through quotes')
    @utility.default_command(thesaurus={'e': 'exact', 'c': 'contains', 'f': 'fuzzy'})
    @utility.summarized()
    async def search(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> utility.Summary:
        summary = utility.Summary(ctx)
        dialog = utility.Dialog(ctx)

        # Check params
        if params:
            parameters = ', '.join(params)
            log.warning(f'Redundant parameters found: {parameters}')
            summary.set_field('Redundant parameters', f'This function does not accept parameters, yet it found these: {parameters}.')

        # Get quotes
        with pony.db_session:
            if 'content' in vars and 'author' in vars:
                log.debug(f'Following --content/author branch for {ctx.prefix}{ctx.command}')

                if 'exact' in flags:
                    log.debug(f'Following --exact branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(
                        lambda quote: quote.guild_id == ctx.guild.id and quote.content == vars['content'] and quote.author == vars['author']
                    ))

                elif 'contains' in flags:
                    log.debug(f'Following --contains branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(
                        lambda quote: quote.guild_id == ctx.guild.id and vars['content'] in quote.content and vars['author'] in quote.author
                    ))

                else: # Fuzzy search is default
                    log.debug(f'Following --fuzzy branch for {ctx.prefix}{ctx.command}')
                    quotes = entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id)
                    options = [utility.SearchItem(quote, quote.content) for quote in quotes]
                    _, results = utility.fuzzy_search(options, vars['content'])
                    author_options = [utility.SearchItem(quote, quote.author) for quote in quotes]
                    _, author_results = utility.fuzzy_search(author_options, vars['author'])

                    # Merge the two rankings
                    for content_result in results:
                        for author_result in author_results:
                            if author_result.item == content_result.item:
                                content_result.ranking += author_result.ranking
                                break

                    # Grab top 10 quotes
                    results.sort(key=lambda result: result.ranking)
                    quotes = [item.item for item in results[:10]]

            elif 'content' in vars:
                log.debug(f'Following --content branch for {ctx.prefix}{ctx.command}')

                if 'exact' in flags:
                    log.debug(f'Following --exact branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(
                        lambda quote: quote.guild_id == ctx.guild.id and quote.content == vars['content']
                    ))

                elif 'contains' in flags:
                    log.debug(f'Following --contains branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(
                        lambda quote: quote.guild_id == ctx.guild.id and vars['content'] in quote.content
                    ))

                else: # Fuzzy search is default
                    log.debug(f'Following --fuzzy branch for {ctx.prefix}{ctx.command}')
                    quotes = entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id)
                    options = [utility.SearchItem(quote, quote.content) for quote in quotes]
                    _, results = utility.fuzzy_search(options, vars['content'])
                    quotes = [item.item for item in results[:10]]

            elif 'author' in vars:
                log.debug(f'Following --author branch for {ctx.prefix}{ctx.command}')

                if 'exact' in flags:
                    log.debug(f'Following --exact branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(
                        lambda quote: quote.guild_id == ctx.guild.id and quote.author == vars['author']
                    ))

                elif 'contains' in flags:
                    log.debug(f'Following --contains branch for {ctx.prefix}{ctx.command}')
                    quotes = list(entities.Quote.select(
                        lambda quote: quote.guild_id == ctx.guild.id and vars['author'] in quote.author
                    ))

                else: # Fuzzy search is default
                    log.debug(f'Following --fuzzy branch for {ctx.prefix}{ctx.command}')
                    quotes = entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id)
                    options = [utility.SearchItem(quote, quote.author) for quote in quotes]
                    _, results = utility.fuzzy_search(options, vars['author'])
                    quotes = [result.item for result in results[:10]]

            else:
                summary.set_header('Bad parameters given')
                summary.set_field('Usage', f'`{ctx.prefix}quote search [--content=<content>] [--author=<author>] [--exact | --contains | --fuzy] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
                log.warn(f'Bad parameters given')
                await dialog.cleanup()
                return summary

            # Display quotes
            await self.display_quotes(dialog, summary, quotes)
            await dialog.cleanup()
            return summary

    @quote.command(name='remove', aliases=['del', 'delete'], description='Removes quotes')
    @commands.has_permissions(administrator=True)
    @utility.default_command(param_filter=r'(\d+)', thesaurus={'a': 'all', 'f': 'force'})
    @utility.summarized()
    async def remove(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> utility.Summary:
        summary = utility.Summary(ctx)
        dialog = utility.Dialog(ctx)

        # Check params
        if not params and 'all' not in flags:
            summary.set_header('No parameters or applicable flags given')
            summary.set_field('Usage', f'`{ctx.prefix}quote remove <quote IDS | --all> [--force] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'Bad parameters given')
            await dialog.cleanup()
            return summary

        if 'all' in flags and str(ctx.author.id) not in os.getenv('DEVELOPER_IDS'):
            summary.set_header('Only developers can bulk delete')
            summary.set_field('Aborted', f'User `{ctx.author.name}` ({ctx.author.id}) is not a developer, thus can\'t bulk delete.')
            log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) is not a developer')
            await dialog.cleanup()
            return summary

        if vars:
            variables = ', '.join([f'{key} = "{value}"' for key, value in vars.items()])
            log.warning(f'Redundant variables found: {variables}')
            summary.set_field('Redundant variables', f'This function does not accept variables, yet it found these: {variables}.')

        # Get quotes
        with pony.db_session:
            if 'all' in flags:
                log.debug(f'Following --all branch for {ctx.prefix}{ctx.command}')
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id))

            else:
                log.debug(f'Following parameter branch for {ctx.prefix}{ctx.command}')
                quotes = list(entities.Quote.select(lambda quote: quote.guild_id == ctx.guild.id and str(quote.quote_id) in params))

            # Check query
            if not quotes:
                if 'all' in flags:
                    summary.set_field('Empty database', 'There are no quotes in the database registered to this server.')
                    log.warning(f'There are no quotes in the database registered to this server ({ctx.guild.id})')

                else:
                    summary.set_field('Invalid parameters', f'The given quote IDs ({" ,".join(params)}) don\'t exist!')
                    log.warning(f'The given quote IDs: {" ,".join(params)} don\'t exist, and can\'t be removed from the database')

                summary.set_header('No quotes found')
                await dialog.cleanup()
                return summary

            # Bulk delete
            if ('all' in flags or len(quotes) >= 10) and 'force' not in flags:
                log.debug(f'Following bulk delete branch for {ctx.prefix}{ctx.command}')

                # Verify bulk delete
                view = utility.ContinueCancelMenu(ctx.author)
                log.warning(f'User `{ctx.author.name}` ({ctx.author.id}) is about to delete {len(quotes)} quotes')
                await dialog.set(f'You are about to delete {len(quotes)} quotes. Are you really fucking sure?', view=view)
                result = await view.await_response()

                if not result:
                    summary.set_header('Bulk delete has been aborted')
                    summary.set_field('Aborted', f'User `{ctx.author.name}` ({ctx.author.id}) aborted bulk delete.')
                    log.info(f'User `{ctx.author.name}` ({ctx.author.id}) aborted bulk delete')
                    await dialog.cleanup()
                    return summary

            # Delete quotes
            msg, count = '', 0
            for quote in quotes:
                count += 1
                msg += f'Quote {str(quote)}\n'
                log.info(f'Quote {quote.quote_id} from guild {quote.guild_id} has been removed')
                quote.delete()

        if count < 20:
            summary.set_field('Removed quotes', msg)
        summary.set_header(f'Sucessfully removed {count} quote{"" if count == 1 else "s"}')
        await dialog.cleanup()
        return summary

    @quote.command(name='edit', description='Edits quotes')
    @commands.has_permissions(administrator=True)
    @utility.default_command(param_filter=r'^ *(\d+) *$')
    @utility.summarized()
    async def edit(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> utility.Summary:
        summary = utility.Summary(ctx)
        dialog = utility.Dialog(ctx)

        # Check params
        if not params or 'content' not in vars and 'author' not in vars:
            summary.set_header('No parameters or applicable flags given')
            summary.set_field('Usage', f'`{ctx.prefix}quote edit <quote ID> [--content=<new content>] [--author=<new author>] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'Bad parameters given')
            await dialog.cleanup()
            return summary

        with pony.db_session:

            # Get quote
            db_quote = entities.Quote.get(quote_id=params[0])
            if not db_quote:
                summary.set_header('Quote not found')
                summary.set_field('ValueError', f'User provided bad parameters. No quote with ID ({params[0]}) found')
                log.warning(f'Quote not found')
                await dialog.cleanup()
                return summary

            # Edit content
            if 'content' in vars:
                db_quote.content = vars['content']
                log.info(f'Content of quote ({db_quote.quote_id}) edited to "{vars["content"]}"')

            if 'author' in vars:
                db_quote.author = vars['author']
                log.info(f'Author of quote ({db_quote.quote_id}) edited to "{vars["author"]}"')

        summary.set_header('Succesfully edited quote')
        summary.set_field('New quote', str(db_quote))
        await dialog.cleanup()
        return summary
