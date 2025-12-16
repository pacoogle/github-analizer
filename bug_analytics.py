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
        "User-Agent": "bug-analytics-script"
    })
    return session


def validate_date(date_string: str) -> str:
    """Valida il formato della data."""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return date_string
    except ValueError:
        raise click.BadParameter(f"Data non valida: {date_string}. Usa il formato YYYY-MM-DD")


def has_bug_label(item: Dict) -> bool:
    """Verifica se un'issue ha la label 'bug' (case-insensitive)."""
    labels = item.get("labels", [])
    for label in labels:
        if label.get("name", "").lower() == "bug":
            return True
    return False


def search_issues(
    session,
    org: str,
    from_date: str,
    to_date: str,
    is_bug: Optional[bool] = None,
    verbose: bool = False
):
    """
    Cerca issues nell'organizzazione nel periodo specificato.
    
    Args:
        session: Sessione GitHub autenticata
        org: Nome dell'organizzazione
        from_date: Data inizio (YYYY-MM-DD)
        to_date: Data fine (YYYY-MM-DD)
        is_bug: True per bug, False per non-bug, None per tutte
        verbose: Mostra informazioni dettagliate
    """
    # Costruisce la query base per issues (non PR)
    # Cerchiamo tutte le issues e poi filtriamo per label nel codice
    # Questo è più affidabile perché -label:bug può escludere issues senza labels
    query_parts = [
        f"org:{org}",
        "is:issue",
        f"created:{from_date}..{to_date}"
    ]
    
    # Se cerchiamo solo bug, possiamo usare il filtro label nella query per efficienza
    if is_bug is True:
        query_parts.append("label:bug")
    
    query = " ".join(query_parts)
    
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
        task_type = "bug" if is_bug is True else ("non-bug" if is_bug is False else "issues")
        task = progress.add_task(f"Cercando {task_type}...", total=None)
        
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
            
            # Se non stiamo filtrando per bug nella query, filtriamo nel codice
            if is_bug is False:
                items = [item for item in items if not has_bug_label(item)]
            elif is_bug is None:
                # Non filtriamo, prendiamo tutte
                pass
            
            all_items.extend(items)
            if verbose:
                progress.update(task, description=f"Trovate {len(all_items)} {task_type}...")
            
            # Se abbiamo meno di per_page elementi, non ci sono altre pagine
            if len(items) < per_page:
                break
            
            page += 1
    
    if verbose:
        console.print(f"[green]✓[/green] Trovate [bold]{len(all_items)}[/bold] {task_type} create nel periodo.")
    
    return all_items


def search_merged_prs(
    session,
    org: str,
    from_date: str,
    to_date: str,
    is_bug: Optional[bool] = None,
    verbose: bool = False
):
    """
    Cerca PR merged con/senza label bug nel periodo specificato.
    
    Args:
        session: Sessione GitHub autenticata
        org: Nome dell'organizzazione
        from_date: Data inizio (YYYY-MM-DD)
        to_date: Data fine (YYYY-MM-DD)
        is_bug: True per bug (label:bug), False per non-bug (-label:bug), None per tutte
        verbose: Mostra informazioni dettagliate
    """
    # Costruisce la query per PR merged
    query_parts = [
        f"org:{org}",
        "is:pr",
        "is:merged",
        f"merged:{from_date}..{to_date}"
    ]
    
    # Filtra per label bug o non-bug
    if is_bug is True:
        query_parts.append("label:bug")
    elif is_bug is False:
        query_parts.append("-label:bug")
    
    query = " ".join(query_parts)
    
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
        task_type = "bug" if is_bug is True else ("non-bug" if is_bug is False else "PR")
        task = progress.add_task(f"Cercando PR merged ({task_type})...", total=None)
        
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
            
            # Se non stiamo filtrando per bug nella query, filtriamo nel codice
            if is_bug is False:
                items = [item for item in items if not has_bug_label(item)]
            elif is_bug is None:
                # Non filtriamo, prendiamo tutte
                pass
            
            all_items.extend(items)
            if verbose:
                progress.update(task, description=f"Trovate {len(all_items)} PR merged ({task_type})...")
            
            # Se abbiamo meno di per_page elementi, non ci sono altre pagine
            if len(items) < per_page:
                break
            
            page += 1
    
    if verbose:
        task_type = "bug" if is_bug is True else ("non-bug" if is_bug is False else "PR")
        console.print(f"[green]✓[/green] Trovate [bold]{len(all_items)}[/bold] PR merged ({task_type}) nel periodo.")
    
    return all_items


