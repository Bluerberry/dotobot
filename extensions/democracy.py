
from __future__ import annotations

import logging
from os.path import basename

import discord
import pony.orm as pony
from discord.ext import commands

import lib.entities as entities
import lib.utility.util as util

MAX_VOTE_OPTIONS = 5
MAX_VOTE_WIDTH = 15


# ---------------------> Logging setup


name = basename(__file__)[:-3]
log = logging.getLogger(name)


# ---------------------> UI classes


class VoteButton(discord.ui.Button):
    def __init__(self, parent: VoteUI, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.parent.on_vote(interaction)

class VoteUI(discord.ui.View):
    def __init__(self, votes: dict[str, list[discord.User]], on_vote) -> None:
        super().__init__(timeout=60)
        self.votes = votes
        self.on_vote = on_vote
        
        # Add buttons
        for option in votes.keys():
            self.add_item(VoteButton(self, custom_id=option, label=option, style=discord.ButtonStyle.grey))
    
    def close_voting(self) -> None:
        self.clear_items()
        self.stop()


# ---------------------> Democracy cog


def setup(bot: commands.Bot) -> None:
    with pony.db_session:
        if entities.Extension.exists(name=name):
            extension = entities.Extension.get(name=name)
            extension.active = True

        else:
            entities.Extension(name=name, active=True)

    bot.add_cog(Democracy(bot))
    log.info(f'Extension has been created: {name}')

def teardown(bot: commands.Bot) -> None:
    with pony.db_session:
        extension = entities.Extension.get(name=name)
        extension.active = False
    
    log.info(f'Extension has been destroyed: {name}')

class Democracy(commands.Cog, name = name, description = 'Voting, lynching, etc.'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def generate_voteUI(self, votes: dict[str, list[discord.User]], threshold: int | None = None) -> str:
        longest_vote = max(len(str(len(voters))) for voters in votes.values())
        longest_option = max(len(option) for option in votes.keys())
        factory = util.ANSIFactory()

        for option, voters in votes.items():
            vote_count = len(voters)

            # Add vote option to UI
            if any(len(voters) >= threshold for voters in votes.values()):
                factory.add_raw('✅ ' if vote_count >= threshold else '⛔ ')
            factory.add(f'{option.ljust(longest_option)} │ {str(vote_count).rjust(longest_vote)} ')

            # Add vote bar to UI
            if threshold is not None:
                factory.add('█' * min(vote_count, threshold - 1), colour='white')
                if vote_count > threshold - 1:
                    factory.add('█' * (vote_count - threshold + 1), colour='green')
                    factory.add('-' * (MAX_VOTE_WIDTH - vote_count), colour='green', stroke='bold')

                else:
                    factory.add('-' * (threshold - vote_count - 1), colour='grey', stroke='bold')
                    factory.add('-' * (MAX_VOTE_WIDTH - threshold + 1), colour='green', stroke='bold')
            else:
                factory.add('█' * vote_count, colour='white')
                factory.add('-' * (MAX_VOTE_WIDTH - vote_count), colour='grey', stroke='bold')

            factory.add_raw('\n')

        return str(factory)
    
    @commands.command(name = 'vote', aliases = ['v'], description = 'Vote for an option.')
    @util.default_command(thesaurus={'a': 'anonymous', 't': 'threshold', 'p': 'prompt'})
    @util.summarized()
    async def vote(self, ctx: commands.Context, flags: list[str], vars: dict, params: list[str]) -> util.Summary:
        summary = util.Summary(ctx)
        dialog = util.Dialog(ctx)

        # Validate parameters
        if len(params) < 2 or len(params) > MAX_VOTE_OPTIONS:
            summary.set_header('Bad parameters given')
            summary.set_field('Error', f'Invalid number ({len(params)}) of options given. Between 2 and { MAX_VOTE_OPTIONS } options are required.')
            summary.set_field('Usage', f'`{ctx.prefix}vote <vote options> <--prompt="<prompt>"> [--threshold=<threshold>] [--anonymous] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'Bad parameters given, `{", ".join(params)}`')
            await dialog.cleanup()
            return summary
        
        if 'prompt' not in vars:
            summary.set_header('No prompt provided')
            summary.set_field('Error', f'Prompt not given. Use `--prompt="<prompt>"` to specify a prompt.')
            summary.set_field('Usage', f'`{ctx.prefix}vote <vote options> <--prompt="<prompt>"> [--threshold=<threshold>] [--anonymous] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
            log.warn(f'No prompt provided')
            await dialog.cleanup()
            return summary
        
        if 'threshold' in vars:
            try:
                vars['threshold'] = int(vars['threshold'])
                if not 0 < vars['threshold'] <= MAX_VOTE_WIDTH:
                    raise ValueError

            except ValueError:
                summary.set_header('Bad threshold given')
                summary.set_field('Error', f'Invalid threshold given. Threshold must be an integer between 0 and 20.')
                summary.set_field('Usage', f'`{ctx.prefix}vote <vote options> <--prompt="<prompt>"> [--threshold=<threshold>] [--anonymous] [--quiet | --verbose]`\nUse `{ctx.prefix}help status` for more information.')
                log.warn(f'Bad threshold given, `{vars["threshold"]}`')
                await dialog.cleanup()
                return summary
        
        # Vote callback
        async def on_vote(interaction: discord.Interaction) -> None:
            nonlocal votes, embed, view

            # Check if user has already voted
            if interaction.user in votes[interaction.custom_id]:
                await interaction.response.send_message('You have already voted for this option!', ephemeral=True)
                return
            
            await interaction.response.defer()

            # Update votes
            for option, voters in votes.items():
                if interaction.user in voters and option != interaction.custom_id:
                    voters.remove(interaction.user)
                elif interaction.user not in voters and option == interaction.custom_id:
                    voters.append(interaction.user)

            # Check if voting is complete
            if 'threshold' in vars and any(len(voters) >= vars['threshold'] for voters in votes.values()):
                embed = util.DefaultEmbed(ctx.bot, vars['prompt'], f'The vote has been completed! The results are as follows:')
                embed.add_field(name='Options', value=self.generate_voteUI(votes, vars['threshold']))
                view.close_voting()

                return await dialog.set(embed=embed, view=view)

            # Update UI
            embed.set_field_at(0, name='Options', value=self.generate_voteUI(votes, vars['threshold'] if 'threshold' in vars else None))
            await dialog.set(embed=embed, view=view)

        # Setup vote
        votes = {option: [] for option in params}
        embed = util.DefaultEmbed(ctx.bot, vars['prompt'], f'Democracy is beautiful. Vote for an option below! This vote **{"will" if "anonymous" in flags else "wont"}** be anonymous.')
        embed.add_field(name='Options', value=self.generate_voteUI(votes, vars['threshold'] if 'threshold' in vars else None))
        view = VoteUI(votes, on_vote)
        
        # Start voting!
        await dialog.set(embed=embed, view=view)

        return summary