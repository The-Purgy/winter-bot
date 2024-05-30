import discord
from discord.ext import commands
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import random
import asyncio
import json
import datetime
import re
import pytz
import string
import os
from dotenv import load_dotenv

load_dotenv()

nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

# Initialize an empty dictionary to store user data
user_data = {}

# Create a new bot instance with a specified prefix and intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# Define handlers for each command
async def play_game(message):
    await message.channel.send(f"Which game would you like to play, {message.author.mention}?")

    # Wait for the user's response
    def check(response):
        """Check if the response is from the same user and in the same channel"""
        return response.author == message.author and response.channel == message.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=30)
        game_name = response.content.lower()

        if game_name == 'rock paper scissors':
            await rock_paper_scissors(message)
        else:
            await message.channel.send(f"Sorry, I don't know how to play {game_name} yet!")

    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond!")


async def how_are_you(message):
    responses = [
        "I'm doing great, thanks for asking!",
        "I'm feeling a little glitchy today, but I'll survive.",
        "I'm doing fantastic! Just hanging out and waiting for someone to play with.",
        "I'm a bot, so I don't really have feelings, but I'm functioning properly, so that's good, right?",
        "I'm super duper awesome, thanks for asking!"
    ]
    await message.channel.send(random.choice(responses))


async def how_many_points(message):
    user_id = str(message.author.id)
    activity_data = load_activity_data()
    if user_id in activity_data:
        points = activity_data[user_id]['points']
        await message.channel.send(f'{message.author.mention}, you have {points} points!')
    else:
        await message.channel.send(f'{message.author.mention}, you don\'t have any points yet!')


async def get_leaderboard(message):
    data = load_activity_data()
    user_data = {k: v for k, v in data.items() if k != 'last_deterioration'}
    sorted_data = sorted(user_data.items(), key=lambda x: x[1]['points'], reverse=True)
    leaderboard = ''
    for i, (user_id, user_data) in enumerate(sorted_data[:5]):
        leaderboard += f"{i+1}. {user_data['name']} - {user_data['points']} points\n"
    await message.channel.send(f"Sure! Here's the leaderboard:\n{leaderboard}")


async def make_hydrate(message):
    target_user = None
    for mention in message.mentions:
        if mention != bot.user:
            target_user = mention
            break

    if target_user is None:
        await message.channel.send('You need to mention the user you want to make hydrate!')
        return

    reward_cost = 10
    user_id = str(message.author.id)
    activity_data = load_activity_data()

    if user_id in activity_data and activity_data[user_id]['points'] >= reward_cost:
        activity_data[user_id]['points'] -= reward_cost
        save_activity_data(activity_data)
        await message.channel.send(f'You heard them {target_user.mention}, bottoms up!  It\'s time for hydration!')
    else:
        await message.channel.send(f'Sorry {message.author.mention}, you don\'t have enough points right now!')


async def get_time(message):
    country_name = message.content.split('what time is it in')[-1].strip().strip(string.punctuation)

    # Map country names to their time zones
    time_zones = {
        'usa': 'America/New_York',  # You can use different time zones like 'America/Los_Angeles'
        'uk': 'Europe/London',
        'australia': 'Australia/Sydney',
        # Add more countries as needed
    }

    if country_name in time_zones:
        time_zone = pytz.timezone(time_zones[country_name])
        current_time = datetime.datetime.now(time_zone).strftime('%Y-%m-%d %H:%M:%S')

        await message.channel.send(f'The current time in {country_name} is {current_time}')
    else:
        await message.channel.send(f'Unknown country: {country_name}')


async def what_is_kraz(message):
    await message.channel.send('A nerd!  Tehe!')


commands = {
    r'\bplay\b.*\bgame\b|\bgame\b.*\bplay\b': play_game,
    r'how\s+are\s+you': how_are_you,
    r'how\s+many\s+points': how_many_points,
    r'leaderboard': get_leaderboard,
    r'make.*hydrate': make_hydrate,
    r'what\s+time\s+is\s+it\s+in': get_time,
    r'what\s+is\s+kraz': what_is_kraz,
    # Add more commands as needed
}


# Event that triggers when the bot is ready
@bot.event
async def on_ready():
    """Event that triggers when the bot is ready"""
    deteriorate_points()
    print(f'{bot.user.name} has connected to Discord!')


# Event that triggers when a message is received
@bot.event
async def on_message(message):
    """Event that triggers when a message is received"""
    if message.author == bot.user:  # Don't track activity for the bot itself
        return

    update_user_activity(message.author.id, message.author.name)

    text = message.content.lower()

    if bot.user.mentioned_in(message):
        # Check if the message matches any command
        for pattern, handler in commands.items():
            if re.findall(pattern, text):
                await handler(message)
                return
            
        if message.content.endswith('?'):
            responses = [
                'It is certain',
                'It is decidedly so',
                'Without a doubt',
                'Yes definitely',
                'You may rely on it',
                'As I see it, yes',
                'Most likely',
                'Outlook good',
                'Yes',
                'Signs point to yes',
                'Reply hazy try again',
                'Ask again later',
                'Better not tell you now',
                'Cannot predict now',
                'Concentrate and ask again',
                'Don\'t count on it',
                'My reply is no',
                'My sources say no',
                'Outlook not so good',
                'Very doubtful'
            ]
            await message.channel.send(random.choice(responses))
            return

        await sentiment_response(message)

    if check_whats_up(text):
        await message.channel.send(f'Chicken butt!')
        return

    await bot.process_commands(message)


