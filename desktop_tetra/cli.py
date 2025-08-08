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
from .interaction.sim.engine import SimEngine


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


@cli.group()
def sim() -> None:
    """Simulation controls"""


@sim.command("start")
@click.option("--hz", type=int, default=4)
@click.option("--seed", type=int, default=0)
def sim_start(hz: int, seed: int) -> None:
    eng = SimEngine.instance(tick_hz=hz, seed=seed)
    eng.start()
    time.sleep(0.2)
    click.echo(json.dumps({"sim": "started", "nodes": len(eng.snapshot().get("order", []))}, indent=2))


@sim.command("stop")
def sim_stop() -> None:
    eng = SimEngine.instance()
    eng.stop()
    click.echo(json.dumps({"sim": "stopped"}, indent=2))


@sim.command("status")
def sim_status() -> None:
    eng = SimEngine.instance_if_running()
    click.echo(json.dumps({"running": eng is not None, "nodes": (len(eng.snapshot().get("order", [])) if eng else 0)}, indent=2))


@cli.command("goal")
@click.argument("goal", type=str)
@click.option("--provider", type=str, default="openai", help="openai|lmstudio|xai|anthropic|local")
@click.option("--model", type=str, default="gpt-4o-mini")
@click.option("--api-key", type=str, default=None)
@click.option("--base-url", type=str, default=None)
@click.option("--os", "os_override", type=str, default=None, help="Force platform: sim|darwin|windows")
@click.option("--context", type=str, default=None, help="JSON string with hints")
@click.option("--continuous/--no-continuous", default=False)
@click.option("--infinite/--no-infinite", default=False)
@click.option("--max-cycles", type=int, default=10)
@click.option("--timeout", type=float, default=120.0)
@click.option("--success", type=str, default=None, help='JSON selector, e.g. {"role":"StaticText","title":"Done"}')
def goal_cmd(goal: str, provider: str, model: str, api_key: Optional[str], base_url: Optional[str], os_override: Optional[str], context: Optional[str], continuous: bool, infinite: bool, max_cycles: int, timeout: float, success: Optional[str]) -> None:
    ctx = None
    if context:
        try:
            ctx = json.loads(context)
        except json.JSONDecodeError:
            raise click.ClickException("--context must be valid JSON")
    success_sel = None
    if success:
        try:
            success_sel = json.loads(success)
        except json.JSONDecodeError:
            raise click.ClickException("--success must be valid JSON selector")
    LiveEngine.instance().start()
    agent = Agent(model=model, provider=provider, api_key=api_key, base_url=base_url, os_override=os_override)
    if infinite or continuous:
        if infinite:
            # Run with unbounded cycles/time (practically high caps)
            out = agent.run_continuous(goal, context=ctx, success=success_sel, max_cycles=10**9, max_time_seconds=10**9)
        else:
            out = agent.run_continuous(goal, context=ctx, success=success_sel, max_cycles=max_cycles, max_time_seconds=timeout)
    else:
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
