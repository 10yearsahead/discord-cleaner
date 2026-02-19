import requests
import time
import sys
import os
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

console = Console()
TOKEN_FILE = "tokens.txt"

def get_headers(token):
    clean_token = token.strip().replace('"', '').replace("'", "")
    return {
        "Authorization": clean_token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

def get_account_info(token):
    headers = get_headers(token)
    try:
        res = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=5)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def save_token(token):
    with open(TOKEN_FILE, "a") as f:
        f.write(f"{token.strip()}\n")

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return []
    with open(TOKEN_FILE, "r") as f:
        return list(set(line.strip() for line in f.readlines() if line.strip()))

def session_manager():
    tokens = load_tokens()
    valid_sessions = []
    
    if tokens:
        table = Table(box=None, padding=(0, 2), show_header=False)
        table.add_column("ID", style="magenta")
        table.add_column("USER", style="cyan")
        
        with console.status("[dim]Loading..."):
            for token in tokens:
                data = get_account_info(token)
                if data:
                    valid_sessions.append((token, data['username']))
                    table.add_row(f"[{len(valid_sessions)}]", data['username'])
        
        if valid_sessions:
            console.print("\n[bold white]Available Sessions:[/bold white]")
            console.print(table)
            choice = Prompt.ask("\n[bold magenta]❯ Select session[/bold magenta] [dim](1..n/new)[/dim]", default="1")
            if choice.lower() != 'new':
                try:
                    return valid_sessions[int(choice)-1][0]
                except:
                    pass

    new_token = console.input("\n[bold magenta]❯ Token:[/bold magenta] ", password=True)
    user_data = get_account_info(new_token)
    if user_data:
        if Prompt.ask("[dim]Save?[/dim]", choices=["y", "n"], default="y") == "y":
            save_token(new_token)
        return new_token
    return None

def main():
    console.clear()
    token = session_manager()
    if not token:
        console.print("[red]Unauthorized.[/red]")
        return
    
    user_data = get_account_info(token)
    headers = get_headers(token)
    
    console.print(f"\n[dim]Active:[/dim] [cyan]{user_data['username']}[/cyan]")
    channel_id = Prompt.ask("[bold cyan]❯ Channel ID[/bold cyan]")
    target = int(Prompt.ask("[bold cyan]❯ Amount[/bold cyan]", default="10"))

    deleted_count = 0
    last_id = None

    with Progress(
        SpinnerColumn(spinner_name="dots", style="magenta"),
        TextColumn("[white]{task.description}"),
        BarColumn(bar_width=20, style="dim", complete_style="cyan"),
        TextColumn("[bold magenta]{task.completed}/{task.total}"),
        console=console,
        transient=True
    ) as progress:
        
        task = progress.add_task("Wiping...", total=target)

        while deleted_count < target:
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"
            if last_id: url += f"&before={last_id}"
            
            res = requests.get(url, headers=headers)
            if res.status_code != 200: break
            
            messages = res.json()
            if not messages: break

            for msg in messages:
                if deleted_count >= target: break
                last_id = msg['id']

                if msg['author']['id'] == user_data['id']:
                    success = False
                    while not success:
                        del_res = requests.delete(
                            f"https://discord.com/api/v9/channels/{channel_id}/messages/{msg['id']}", 
                            headers=headers
                        )
                        
                        if del_res.status_code == 204:
                            deleted_count += 1
                            progress.update(task, advance=1)
                            success = True
                            time.sleep(0.8)
                        elif del_res.status_code == 429:
                            wait = del_res.json().get('retry_after', 2)
                            time.sleep(float(wait) + 0.2)
                        elif del_res.status_code == 403:
                            success = True 
                        else:
                            time.sleep(1)

    console.print(f"\n[bold cyan]CLEANED.[/bold cyan] [white]{deleted_count} messages removed.[/white]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