# Play Rock Paper Scissors
async def rock_paper_scissors(message):
    """Play Rock Paper Scissors with the user"""
    await message.channel.send("Pick an option: rock, paper, or scissors! Don't worry, I won't cheat.")

    # Wait for the user's response
    def check(response):
        """Check if the response is from the same user and in the same channel"""
        return response.author == message.author and response.channel == message.channel
    try:
        response = await bot.wait_for('message', check=check, timeout=30)
        user_choice = response.content.lower()
        # Generate the bot's choice
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        await message.channel.send(f"I chose {bot_choice}!")
        # Determine the winner
        if user_choice == bot_choice:
            await message.channel.send("It's a tie!")
        elif (user_choice == 'rock' and bot_choice == 'scissors') or \
             (user_choice == 'paper' and bot_choice == 'rock') or \
             (user_choice == 'scissors' and bot_choice == 'paper'):
            await message.channel.send("You win! Congratulations!")
        else:
            await message.channel.send("I win! Yay!")
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to respond!")


# Load the current activity data from the JSON file
def load_activity_data():
    """Load the current activity data from the JSON file"""
    try:
        with open('E:\Code Projects\DiscordBot\\activity_data.json', 'r') as f:
            data = f.read()
            if not data:  # Check if the file is empty
                return {}
            return json.loads(data)
    except FileNotFoundError:
        return {}


# Save the activity data to the JSON file
def save_activity_data(data):
    """Save the activity data to the JSON file"""
    with open('E:\Code Projects\DiscordBot\\activity_data.json', 'w') as f:
        json.dump(data, f, indent=2)


# Update the user activity and points
def update_user_activity(id, name):
    """Update the user activity and points"""
    activity_data = load_activity_data()
    user_id = str(id)
    user_name = str(name)

    if user_id not in activity_data:
        activity_data[user_id] = {'name': user_name, 'points': 0, 'last_active': None, 'streak': 0}

    user_data = activity_data[user_id]

    # Calculate the streak
    today = datetime.date.today()

    if user_data['last_active'] is not None:
        last_active = datetime.date.fromisoformat(user_data['last_active'])
        if (today - last_active).days == 1:
            user_data['streak'] += 1
        elif today != last_active:
            user_data['streak'] = 1

    # Calculate the points earned
    if user_data['streak'] < 2:
        points_earned = 1
    elif user_data['streak'] < 7:
        points_earned = 2
    else:
        points_earned = 3

    user_data['points'] += points_earned
    user_data['last_active'] = today.isoformat()

    save_activity_data(activity_data)


# Deteriorate points for inactive users
def deteriorate_points():
    """Deteriorate points for inactive users"""
    activity_data = load_activity_data()

    # Check if we've already run today
    if 'last_deterioration' in activity_data and activity_data['last_deterioration'] == datetime.date.today().isoformat():
        return

    for user_id, user_data in activity_data.items():
        if user_id == 'last_deterioration':
            continue

        last_active = datetime.date.fromisoformat(user_data['last_active'])
        days_inactive = (datetime.date.today() - last_active).days

        if days_inactive > 7:
            # Calculate the number of days the user has been inactive beyond 7 days
            # since the last deterioration
            if 'days_inactive_beyond_7' not in user_data:
                user_data['days_inactive_beyond_7'] = 0

            days_inactive_beyond_7 = days_inactive - 7
            points_to_remove = (days_inactive_beyond_7 - user_data.get('days_inactive_beyond_7', 0)) * 5

            print(f"Decreasing {user_data['name']}'s points by {points_to_remove}")
            user_data['points'] = max(0, user_data['points'] - points_to_remove)

            # Update the number of days the user has been inactive beyond 7 days
            user_data['days_inactive_beyond_7'] = days_inactive_beyond_7

    activity_data['last_deterioration'] = datetime.date.today().isoformat()
    save_activity_data(activity_data)


def check_whats_up(message):
    """Check if the message contains 'what's up'"""
    pattern = r"(?i)\bwhat\'?s?\s+up\b"
    if re.search(pattern, message):
        return True
    else:
        return False


# Respond to generic messages with basic sentiment analysis
async def sentiment_response(message):
        """Respond to generic messages with basic sentiment analysis"""
        sentiment = sia.polarity_scores(message.content)

        if sentiment['compound'] > 0:
            await message.channel.send(f"Thanks for the kind words, {message.author.mention}!")
        elif sentiment['compound'] < 0:
            await message.channel.send(f"Aww, sorry to hear that, {message.author.mention}.")
        else:
            await message.channel.send(f"Hello {message.author.mention}!")


# Get token from .env file
bot.run(os.getenv('TOKEN'))