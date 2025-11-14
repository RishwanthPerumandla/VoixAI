from rich.console import Console

console = Console()

def log(msg):
    console.print(f"[bold cyan]{msg}[/bold cyan]")
