import os
import sys
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import requests
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel


GITHUB_API_URL = "https://api.github.com"
console = Console()


def get_github_session(token: Optional[str] = None):
    """Crea una sessione GitHub autenticata."""
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        console.print(
            "[bold red]Errore:[/bold red] devi impostare la variabile d'ambiente GITHUB_TOKEN "
            "o passare il token con --token",
            style="red"
        )
        console.print("Esempio: [cyan]export GITHUB_TOKEN=tuo_token_personale[/cyan]")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pr-review-stats-script"
    })
    return session


def validate_date(date_string: str) -> str:
    """Valida il formato della data."""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return date_string
    except ValueError:
        raise click.BadParameter(f"Data non valida: {date_string}. Usa il formato YYYY-MM-DD")


def search_merged_prs(session, org: str, author: str, from_date: str, to_date: str, verbose: bool = False):
    """
    Restituisce la lista di tutti gli item (issues/PR) che matchano la query.
    Usiamo la Search API di GitHub.
    """
    query = (
        f"org:{org} "
        f"is:pr "
        f"is:merged "
        f"author:{author} "
        f"merged:{from_date}..{to_date}"
    )

    if verbose:
        console.print(f"[dim]Query di ricerca:[/dim] {query}")

    page = 1
    per_page = 100
    all_items = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=not verbose
    ) as progress:
        task = progress.add_task("Cercando PR...", total=None)
        
        while True:
            params = {
                "q": query,
                "per_page": per_page,
                "page": page,
            }
            resp = session.get(f"{GITHUB_API_URL}/search/issues", params=params)
            
            if resp.status_code == 403:
                console.print("[bold red]Errore:[/bold red] Rate limit raggiunto o permessi insufficienti")
                console.print(f"[dim]Status: {resp.status_code}[/dim]")
                if "rate limit" in resp.text.lower():
                    console.print("[yellow]Suggerimento:[/yellow] Attendi qualche minuto e riprova")
                sys.exit(1)
            
            if resp.status_code != 200:
                console.print(f"[bold red]Errore nella chiamata alla Search API:[/bold red]")
                console.print(f"Status: {resp.status_code}")
                console.print(f"Risposta: {resp.text}")
                sys.exit(1)

            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            all_items.extend(items)
            if verbose:
                progress.update(task, description=f"Trovate {len(all_items)} PR...")

            # Se abbiamo meno di per_page elementi, non ci sono altre pagine
            if len(items) < per_page:
                break

            page += 1

    console.print(f"[green]✓[/green] Trovate [bold]{len(all_items)}[/bold] PR mergiate nel range indicato.")
    return all_items


def get_reviews_for_pr(session, pr_api_url: str, verbose: bool = False):
    """
    pr_api_url è tipo https://api.github.com/repos/{owner}/{repo}/pulls/{number}
    Per le review chiamiamo {pr_api_url}/reviews
    """
    reviews_url = pr_api_url.rstrip("/") + "/reviews"
    resp = session.get(reviews_url)
    if resp.status_code != 200:
        if verbose:
            console.print(f"  [yellow][WARN][/yellow] Impossibile leggere le review per {pr_api_url}: "
                  f"{resp.status_code}")
        return []

    return resp.json()


def analyze_prs(session, items: List[Dict], verbose: bool = False) -> Dict:
    """Analizza le PR e restituisce i risultati."""
    senza_bocciature = []
    bocciate_poi_approvate = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=not verbose
    ) as progress:
        task = progress.add_task("Analizzando PR...", total=len(items))
        
        for item in items:
            pr_info = item.get("pull_request")
            if not pr_info:
                continue

            pr_url = pr_info["url"]
            number = item["number"]
            title = item["title"]
            html_url = item.get("html_url", "")
            repo = item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else ""

            reviews = get_reviews_for_pr(session, pr_url, verbose)
            states = {r.get("state") for r in reviews}

            has_changes_requested = "CHANGES_REQUESTED" in states

            pr_data = {
                "number": number,
                "title": title,
                "url": html_url,
                "repo": repo,
                "merged_at": item.get("pull_request", {}).get("merged_at", "")
            }

            if has_changes_requested:
                bocciate_poi_approvate.append(pr_data)
            else:
                senza_bocciature.append(pr_data)

            if verbose:
                progress.update(task, advance=1, description=f"Analizzate {len(senza_bocciature) + len(bocciate_poi_approvate)}/{len(items)} PR...")

    return {
        "senza_bocciature": senza_bocciature,
        "bocciate_poi_approvate": bocciate_poi_approvate,
        "totale": len(senza_bocciature) + len(bocciate_poi_approvate)
    }