def analyze_issues(
    session,
    org: str,
    from_date: str,
    to_date: str,
    verbose: bool = False
) -> Dict:
    """
    Analizza bug e non-bug aperti e risolti nel periodo specificato.
    """
    if verbose:
        console.print("[cyan]Fase 1: Cercando bug aperti...[/cyan]")
    # Cerca bug aperti nel periodo
    bug_aperti = search_issues(session, org, from_date, to_date, is_bug=True, verbose=verbose)
    
    if verbose:
        console.print("[cyan]Fase 2: Cercando non-bug aperti...[/cyan]")
    # Cerca non-bug aperti nel periodo
    non_bug_aperti = search_issues(session, org, from_date, to_date, is_bug=False, verbose=verbose)
    
    if verbose:
        console.print("[cyan]Fase 3: Cercando bug risolti (PR merged con label bug)...[/cyan]")
    # Cerca bug risolti (PR merged con label bug) nel periodo
    bug_chiusi = search_merged_prs(session, org, from_date, to_date, is_bug=True, verbose=verbose)
    
    if verbose:
        console.print("[cyan]Fase 4: Cercando non-bug risolti (PR merged senza label bug)...[/cyan]")
    # Cerca non-bug risolti (PR merged senza label bug) nel periodo
    non_bug_chiusi = search_merged_prs(session, org, from_date, to_date, is_bug=False, verbose=verbose)
    
    if verbose:
        console.print(f"[dim]Bug aperti trovati: {len(bug_aperti)}[/dim]")
        console.print(f"[dim]Non-bug aperti trovati: {len(non_bug_aperti)}[/dim]")
        console.print(f"[dim]Bug chiusi trovati: {len(bug_chiusi)}[/dim]")
        console.print(f"[dim]Non-bug chiusi trovati: {len(non_bug_chiusi)}[/dim]")
    
    # Filtra le issues aperte: solo quelle create nel periodo che sono ancora aperte
    # Le issues chiuse nel periodo vengono conteggiate solo come "risolte"
    bug_aperti_filtrati = [
        item for item in bug_aperti
        if item["state"] == "open"
    ]
    
    non_bug_aperti_filtrati = [
        item for item in non_bug_aperti
        if item["state"] == "open"
    ]
    
    if verbose:
        console.print(f"[dim]Bug aperti ancora aperti: {len(bug_aperti_filtrati)}[/dim]")
        console.print(f"[dim]Non-bug aperti ancora aperti: {len(non_bug_aperti_filtrati)}[/dim]")
    
    # Prepara i dati per il risultato
    def format_issue(item):
        labels = [label["name"] for label in item.get("labels", [])]
        repo = item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else ""
        # Per le PR merged, usiamo merged_at invece di closed_at
        merged_at = item.get("pull_request", {}).get("merged_at", "") if item.get("pull_request") else ""
        return {
            "number": item["number"],
            "title": item["title"],
            "url": item.get("html_url", ""),
            "repo": repo,
            "state": item["state"],
            "created_at": item.get("created_at", ""),
            "closed_at": merged_at or item.get("closed_at", ""),
            "merged_at": merged_at,
            "labels": labels
        }
    
    def format_pr(item):
        """Formatta una PR come se fosse un'issue per compatibilità."""
        labels = [label["name"] for label in item.get("labels", [])]
        repo = item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else ""
        merged_at = item.get("pull_request", {}).get("merged_at", "") if item.get("pull_request") else ""
        return {
            "number": item["number"],
            "title": item["title"],
            "url": item.get("html_url", ""),
            "repo": repo,
            "state": "closed" if merged_at else item.get("state", ""),
            "created_at": item.get("created_at", ""),
            "closed_at": merged_at,
            "merged_at": merged_at,
            "labels": labels
        }
    
    return {
        "bug": {
            "aperti": [format_issue(item) for item in bug_aperti_filtrati],
            "risolti": [format_pr(item) for item in bug_chiusi],
            "totale_aperti": len(bug_aperti_filtrati),
            "totale_risolti": len(bug_chiusi)
        },
        "non_bug": {
            "aperti": [format_issue(item) for item in non_bug_aperti_filtrati],
            "risolti": [format_pr(item) for item in non_bug_chiusi],
            "totale_aperti": len(non_bug_aperti_filtrati),
            "totale_risolti": len(non_bug_chiusi)
        },
        "periodo": {
            "da": from_date,
            "a": to_date
        }
    }


