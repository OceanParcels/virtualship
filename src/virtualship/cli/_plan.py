import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Collapsible,
    Input,
    Label,
    Rule,
    Select,
    Static,
    Switch,
)

from virtualship.models.location import Location
from virtualship.models.schedule import Schedule, Waypoint
from virtualship.models.ship_config import (
    ADCPConfig,
    ArgoFloatConfig,
    CTD_BGCConfig,
    CTDConfig,
    DrifterConfig,
    InstrumentType,
    ShipConfig,
    ShipUnderwaterSTConfig,
    XBTConfig,
)
from virtualship.models.space_time_region import (
    SpaceTimeRegion,
    SpatialRange,
    TimeRange,
)

# TODO: I wonder whether it would be a good idea to be able to recognise all the subcomponents of a pydantic model
# TODO: such as the instrument configuration, and be able to loop (?) rather than explicitly type each one out
# TODO: maybe in some kind of form where it's stored externally so as to facilitate it being in one place and helps there be more ease of adding instruments
# TODO: down the line without having to make changes in so many places...?
# TODO: but is this possible given the different requirements/units etc. that they all require?

# TODO: NEED TO MAKE SURE THE CHANGES OVERWRITTEN TO THE YAML FILES DO IT IN THE RIGHT ORDER, IT DOESN'T SAVE PROPERLY AT CURRENT
# TODO: implement action for 'Save' button
# TODO: probably with a second pop up that says "are you sure you want to save, this will overwrite schedule. and ship_config.yaml"


# TODO: error handling needs to be better! E.g. if elements of the pydantic model are missing then they should be specifically flagged
# TODO: e.g. if you remove ship_speed_knots from the ship_config.yaml it fails but the error message is misleading (starts going on about adcp_config)


# TODO: Can the whole lot be tidied up by moving some classes/methods to a new directory/files?!


class WaypointWidget(Static):
    def __init__(self, waypoint: Waypoint, index: int):
        super().__init__()
        self.waypoint = waypoint
        self.index = index

    def compose(self) -> ComposeResult:
        with Collapsible(title=f"[b]Waypoint {self.index + 1}[/b]", collapsed=False):
            if self.index > 0:
                yield Button(
                    "Copy from Previous", id=f"wp{self.index}_copy", variant="warning"
                )
            yield Label("Location:")
            yield Label("    Latitude:")
            yield Input(
                id=f"wp{self.index}_lat",
                value=str(self.waypoint.location.lat),
            )
            yield Label("    Longitude:")
            yield Input(
                id=f"wp{self.index}_lon",
                value=str(self.waypoint.location.lon),
            )
            yield Label("Time:")
            with Horizontal():
                yield Label("Year:")
                yield Select(
                    [
                        (str(year), year)
                        for year in range(
                            datetime.datetime.now().year - 3,
                            datetime.datetime.now().year + 1,
                        )
                    ],
                    id=f"wp{self.index}_year",
                    value=int(self.waypoint.time.year)
                    if self.waypoint.time
                    else Select.BLANK,
                    prompt="YYYY",
                    classes="year-select",
                )
                yield Label("Month:")
                yield Select(
                    [(f"{m:02d}", m) for m in range(1, 13)],
                    id=f"wp{self.index}_month",
                    value=int(self.waypoint.time.month)
                    if self.waypoint.time
                    else Select.BLANK,
                    prompt="MM",
                    classes="month-select",
                )
                yield Label("Day:")
                yield Select(
                    [(f"{d:02d}", d) for d in range(1, 32)],
                    id=f"wp{self.index}_day",
                    value=int(self.waypoint.time.day)
                    if self.waypoint.time
                    else Select.BLANK,
                    prompt="DD",
                    classes="day-select",
                )
                yield Label("Hour:")
                yield Select(
                    [(f"{h:02d}", h) for h in range(24)],
                    id=f"wp{self.index}_hour",
                    value=int(self.waypoint.time.hour)
                    if self.waypoint.time
                    else Select.BLANK,
                    prompt="hh",
                    classes="hour-select",
                )
                yield Label("Min:")
                yield Select(
                    [(f"{m:02d}", m) for m in range(0, 60, 5)],
                    id=f"wp{self.index}_minute",
                    value=int(self.waypoint.time.minute)
                    if self.waypoint.time
                    else Select.BLANK,
                    prompt="mm",
                    classes="minute-select",
                )

            yield Label("Instruments:")
            for instrument in InstrumentType:
                is_selected = instrument in (self.waypoint.instrument or [])
                with Horizontal():
                    yield Label(instrument.value)
                    yield Switch(
                        value=is_selected, id=f"wp{self.index}_{instrument.value}"
                    )

    def copy_from_previous(self) -> None:
        if self.index > 0:
            schedule_editor = self.parent
            if schedule_editor:
                prev_lat = schedule_editor.query_one(f"#wp{self.index - 1}_lat")
                prev_lon = schedule_editor.query_one(f"#wp{self.index - 1}_lon")
                curr_lat = self.query_one(f"#wp{self.index}_lat")
                curr_lon = self.query_one(f"#wp{self.index}_lon")

                if prev_lat and prev_lon and curr_lat and curr_lon:
                    curr_lat.value = prev_lat.value
                    curr_lon.value = prev_lon.value

                time_components = ["year", "month", "day", "hour", "minute"]
                for comp in time_components:
                    prev = schedule_editor.query_one(f"#wp{self.index - 1}_{comp}")
                    curr = self.query_one(f"#wp{self.index}_{comp}")
                    if prev and curr:
                        curr.value = prev.value

                for instrument in InstrumentType:
                    prev_switch = schedule_editor.query_one(
                        f"#wp{self.index - 1}_{instrument.value}"
                    )
                    curr_switch = self.query_one(f"#wp{self.index}_{instrument.value}")
                    if prev_switch and curr_switch:
                        curr_switch.value = prev_switch.value

    @on(Button.Pressed, "Button")
    def button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"wp{self.index}_copy":
            self.copy_from_previous()


