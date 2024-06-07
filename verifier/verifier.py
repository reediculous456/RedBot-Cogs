import discord
import asyncio
from redbot.core import commands, Config
from discord.utils import get

class Verifier(commands.Cog):
    """A cog that handles user verification with questions."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=10061998)
        default_guild = {
            "questions": [],
            "role_id": None
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.ask_questions(member)

    async def get_prefix(self, guild):
        # Retrieve the prefix for the guild
        prefixes = await self.bot.get_prefix(guild)
        if isinstance(prefixes, list):
            return prefixes[0]
        return prefixes

    async def ask_questions(self, member):
        guild = member.guild
        prefix = await self.get_prefix(guild)
        questions = await self.config.guild(guild).questions()
        role_id = await self.config.guild(guild).role_id()
        role = get(guild.roles, id=role_id)

        if not role:
            await member.send("The admins of this server have enabled verification questions but have not set the role to be granted upon correct answers. Please contact them to have this corrected.")
            return

        if not questions:
            await member.send("The admins of this server have enabled verification questions but have not set any questions. Please contact them to have this corrected.")
            return

        def check(m):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        try:
            await member.send("Welcome! Please answer the following questions correctly to gain access to the server. You have 90 seconds to answer each question.")
            for q in questions:
                await member.send(q["question"])
                msg = await self.bot.wait_for('message', check=check, timeout=90.0)
                if msg.content.lower() != q["answer"].lower():
                    await member.send("Incorrect answer. Please contact an admin if you believe this is a mistake.")
                    return
            await member.send("Congratulations! You have answered all questions correctly.")
            await member.add_roles(role)
        except asyncio.TimeoutError:
            await member.send(f'You took too long to respond. To restart this process run the command {prefix}verify in the server.')

    @commands.guild_only()
    @commands.command()
    async def verify(self, ctx):
        """Manually trigger the verification process."""
        member = ctx.author
        role_id = await self.config.guild(ctx.guild).role_id()
        role = get(ctx.guild.roles, id=role_id)

        if role in member.roles:
            await ctx.send("You are already verified.")
        else:
            await self.ask_questions(member)

    @commands.group()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.guild_only()
    async def verifyset(self, ctx: commands.Context) -> None:
        """Sets verification module settings"""
        pass

    @verifyset.command()
    async def setonboardrole(self, ctx, role: discord.Role):
        """Set the role to be granted upon correct answers."""
        await self.config.guild(ctx.guild).role_id.set(role.id)
        await ctx.send(f"The onboarding role has been set to {role.name}.")

    @verifyset.command()
    async def addquestion(self, ctx, question: str, answer: str):
        """Add a question to the onboarding quiz."""
        async with self.config.guild(ctx.guild).questions() as questions:
            questions.append({"question": question, "answer": answer})
        await ctx.send("Question added.")

    @verifyset.command()
    async def listquestions(self, ctx):
        """List all onboarding questions."""
        questions = await self.config.guild(ctx.guild).questions()
        if not questions:
            await ctx.send("No onboarding questions set.")
            return

        question_list = "\n".join([f"Q: {q['question']} A: {q['answer']}" for q in questions])
        await ctx.send(f"Onboarding Questions:\n{question_list}")