def print_table_results(results: Dict, show_details: bool = True):
    """Stampa i risultati in formato tabella."""
    table = Table(title="Risultati Analisi PR", show_header=True, header_style="bold magenta")
    table.add_column("Categoria", style="cyan", no_wrap=True)
    table.add_column("Numero", justify="right", style="green")
    
    table.add_row(
        "PR approvate senza bocciature",
        str(len(results["senza_bocciature"]))
    )
    table.add_row(
        "PR bocciate e poi approvate",
        str(len(results["bocciate_poi_approvate"]))
    )
    table.add_row(
        "[bold]Totale PR considerate[/bold]",
        f"[bold]{results['totale']}[/bold]"
    )
    
    console.print()
    console.print(table)
    
    if show_details and results["totale"] > 0:
        console.print()
        
        if results["senza_bocciature"]:
            console.print(Panel.fit(
                "\n".join([f"#{pr['number']} - {pr['title']}" for pr in results["senza_bocciature"]]),
                title="[green]PR Approvate Senza Bocciature[/green]",
                border_style="green"
            ))
        
        if results["bocciate_poi_approvate"]:
            console.print()
            console.print(Panel.fit(
                "\n".join([f"#{pr['number']} - {pr['title']}" for pr in results["bocciate_poi_approvate"]]),
                title="[yellow]PR Bocciate e Poi Approvate[/yellow]",
                border_style="yellow"
            ))


def export_json(results: Dict, filename: str):
    """Esporta i risultati in formato JSON."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    console.print(f"[green]✓[/green] Risultati esportati in [cyan]{filename}[/cyan]")


def export_csv(results: Dict, filename: str):
    """Esporta i risultati in formato CSV."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Categoria", "Numero PR", "Titolo", "Repository", "URL", "Data Merge"])
        
        for pr in results["senza_bocciature"]:
            writer.writerow([
                "Approvata senza bocciature",
                pr["number"],
                pr["title"],
                pr["repo"],
                pr["url"],
                pr["merged_at"]
            ])
        
        for pr in results["bocciate_poi_approvate"]:
            writer.writerow([
                "Bocciata e poi approvata",
                pr["number"],
                pr["title"],
                pr["repo"],
                pr["url"],
                pr["merged_at"]
            ])
    
    console.print(f"[green]✓[/green] Risultati esportati in [cyan]{filename}[/cyan]")


@click.command()
@click.option("--org", required=True, help="Organizzazione GitHub (es. Gamindo)")
@click.option("--author", required=True, help="Autore delle PR (es. evercloud)")
@click.option("--from-date", required=True, callback=lambda ctx, param, value: validate_date(value) if value else None, help="Data inizio (YYYY-MM-DD)")
@click.option("--to-date", required=True, callback=lambda ctx, param, value: validate_date(value) if value else None, help="Data fine (YYYY-MM-DD)")
@click.option("--token", help="Token GitHub (alternativa a GITHUB_TOKEN env var)")
@click.option("--output", type=click.Choice(["table", "json", "csv"], case_sensitive=False), default="table", help="Formato di output")
@click.option("--export", help="File di esportazione (solo per JSON/CSV)")
@click.option("--verbose", "-v", is_flag=True, help="Mostra informazioni dettagliate")
@click.option("--no-details", is_flag=True, help="Non mostrare il dettaglio delle PR")
def main(org, author, from_date, to_date, token, output, export, verbose, no_details):
    """
    Analizza le Pull Request mergiate di un autore in un'organizzazione GitHub.
    
    Distingue tra PR approvate senza bocciature e PR bocciate e poi approvate.
    """
    session = get_github_session(token)

    items = search_merged_prs(
        session,
        org=org,
        author=author,
        from_date=from_date,
        to_date=to_date,
        verbose=verbose
    )

    if not items:
        console.print("[yellow]Nessuna PR trovata nel periodo specificato.[/yellow]")
        return

    results = analyze_prs(session, items, verbose=verbose)
    
    # Aggiungi statistiche ai risultati per export
    results["statistiche"] = {
        "senza_bocciature": len(results["senza_bocciature"]),
        "bocciate_poi_approvate": len(results["bocciate_poi_approvate"]),
        "totale": results["totale"]
    }

    # Output
    if output == "json":
        if export:
            export_json(results, export)
        else:
            console.print(json.dumps(results, indent=2, ensure_ascii=False))
    elif output == "csv":
        if not export:
            export = "pr_results.csv"
        export_csv(results, export)
    else:  # table
        print_table_results(results, show_details=not no_details)
        if export:
            if export.endswith('.json'):
                export_json(results, export)
            elif export.endswith('.csv'):
                export_csv(results, export)
            else:
                console.print("[yellow]Formato file non riconosciuto. Usa .json o .csv[/yellow]")


if __name__ == "__main__":
    main()
