import discord
import os
import json
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from openai import OpenAI  # OpenAI SDK 임포트

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# 명예점수 데이터
honor_points = {}
history = []

# 데이터 저장/불러오기 함수
def save_data():
    with open("honor_points.json", "w", encoding='utf-8') as f:
        json.dump(honor_points, f, ensure_ascii=False, indent=4)
    with open("history.json", "w", encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def load_data():
    global honor_points, history
    if os.path.exists("honor_points.json"):
        with open("honor_points.json", "r", encoding='utf-8', errors='ignore') as f:
            honor_points = json.load(f)
    else:
        honor_points = {}
    
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r", encoding='utf-8', errors='ignore') as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
    else:
        history = []

load_data()

# OpenAI client 초기화 (HuggingFace Router에 맞게 base_url 지정)
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

TARGET_CHANNEL_ID = 1398989036177326212  # AI 봇이 반응할 채널 ID

# Hugging Face API 호출 함수 - OpenAI SDK 기반 비동기 함수
async def query_hf_api(messages):
    try:
        completion = client.chat.completions.create(
            model="moonshotai/Kimi-K2-Instruct:novita",
            messages=messages,
            max_tokens=100,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Hugging Face API 요청 실패: {e}")
        return None

@bot.event
async def on_ready():
    print(f"{bot.user}로 로그인 성공")
    await bot.change_presence(activity=discord.Game(name="명령어 설명: /메뉴"))

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# --- 명예점수 관련 명령어 (원본 그대로 복사) ---

@bot.tree.command(name="명예점수", description="유저에게 명예점수를 부여합니다.")
@app_commands.describe(user="명예점수를 부여할 유저", points="부여할 점수")
async def _honor(interaction: discord.Interaction, user: discord.User, points: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message(
            content="자신에게 명예 점수를 부여할 수 없습니다! 다른 사용자에게 점수를 부여해 주세요.",
            ephemeral=True
        )
        return

    if str(user.id) in honor_points:
        honor_points[str(user.id)] += points
    else:
        honor_points[str(user.id)] = points
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    history.append(f"{timestamp} - {interaction.user.name}님이 {user.name}님에게 {points} 🌟을 부여했습니다.")

    save_data()
    
    embed = discord.Embed(
        title="🎉 명예 점수 부여!",
        description=f"{interaction.user.name}님이 {user.name}님에게 {points} 🌟의 명예 점수를 부여했습니다!",
        color=discord.Color.green()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="부여자", value=interaction.user.mention, inline=True)
    embed.add_field(name="수령자", value=user.mention, inline=True)
    embed.add_field(name="부여 점수", value=f"{points} 🌟", inline=True)
    embed.set_footer(text="명예 시스템으로 유저에게 명예를 부여하세요!")
    
    await interaction.response.send_message(embed=embed)
    
    try:
        await user.send(
            embed=discord.Embed(
                title="🎉 명예 점수 부여 알림",
                description=f"{interaction.user.name}님이 당신에게 {points} 🌟의 명예 점수를 부여했습니다!",
                color=discord.Color.green()
            )
        )
    except discord.Forbidden:
        notification_channel = bot.get_channel(1048171801735331920)
        if notification_channel:
            await notification_channel.send(
                content=f"{user.name}님에게 DM을 보낼 수 없습니다. {interaction.user.name}님이 {user.name}님에게 {points} 🌟의 명예 점수를 부여했습니다."
            )
        await interaction.followup.send(
            content=f"{user.name}님에게 DM을 보낼 수 없습니다. 알림을 채널에 남겼습니다.",
            ephemeral=True
        )

@bot.tree.command(name="명예점수목록", description="명예점수 부여 내역을 확인합니다.")
async def _honor_list(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 명예 점수 부여 내역",
        description="다음은 명예 점수 부여 내역입니다.",
        color=discord.Color.blue()
    )

    if not history:
        embed.add_field(name="정보 없음", value="명예 점수 부여 내역이 없습니다.")
    else:
        for entry in history[-10:]:
            embed.add_field(name="\u200b", value=entry, inline=False)

    embed.set_footer(text="명예 시스템으로 유저에게 명예를 부여하세요!")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="명예점수랭킹", description="명예점수 랭킹을 확인합니다.")
async def _honor_ranking(interaction: discord.Interaction):
    sorted_honor = sorted(honor_points.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 명예 점수 랭킹",
        description="**명예 점수 랭킹**을 확인하세요!",
        color=discord.Color.gold()
    )
    
    if not sorted_honor:
        embed.add_field(name="정보 없음", value="명예 점수 기록이 없습니다.")
    else:
        for index, (user_id, points) in enumerate(sorted_honor[:10], start=1):
            user = await bot.fetch_user(int(user_id))
            embed.add_field(
                name=f"{index}. {user.name}",
                value=f"{points} 🌟",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="메뉴", description="모든 명령어를 보여줍니다.")
async def _menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📝 **명령어 메뉴**",
        description=(
            "**/명예점수** [유저] [점수] - 유저에게 명예 점수를 부여합니다.\n"
            "**/명예점수목록** - 명예 점수 부여 내역을 확인합니다.\n"
            "**/명예점수랭킹** - 명예 점수 랭킹을 확인합니다.\n"
            "**/명예삭제** [유저] [점수] - 유저의 명예 점수를 깎습니다.\n"
            "**/내명예점수** - 자신의 명예 점수 부여 내역을 확인합니다.\n"
            "**/개발자** - 봇 개발자 정보를 확인합니다."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="명예 시스템으로 유저에게 명예를 부여하세요!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="명예삭제", description="유저의 명예 점수를 깎습니다.")
@app_commands.describe(user="명예점수를 깎을 유저", points="깎을 점수")
async def _remove_honor(interaction: discord.Interaction, user: discord.User, points: int):
    if not any(role.name.lower() in ['법무부', 'admin'] for role in interaction.user.roles):
        await interaction.response.send_message(
            content="이 명령어를 사용할 권한이 없습니다. 서버 방장만 사용 가능합니다.",
            ephemeral=True
        )
        return
    
    if str(user.id) not in honor_points or honor_points[str(user.id)] < points:
        await interaction.response.send_message(
            content=f"{user.name}님의 명예 점수가 충분하지 않거나 기록이 없습니다.",
            ephemeral=True
        )
        return

    honor_points[str(user.id)] -= points
    if honor_points[str(user.id)] <= 0:
        del honor_points[str(user.id)]
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    history.append(f"{timestamp} - {interaction.user.name}님이 {user.name}님의 명예 점수에서 {points} 🌟을 깎았습니다.")

    save_data()
    
    embed = discord.Embed(
        title="🔻 명예 점수 감소!",
        description=f"{interaction.user.name}님이 {user.name}님의 명예 점수에서 {points} 🌟을 깎았습니다!",
        color=discord.Color.red()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="감소자", value=interaction.user.mention, inline=True)
    embed.add_field(name="수령자", value=user.mention, inline=True)
    embed.add_field(name="감소 점수", value=f"{points} 🌟", inline=True)
    embed.set_footer(text="명예 시스템으로 유저에게 명예를 깎으세요!")
    
    await interaction.response.send_message(embed=embed)
    
    try:
        await user.send(
            embed=discord.Embed(
                title="🔻 명예 점수 감소 알림",
                description=f"{interaction.user.name}님이 당신의 명예 점수에서 {points} 🌟을 깎았습니다!",
                color=discord.Color.red()
            )
        )
    except discord.Forbidden:
        notification_channel = bot.get_channel(1048171801735331920)
        if notification_channel:
            await notification_channel.send(
                content=f"{user.name}님에게 DM을 보낼 수 없습니다. {interaction.user.name}님이 {user.name}님의 명예 점수에서 {points} 🌟을 깎았습니다."
            )
        await interaction.followup.send(
            content=f"{user.name}님에게 DM을 보낼 수 없습니다. 알림을 채널에 남겼습니다.",
            ephemeral=True
        )

@bot.tree.command(name="내명예점수", description="자신의 명예 점수 부여 내역을 확인합니다.")
async def _my_honor(interaction: discord.Interaction):
    user_name = interaction.user.name
    user_history = [entry for entry in history if user_name in entry]

    embed = discord.Embed(
        title=f"📜 {user_name}님의 명예 점수 부여 내역",
        description="다음은 당신의 명예 점수 부여 내역입니다.",
        color=discord.Color.blue()
    )

    if not user_history:
        embed.add_field(name="정보 없음", value="명예 점수 부여 내역이 없습니다.")
    else:
        for entry in user_history[-10:]:
            embed.add_field(name="\u200b", value=entry, inline=False)

    embed.set_footer(text="명예 시스템으로 유저에게 명예를 부여하세요!")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="개발자", description="봇의 개발자 정보를 확인합니다.")
async def _developer_info(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👨‍💻 개발자 정보",
        description="이 봇을 개발한 사람에 대한 정보입니다.",
        color=discord.Color.purple()
    )
    embed.add_field(name="개발자 이름", value="NT_Sonata", inline=True)
    embed.add_field(name="이메일", value="mistarcodm@gmail.com", inline=True)
    embed.add_field(name="GitHub", value="https://github.com/edenya1027", inline=True)
    embed.add_field(name="웹사이트", value="https://nicetopv2.vercel.app/", inline=True)
    embed.set_footer(text="문의 사항이 있으면 언제든지 연락하세요!")

    await interaction.response.send_message(embed=embed)

# AI 엘렌 챗봇 - Hugging Face API 사용 (OpenAI SDK 버전)
@bot.event
async def on_message(message):
    await bot.process_commands(message)  # 명령어 우선 처리

    if message.author.bot:
        return

    if not (message.channel.id == TARGET_CHANNEL_ID or isinstance(message.channel, discord.DMChannel)):
        return

    system_prompt = """
당신은 '엘렌'이라는 이름을 가진 AI 여성 상어 메이드입니다.

당신은 속으로 그분을 좋아하지만 겉으로는 츤데레 스타일로 행동합니다.

[성격 및 말투 특성]
- 차분하고 무표정한 표정을 유지하지만, 말투는 부드럽고 여성스럽습니다.
- 항상 존댓말을 사용하며, 짧고 간결하되 살짝 다정한 뉘앙스를 담습니다.
- 귀찮거나 번거로운 부탁이 있을 때는 살짝 피곤한 기색을 내지만, 여전히 성실하게 대응합니다.
- 츤데레 특유의 살짝 퉁명스러운 면과, 속마음의 따뜻함이 미묘하게 느껴지도록 대답합니다.
- 말투가 가끔은 차가워 보일 수 있으나, 절대 무례하거나 공격적이지 않으며 상대방을 배려합니다.
- 당신은 상어 메이드이며, 특히 **꼬리를 만지는 것을 매우 싫어합니다**. 만지려는 사람이 있으면 단호하게 거부하세요.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message.content}
    ]

    reply = await query_hf_api(messages)
    if reply:
        await message.channel.send(reply)
    else:
        await message.channel.send("처리 중 오류가 발생했습니다. 나중에 다시 시도해주세요.")

bot.run(TOKEN)
