" The monitors plugin "
import subprocess
from typing import Any
from .interface import Plugin

from ..ipc import hyprctlJSON


def configure_monitors(monitors, screenid: str, pos_x: int, pos_y: int) -> None:
    "Apply the configuration change"
    x_offset = -pos_x if pos_x < 0 else 0
    y_offset = -pos_y if pos_y < 0 else 0

    min_x = pos_x
    min_y = pos_y

    command = ["wlr-randr"]
    other_monitors = [mon for mon in monitors if mon["name"] != screenid]
    for mon in other_monitors:
        min_x = min(min_x, mon["x"])
        min_y = min(min_y, mon["y"])
    x_offset = -min_x
    y_offset = -min_y
    for mon in other_monitors:
        command.extend(
            [
                "--output",
                mon["name"],
                "--pos",
                f"{mon['x']+x_offset},{mon['y']+y_offset}",
            ]
        )

    command.extend(
        ["--output", screenid, "--pos", f"{pos_x+x_offset},{pos_y+y_offset}"]
    )
    subprocess.call(command)


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    async def load_config(self, config) -> None:
        await super().load_config(config)
        monitors = await hyprctlJSON("monitors")
        for monitor in monitors:
            await self.event_monitoradded(
                monitor["name"], no_default=True, monitors=monitors
            )

    async def event_monitoradded(
        self, screenid, no_default=False, monitors: list | None = None
    ) -> None:
        "Triggers when a monitor is plugged"
        screenid = screenid.strip()

        if not monitors:
            monitors: list[dict[str, Any]] = await hyprctlJSON("monitors")

        for mon in monitors:
            if mon["name"].startswith(screenid):
                mon_name = mon["description"]
                break
        else:
            self.log.info("Monitor %s not found", screenid)
            return

        mon_by_name = {m["name"]: m for m in monitors}

        newmon = mon_by_name[screenid]

        for mon_pattern, conf in self.config["placement"].items():
            if mon_pattern in mon_name:
                for placement, mon_name in conf.items():
                    ref = mon_by_name[mon_name]
                    if ref:
                        place = placement.lower()
                        if place == "topof":
                            x: int = ref["x"]
                            y: int = ref["y"] - newmon["height"]
                        elif place == "bottomof":
                            x: int = ref["x"]
                            y: int = ref["y"] + ref["height"]
                        elif place == "leftof":
                            x: int = ref["x"] - newmon["width"]
                            y: int = ref["y"]
                        else:  # rightof
                            x: int = ref["x"] + ref["width"]
                            y: int = ref["y"]

                        configure_monitors(monitors, screenid, x, y)
                        return
        if not no_default:
            default_command = self.config.get("unknown")
            if default_command:
                subprocess.call(default_command, shell=True)