class ScheduleEditor(Static):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.schedule = None

    def compose(self) -> ComposeResult:
        try:
            self.schedule = Schedule.from_yaml(f"{self.path}/schedule.yaml")
            yield Label("[b]Schedule Editor[/b]", id="title", markup=True)
            yield Rule(line_style="heavy")

            with Collapsible(
                title="[b]Waypoints[/b]",
                collapsed=True,
            ):
                for i, waypoint in enumerate(self.schedule.waypoints):
                    yield WaypointWidget(waypoint, i)

            # Space-Time Region Section
            # TODO: MAY NEED TO ADD A FEATURE ON SAVE CHANGES WHICH AUTOMATICALLY DETECTS MAX AND MIN TIME
            # TODO: FOR THE SCENARIO WHERE YAML LOADED IN IS NULL AND USER DOES NOT EDIT THEMSELVES
            with Collapsible(
                title="[b]Space-Time Region[/b] (advanced users only)",
                collapsed=True,
            ):
                if self.schedule.space_time_region:
                    str_data = self.schedule.space_time_region
                    yield Label("Minimum Latitude:")
                    yield Input(
                        id="min_lat",
                        value=str(str_data.spatial_range.minimum_latitude),
                    )
                    yield Label("Maximum Latitude:")
                    yield Input(
                        id="max_lat",
                        value=str(str_data.spatial_range.maximum_latitude),
                    )
                    yield Label("Minimum Longitude:")
                    yield Input(
                        id="min_lon",
                        value=str(str_data.spatial_range.minimum_longitude),
                    )
                    yield Label("Maximum Longitude:")
                    yield Input(
                        id="max_lon",
                        value=str(str_data.spatial_range.maximum_longitude),
                    )
                    yield Label("Minimum Depth (meters):")
                    yield Input(
                        id="min_depth",
                        value=str(str_data.spatial_range.minimum_depth),
                    )
                    yield Label("Maximum Depth (meters):")
                    yield Input(
                        id="max_depth",
                        value=str(str_data.spatial_range.maximum_depth),
                    )
                    yield Label("Start Time:")
                    yield Input(
                        id="start_time",
                        placeholder="YYYY-MM-DD hh:mm:ss",
                        value=(
                            str(str_data.time_range.start_time)
                            if str_data.time_range and str_data.time_range.start_time
                            else ""
                        ),
                    )
                    yield Label("End Time:")
                    yield Input(
                        id="end_time",
                        placeholder="YYYY-MM-DD hh:mm:ss",
                        value=(
                            str(str_data.time_range.end_time)
                            if str_data.time_range and str_data.time_range.end_time
                            else ""
                        ),
                    )

        except Exception as e:
            yield Label(f"Error loading schedule: {e!s}")

    def save_changes(self) -> None:
        """Save changes to schedule.yaml."""
        try:
            # spacetime region
            spatial_range = SpatialRange(
                minimum_longitude=self.query_one("#min_lon").value,
                maximum_longitude=self.query_one("#max_lon").value,
                minimum_latitude=self.query_one("#min_lat").value,
                maximum_latitude=self.query_one("#max_lat").value,
                minimum_depth=self.query_one("#min_depth").value,
                maximum_depth=self.query_one("#max_depth").value,
            )

            time_range = TimeRange(
                start_time=self.query_one("#start_time").value,
                end_time=self.query_one("#end_time").value,
            )

            space_time_region = SpaceTimeRegion(
                spatial_range=spatial_range, time_range=time_range
            )

            self.schedule.space_time_region = space_time_region

            # waypoints
            waypoints = []
            for i in range(len(self.schedule.waypoints)):
                location = Location(
                    latitude=float(self.query_one(f"#wp{i}_lat").value),
                    longitude=float(self.query_one(f"#wp{i}_lon").value),
                )
                time = datetime.datetime(
                    int(self.query_one(f"#wp{i}_year").value),
                    int(self.query_one(f"#wp{i}_month").value),
                    int(self.query_one(f"#wp{i}_day").value),
                    int(self.query_one(f"#wp{i}_hour").value),
                    int(self.query_one(f"#wp{i}_minute").value),
                    0,
                )
                instruments = [
                    instrument
                    for instrument in InstrumentType
                    if self.query_one(f"#wp{i}_{instrument.value}").value
                ]

                waypoints.append(
                    Waypoint(location=location, time=time, instrument=instruments)
                )

            # save
            self.schedule.waypoints = waypoints
            self.schedule.to_yaml(f"{self.path}/schedule.yaml")

        # TODO: one error type for User Errors (e.g. new UserError class?) which gives information on where went wrong (e.g. as above "Inputs for all latitude, longitude and time parameters are required for waypoint {i + 1}")
        except Exception as e:
            self.notify(f"Error saving schedule: {e!r}", severity="error", timeout=60)
            raise
        # TODO: then also another type of generic error (e.g. the existing except Exception as e) where there is a bug in the code but it's unknown where (i.e. it has got past all the other tests before being committed)
        # TODO: and add a message saying "please raise an issue on the VirtualShip GitHub issue tracker"
        # TODO: also provide a full traceback which the user can copy to their issue (may need to quit the application to provide this option)


