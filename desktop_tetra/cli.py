import json
import time
from typing import Optional

import click

from .ax import AXFinder
from .player import ActionPlayer
from .recorder import ActionRecorder
from .agent import Agent
from .interaction.livefeed import LiveFeed
from .interaction.engine import LiveEngine


@click.group()
def cli() -> None:
    """macOS/Windows Accessibility Agent CLI"""


@cli.command()
def info() -> None:
    finder = AXFinder()
    front_app = finder.get_frontmost_app_bundle_id()
    ax_enabled = finder.is_accessibility_enabled()
    click.echo(json.dumps({"accessibilityEnabled": ax_enabled, "frontmostApp": front_app}, indent=2))


@cli.group()
def live() -> None:
    """Live visual feed controls"""


@live.command("start")
@click.option("--monitor", type=int, default=1)
@click.option("--fps", type=int, default=4)
def live_start(monitor: int, fps: int) -> None:
    lf = LiveFeed(monitor_index=monitor, target_fps=fps)
    lf.start()
    time.sleep(0.5)
    snap = lf.snapshot()
    click.echo(json.dumps({"nodes": len(snap.get("order", []))}, indent=2))
    lf.stop()


@cli.command("press")
@click.option("--title", type=str, default=None)
@click.option("--role", type=str, default=None)
@click.option("--app", type=str, default=None)
@click.option("--timeout", type=float, default=3.0)
@click.option("--contains/--exact", default=True, help="Title match mode")
def press_cmd(title: Optional[str], role: Optional[str], app: Optional[str], timeout: float, contains: bool) -> None:
    finder = AXFinder()
    el = finder.find_element(title=title, role=role, app=app, timeout_seconds=timeout, contains=contains)
    if el is None:
        raise click.ClickException("Element not found")
    if not finder.press(el):
        raise click.ClickException("AXPress failed")


@cli.command("set")
@click.option("--title", type=str, default=None)
@click.option("--role", type=str, default=None)
@click.option("--app", type=str, default=None)
@click.option("--timeout", type=float, default=3.0)
@click.option("--value", type=str, required=True)
@click.option("--contains/--exact", default=True)
def set_cmd(title: Optional[str], role: Optional[str], app: Optional[str], timeout: float, value: str, contains: bool) -> None:
    finder = AXFinder()
    el = finder.find_element(title=title, role=role, app=app, timeout_seconds=timeout, contains=contains)
    if el is None:
        raise click.ClickException("Element not found")
    if not finder.set_value(el, value):
        raise click.ClickException("Set value failed")


@cli.command("scan")
@click.option("--app", type=str, default=None, help="Bundle id or name; default frontmost")
@click.option("--depth", type=int, default=4)
def scan_cmd(app: Optional[str], depth: int) -> None:
    finder = AXFinder()
    tree = finder.build_semantic_map(app=app, max_depth=depth)
    click.echo(json.dumps(tree, indent=2))


@cli.command("goal")
@click.argument("goal", type=str)
@click.option("--provider", type=str, default="openai", help="openai|lmstudio|xai|anthropic|local")
@click.option("--model", type=str, default="gpt-4o-mini")
@click.option("--api-key", type=str, default=None)
@click.option("--base-url", type=str, default=None)
@click.option("--os", "os_override", type=str, default=None, help="Force platform: darwin|windows")
@click.option("--context", type=str, default=None, help="JSON string with hints")
def goal_cmd(goal: str, provider: str, model: str, api_key: Optional[str], base_url: Optional[str], os_override: Optional[str], context: Optional[str]) -> None:
    ctx = None
    if context:
        try:
            ctx = json.loads(context)
        except json.JSONDecodeError:
            raise click.ClickException("--context must be valid JSON")
    # Ensure live engine is running to provide CRDT perception
    LiveEngine.instance().start()
    agent = Agent(model=model, provider=provider, api_key=api_key, base_url=base_url, os_override=os_override)
    plan = agent.plan(goal, context=ctx)
    results = agent.execute_steps(plan)
    out = {"plan": plan, "results": results}
    click.echo(json.dumps(out, indent=2))


@cli.command()
@click.option("--out", "out_path", type=str, required=True)
@click.option("--include-keys/--no-include-keys", default=False)
@click.option("--include-mouse/--no-include-mouse", default=False)
def record(out_path: str, include_keys: bool, include_mouse: bool) -> None:
    if not include_keys and not include_mouse:
        raise click.ClickException("Enable at least one: --include-keys or --include-mouse")
    recorder = ActionRecorder(include_keys=include_keys, include_mouse=include_mouse)
    click.echo("Recording... Press Ctrl+C to stop.")
    try:
        recorder.start()
        while True:
            recorder.tick(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        actions = recorder.stop()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=2)
        click.echo(f"Saved {len(actions)} actions to {out_path}")


@cli.command()
@click.option("--in", "in_path", type=str, required=True)
@click.option("--speed", type=float, default=1.0)
def play(in_path: str, speed: float) -> None:
    with open(in_path, "r", encoding="utf-8") as f:
        actions = json.load(f)
    player = ActionPlayer(speed_multiplier=speed)
    player.play(actions)


if __name__ == "__main__":
    cli()