def print_table_results(results: Dict, show_details: bool = True):
    """Stampa i risultati in formato tabella."""
    table = Table(title="Analisi Bug e Non-Bug", show_header=True, header_style="bold magenta")
    table.add_column("Categoria", style="cyan", no_wrap=True)
    table.add_column("Aperti", justify="right", style="yellow")
    table.add_column("Risolti", justify="right", style="green")
    table.add_column("Totale", justify="right", style="bold")
    
    bug_aperti = results["bug"]["totale_aperti"]
    bug_risolti = results["bug"]["totale_risolti"]
    bug_totale = bug_aperti + bug_risolti
    
    non_bug_aperti = results["non_bug"]["totale_aperti"]
    non_bug_risolti = results["non_bug"]["totale_risolti"]
    non_bug_totale = non_bug_aperti + non_bug_risolti
    
    table.add_row(
        "[bold red]Bug[/bold red]",
        str(bug_aperti),
        str(bug_risolti),
        f"[bold]{bug_totale}[/bold]"
    )
    table.add_row(
        "[bold blue]Non-Bug[/bold blue]",
        str(non_bug_aperti),
        str(non_bug_risolti),
        f"[bold]{non_bug_totale}[/bold]"
    )
    table.add_row(
        "[bold]Totale[/bold]",
        f"[bold]{bug_aperti + non_bug_aperti}[/bold]",
        f"[bold]{bug_risolti + non_bug_risolti}[/bold]",
        f"[bold]{bug_totale + non_bug_totale}[/bold]"
    )
    
    console.print()
    console.print(table)
    console.print(f"[dim]Periodo: {results['periodo']['da']} - {results['periodo']['a']}[/dim]")
    
    if show_details:
        console.print()
        
        if results["bug"]["aperti"]:
            console.print(Panel.fit(
                "\n".join([
                    f"#{issue['number']} - {issue['title']} ({issue['repo']})"
                    for issue in results["bug"]["aperti"]
                ]),
                title="[yellow]Bug Aperti[/yellow]",
                border_style="yellow"
            ))
        
        if results["bug"]["risolti"]:
            console.print()
            console.print(Panel.fit(
                "\n".join([
                    f"#{issue['number']} - {issue['title']} ({issue['repo']})"
                    for issue in results["bug"]["risolti"]
                ]),
                title="[green]Bug Risolti[/green]",
                border_style="green"
            ))
        
        if results["non_bug"]["aperti"]:
            console.print()
            console.print(Panel.fit(
                "\n".join([
                    f"#{issue['number']} - {issue['title']} ({issue['repo']})"
                    for issue in results["non_bug"]["aperti"]
                ]),
                title="[yellow]Non-Bug Aperti[/yellow]",
                border_style="yellow"
            ))
        
        if results["non_bug"]["risolti"]:
            console.print()
            console.print(Panel.fit(
                "\n".join([
                    f"#{issue['number']} - {issue['title']} ({issue['repo']})"
                    for issue in results["non_bug"]["risolti"]
                ]),
                title="[green]Non-Bug Risolti[/green]",
                border_style="green"
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
        writer.writerow([
            "Tipo", "Stato", "Numero", "Titolo", "Repository", "URL",
            "Data Creazione", "Data Chiusura", "Labels"
        ])
        
        for issue in results["bug"]["aperti"]:
            writer.writerow([
                "Bug",
                "Aperto",
                issue["number"],
                issue["title"],
                issue["repo"],
                issue["url"],
                issue["created_at"],
                issue["closed_at"],
                ", ".join(issue["labels"])
            ])
        
        for issue in results["bug"]["risolti"]:
            writer.writerow([
                "Bug",
                "Risolto",
                issue["number"],
                issue["title"],
                issue["repo"],
                issue["url"],
                issue["created_at"],
                issue["closed_at"],
                ", ".join(issue["labels"])
            ])
        
        for issue in results["non_bug"]["aperti"]:
            writer.writerow([
                "Non-Bug",
                "Aperto",
                issue["number"],
                issue["title"],
                issue["repo"],
                issue["url"],
                issue["created_at"],
                issue["closed_at"],
                ", ".join(issue["labels"])
            ])
        
        for issue in results["non_bug"]["risolti"]:
            writer.writerow([
                "Non-Bug",
                "Risolto",
                issue["number"],
                issue["title"],
                issue["repo"],
                issue["url"],
                issue["created_at"],
                issue["closed_at"],
                ", ".join(issue["labels"])
            ])
    
    console.print(f"[green]✓[/green] Risultati esportati in [cyan]{filename}[/cyan]")


@click.command()
@click.option("--org", required=True, help="Organizzazione GitHub (es. Gamindo)")
@click.option("--from-date", required=True, callback=lambda ctx, param, value: validate_date(value) if value else None, help="Data inizio (YYYY-MM-DD)")
@click.option("--to-date", required=True, callback=lambda ctx, param, value: validate_date(value) if value else None, help="Data fine (YYYY-MM-DD)")
@click.option("--token", help="Token GitHub (alternativa a GITHUB_TOKEN env var)")
@click.option("--output", type=click.Choice(["table", "json", "csv"], case_sensitive=False), default="table", help="Formato di output")
@click.option("--export", help="File di esportazione (solo per JSON/CSV)")
@click.option("--verbose", "-v", is_flag=True, help="Mostra informazioni dettagliate")
@click.option("--no-details", is_flag=True, help="Non mostrare il dettaglio delle issues")
def main(org, from_date, to_date, token, output, export, verbose, no_details):
    """
    Analizza bug e non-bug aperti e risolti in un'organizzazione GitHub nel periodo specificato.
    
    Le issues sono classificate come "bug" se hanno la label "bug", altrimenti come "non-bug".
    """
    session = get_github_session(token)
    
    if verbose:
        console.print(f"[cyan]Analisi issues per organizzazione:[/cyan] {org}")
        console.print(f"[cyan]Periodo:[/cyan] {from_date} - {to_date}")
        console.print()
    
    results = analyze_issues(
        session,
        org=org,
        from_date=from_date,
        to_date=to_date,
        verbose=verbose
    )
    
    # Output
    if output == "json":
        if export:
            export_json(results, export)
        else:
            console.print(json.dumps(results, indent=2, ensure_ascii=False))
    elif output == "csv":
        if not export:
            export = "bug_results.csv"
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