class ConfigEditor(Container):
    # TODO: Also incorporate verify methods!

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.config = None

    def compose(self) -> ComposeResult:
        try:
            self.config = ShipConfig.from_yaml(f"{self.path}/ship_config.yaml")
            yield Label("[b]Ship Config Editor[/b]", id="title", markup=True)
            yield Rule(line_style="heavy")

            # ship speed and onboard measurement selection
            with Collapsible(title="[b]Ship Speed and Onboard Measurements[/b]"):
                with Horizontal(classes="ship_speed"):
                    yield Label("[b]Ship Speed (knots):[/b]")
                    yield Input(
                        id="speed",
                        classes="ship_speed_input",
                        placeholder="knots",
                        value=str(
                            self.config.ship_speed_knots
                            if self.config.ship_speed_knots
                            else ""
                        ),
                    )

                with Horizontal(classes="ts-section"):
                    yield Label("[b]Onboard Temperature/Salinity:[/b]")
                    yield Switch(
                        value=bool(self.config.ship_underwater_st_config),
                        id="has_onboard_ts",
                    )

                with Horizontal(classes="adcp-section"):
                    yield Label("[b]Onboard ADCP:[/b]")
                    yield Switch(value=bool(self.config.adcp_config), id="has_adcp")

                # adcp type selection
                with Horizontal(id="adcp_type_container", classes="-hidden"):
                    is_deep = (
                        self.config.adcp_config
                        and self.config.adcp_config.max_depth_meter == -1000.0
                    )
                    yield Label("       OceanObserver:")
                    yield Switch(value=is_deep, id="adcp_deep")
                    yield Label("   SeaSeven:")
                    yield Switch(value=not is_deep, id="adcp_shallow")

            # specific instrument configurations
            with Collapsible(
                title="[b]Instrument Configurations[/b] (advanced users only)",
                collapsed=True,
            ):
                # TODO: could all of the below be a loop instead?! Extracting each of the sub parameters for each instrument config?

                with Collapsible(
                    title="[b]Onboard ADCP Configuration[/b]", collapsed=True
                ):
                    with Container(classes="instrument-config"):
                        yield Label("Number of Bins:")
                        yield Input(
                            id="adcp_num_bins",
                            value=str(
                                self.config.adcp_config.num_bins
                                if self.config.adcp_config
                                else ""
                            ),
                        )
                        yield Label("Period (minutes):")
                        yield Input(
                            id="adcp_period",
                            value=str(
                                self.config.adcp_config.period.total_seconds() / 60.0
                                if self.config.adcp_config
                                else ""
                            ),
                        )

                with Collapsible(
                    title="[b]Onboard Temperature/Salinity Configuration[/b]",
                    collapsed=True,
                ):
                    with Container(classes="instrument-config"):
                        yield Label("Period (minutes):")
                        yield Input(
                            id="ts_period",
                            value=str(
                                self.config.ship_underwater_st_config.period.total_seconds()
                                / 60.0
                                if self.config.ship_underwater_st_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]CTD Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="ctd_max_depth",
                            value=str(
                                self.config.ctd_config.max_depth_meter
                                if self.config.ctd_config
                                else ""
                            ),
                        )
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="ctd_min_depth",
                            value=str(
                                self.config.ctd_config.min_depth_meter
                                if self.config.ctd_config
                                else ""
                            ),
                        )
                        yield Label("Stationkeeping Time (minutes):")
                        yield Input(
                            id="ctd_stationkeeping_time",
                            value=str(
                                self.config.ctd_config.stationkeeping_time.total_seconds()
                                / 60.0
                                if self.config.ctd_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]CTD-BGC Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="ctd_bgc_max_depth",
                            value=str(
                                self.config.ctd_bgc_config.max_depth_meter
                                if self.config.ctd_bgc_config
                                else ""
                            ),
                        )
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="ctd_bgc_min_depth",
                            value=str(
                                self.config.ctd_bgc_config.min_depth_meter
                                if self.config.ctd_bgc_config
                                else ""
                            ),
                        )
                        yield Label("Stationkeeping Time (minutes):")
                        yield Input(
                            id="ctd_bgc_stationkeeping_time",
                            value=str(
                                self.config.ctd_bgc_config.stationkeeping_time.total_seconds()
                                / 60.0
                                if self.config.ctd_bgc_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]XBT Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="xbt_max_depth",
                            value=str(
                                self.config.xbt_config.max_depth_meter
                                if self.config.xbt_config
                                else ""
                            ),
                        )
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="xbt_min_depth",
                            value=str(
                                self.config.xbt_config.min_depth_meter
                                if self.config.xbt_config
                                else ""
                            ),
                        )
                        yield Label("Fall Speed (meters/second):")
                        yield Input(
                            id="xbt_fall_speed",
                            value=str(
                                self.config.xbt_config.fall_speed_meter_per_second
                                if self.config.xbt_config
                                else ""
                            ),
                        )
                        yield Label("Deceleration Coefficient:")
                        yield Input(
                            id="xbt_decel_coeff",
                            value=str(
                                self.config.xbt_config.deceleration_coefficient
                                if self.config.xbt_config
                                else ""
                            ),
                        )

                with Collapsible(
                    title="[b]Argo Float Configuration[/b]", collapsed=True
                ):
                    with Container(classes="instrument-config"):
                        yield Label("Cycle Days:")
                        yield Input(
                            id="argo_cycle_days",
                            value=str(
                                self.config.argo_float_config.cycle_days
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        yield Label("Drift Days:")
                        yield Input(
                            id="argo_drift_days",
                            value=str(
                                self.config.argo_float_config.drift_days
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        yield Label("Drift Depth (meters):")
                        yield Input(
                            id="argo_drift_depth",
                            value=str(
                                self.config.argo_float_config.drift_depth_meter
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="argo_max_depth",
                            value=str(
                                self.config.argo_float_config.max_depth_meter
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="argo_min_depth",
                            value=str(
                                self.config.argo_float_config.min_depth_meter
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        yield Label("Vertical Speed (meters/second):")
                        yield Input(
                            id="argo_vertical_speed",
                            value=str(
                                self.config.argo_float_config.vertical_speed_meter_per_second
                                if self.config.argo_float_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]Drifter Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        yield Label("Depth (meters):")
                        yield Input(
                            id="drifter_depth",
                            value=str(
                                self.config.drifter_config.depth_meter
                                if self.config.drifter_config
                                else ""
                            ),
                        )
                        yield Label("Lifetime (minutes):")
                        yield Input(
                            id="drifter_lifetime",
                            value=str(
                                self.config.drifter_config.lifetime.total_seconds()
                                / 60.0
                                if self.config.drifter_config
                                else ""
                            ),
                        )

        except Exception as e:
            yield Label(f"Error loading ship config: {e!s}")

    def on_mount(self) -> None:
        self.show_hide_adcp_type(bool(self.config.adcp_config))

    def show_hide_adcp_type(self, show: bool) -> None:
        container = self.query_one("#adcp_type_container")
        if show:
            container.remove_class("-hidden")
        else:
            container.add_class("-hidden")

    @on(Switch.Changed, "#has_adcp")
    def on_adcp_toggle(self, event: Switch.Changed) -> None:
        self.show_hide_adcp_type(event.value)

    @on(Switch.Changed, "#adcp_deep")
    def deep_changed(self, event: Switch.Changed) -> None:
        if event.value:
            shallow = self.query_one("#adcp_shallow", Switch)
            shallow.value = False

    @on(Switch.Changed, "#adcp_shallow")
    def shallow_changed(self, event: Switch.Changed) -> None:
        if event.value:
            deep = self.query_one("#adcp_deep", Switch)
            deep.value = False

    def save_changes(self) -> None:
        """Save changes to ship_config.yaml."""
        try:
            # ship speed
            self.config.ship_speed_knots = float(self.query_one("#speed").value)

            # adcp config
            has_adcp = self.query_one("#has_adcp", Switch).value
            if has_adcp:
                self.config.adcp_config = ADCPConfig(
                    max_depth_meter=-1000.0
                    if self.query_one("#adcp_deep", Switch).value
                    else -150.0,
                    num_bins=int(self.query_one("#adcp_num_bins").value),
                    period=float(self.query_one("#adcp_period").value),
                )
            else:
                self.config.adcp_config = None

            # T/S config
            has_ts = self.query_one("#has_onboard_ts", Switch).value
            if has_ts:
                self.config.ship_underwater_st_config = ShipUnderwaterSTConfig(
                    period=float(self.query_one("#ts_period").value)
                )
            else:
                self.config.ship_underwater_st_config = None

            # ctd config
            self.config.ctd_config = CTDConfig(
                max_depth_meter=float(self.query_one("#ctd_max_depth").value),
                min_depth_meter=float(self.query_one("#ctd_min_depth").value),
                stationkeeping_time=float(
                    self.query_one("#ctd_stationkeeping_time").value
                ),
            )

            # CTD-BGC config
            self.config.ctd_bgc_config = CTD_BGCConfig(
                max_depth_meter=float(self.query_one("#ctd_bgc_max_depth").value),
                min_depth_meter=float(self.query_one("#ctd_bgc_min_depth").value),
                stationkeeping_time=float(
                    self.query_one("#ctd_bgc_stationkeeping_time").value
                ),
            )

            # xbt config
            self.config.xbt_config = XBTConfig(
                min_depth_meter=float(self.query_one("#xbt_min_depth").value),
                max_depth_meter=float(self.query_one("#xbt_max_depth").value),
                fall_speed_meter_per_second=float(
                    self.query_one("#xbt_fall_speed").value
                ),
                deceleration_coefficient=float(
                    self.query_one("#xbt_decel_coeff").value
                ),
            )

            # argo config
            self.config.argo_float_config = ArgoFloatConfig(
                min_depth_meter=float(self.query_one("#argo_min_depth").value),
                max_depth_meter=float(self.query_one("#argo_max_depth").value),
                drift_depth_meter=float(self.query_one("#argo_drift_depth").value),
                vertical_speed_meter_per_second=float(
                    self.query_one("#argo_vertical_speed").value
                ),
                cycle_days=float(self.query_one("#argo_cycle_days").value),
                drift_days=float(self.query_one("#argo_drift_days").value),
            )

            # drifter config
            self.config.drifter_config = DrifterConfig(
                depth_meter=float(self.query_one("#drifter_depth").value),
                lifetime=float(self.query_one("#drifter_lifetime").value),
            )

            # save
            self.config.to_yaml(f"{self.path}/ship_config.yaml")

        # TODO: one error type for User Errors (e.g. new UserError class?) which gives information on where went wrong (e.g. as above "Inputs for all latitude, longitude and time parameters are required for waypoint {i + 1}")
        except Exception as e:
            self.notify(f"Error saving config: {e!s}", severity="error", timeout=60)
            raise
        # TODO: then also another type of generic error (e.g. the existing except Exception as e) where there is a bug in the code but it's unknown where (i.e. it has got past all the other tests before being committed)
        # TODO: and add a message saying "please raise an issue on the VirtualShip GitHub issue tracker"
        # TODO: also provide a full traceback which the user can copy to their issue (may need to quit the application to provide this option)


class ScheduleScreen(Screen):
    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield ConfigEditor(self.path)
            yield ScheduleEditor(self.path)
            # Move buttons to screen level
            with Horizontal():
                yield Button("Save Changes", id="save_button", variant="success")
                yield Button("Exit", id="exit_button", variant="error")

    @on(Button.Pressed, "#exit_button")
    def exit_pressed(self) -> None:
        self.app.exit()

    @on(Button.Pressed, "#save_button")
    def save_pressed(self) -> None:
        """Handle save button press."""
        config_editor = self.query_one(ConfigEditor)
        schedule_editor = self.query_one(ScheduleEditor)

        try:
            config_editor.save_changes()
            schedule_editor.save_changes()
            self.notify(
                "Changes saved successfully", severity="information", timeout=20
            )
        except Exception as e:
            self.notify(f"Error saving changes: {e!s}", severity="error", timeout=60)


class ScheduleApp(App):
    CSS = """
    Screen {
        align: center middle;
    }

    ConfigEditor {
        background: $panel;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }

    VerticalScroll {
        width: 100%;
        height: 100%;
        background: $surface;
        color: $text;
        padding: 1;
    }

    WaypointWidget {
        padding: 0;
        margin: 0;
        border: none;
    }

    WaypointWidget > Collapsible {
        margin: 1;
        background: $boost;
        border: solid $primary;
    }

    WaypointWidget > Collapsible > .collapsible--content {
        padding: 1;
    }

    Input {
        margin: 1;
    }

    Label {
        margin-top: 1;
    }

    Button {
        min-width: 16;
        margin: 1;
        color: $text;
    }

    Button.-primary {
        background: $primary;
        width: 100%;
    }

    Button.-default {
        background: $boost;
    }

    Button.-success {
        background: $success;
    }

    Button.-error {
        background: $error;
    }

    Button#exit_button {
        margin-left: 1;
    }

    Horizontal {
        height: auto;
        align: left middle;
    }

    Vertical {
        height: auto;
    }

    Switch {
        margin: 0 1;
    }

    #title {
        text-style: bold;
        padding: 1;
    }

    .path {
        color: $text-muted;
        text-style: italic;
    }

    Collapsible {
        background: $boost;
        margin: 1;
    }

    Collapsible > .collapsible--content {
        padding: 1;
    }

    Collapsible > .collapsible--title {
        padding: 1;
    }

    Collapsible > .collapsible--content > Collapsible {
        margin: 0 1;
        background: $surface;
    }

    .-hidden {
        display: none;
    }

    .ts-section {
        margin-bottom: 1;
    }

    .adcp-section {
        margin-bottom: 1;
    }

    .ship_speed {
        align: left middle;
        margin-bottom: 1;
    }

    .ship_speed_input {
        width: 20;
        margin: 0 4;
    }

    .instrument-config {
        margin: 1;
        padding: 0 2;
        height: auto;
    }

    .instrument-config Label {
        margin-top: 1;
        color: $text-muted;
    }

    .instrument-config Input {
        width: 30;
        margin: 0 1;
    }

    .year-select {
        width: 20;
    }

    .month-select, .day-select {
        width: 18;
    }

    .hour-select, .minute-select {
        width: 15;
    }
    """

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def on_mount(self) -> None:
        self.push_screen(ScheduleScreen(self.path))
        self.theme = "textual-light"


def _plan(path: str) -> None:
    app = ScheduleApp(path)
    app.run()


# FOR DEV?!

# if __name__ == "__main__":
#     _plan(".")

# # FOR RUNNING IN DEV MODE:
# # PYTHONPATH="/Users/Atkin004/Documents/virtualship/src" textual run --dev virtualship.cli._plan
