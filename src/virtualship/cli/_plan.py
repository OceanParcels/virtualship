import datetime
import sys
from typing import ClassVar

from pydantic import ValidationError
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.validation import Function
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

from virtualship.errors import UserError
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

# TODO: need to do a big round of edits where tidy up all the error messaging.
# - given a lot of the validation of entry is done natively now in textual, this should mean that all other
#   errors associated with inputting to the app should be 'unexpected' and therefore call to the report-to-GitHub workflow
# - errors associated with ship_config and schedule.verify() should, however, provide in-UI messaging ideally
#   to notify the user that their selections are not valid...

# TODO: add TEXTUAL_SERVE dependency if end up using it...

# TODO: add a flag to the `virtualship plan` command which allows toggle between hosting the UI in terminal or web browser..

# TODO: need to handle how to add the start_ and end_ datetimes automatically to Space-Time Region!
# TODO: because I think the .yaml that comes from `virtualship init` will not have these as standard and we don't expect students to go add themselves...

# TODO: look through all error handling in both _plan.py and command.py scripts to check redudancy
# TODO: also add more error handling for 1) if there are no yamls found in the specified *path*
# TODO: and also for if there are errors in the yaml being opened, for example if what should be a float has been manaully changed to something invalid
# TODO: or if indeed any of the pydantic model components associated with the yamls are missing


# TODO: make sure 'Save' writes the yaml file components in the right order? Or does this not matter?
# TODO: test via full run through of an expedition using yamls edited by `virtualship plan`
# TODO: implement action for 'Save' button

# TODO: Can the whole lot be tidied up by moving some classes/methods to a new directory/files?!

# TODO: the valid entry + User errors etc. need to be added to the Schedule editor (currently on the Config Editor)


class WaypointWidget(Static):
    def __init__(self, waypoint: Waypoint, index: int):
        super().__init__()
        self.waypoint = waypoint
        self.index = index

    def compose(self) -> ComposeResult:
        with Collapsible(title=f"[b]Waypoint {self.index + 1}[/b]", collapsed=True):
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
                # Only copy time components and instruments, not lat/lon
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
                title="[b]Waypoints & Instrument Selection[/b]",
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

    def save_changes(self) -> bool:
        """Save changes to schedule.yaml."""
        # TODO: SAVE_CHANGES() NEEDS TO BE LARGELY RE-WORKED NOW THAT MORE VALIDATION IS BUILT INTO THE INPUTS
        # TODO: and should proabably now be more focussed on .verify() methods
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
            return True

        except Exception as e:
            self.notify(
                f"Error saving schedule: {e!r}",
                severity="error",
                timeout=60,
                markup=False,
            )
            return False


# TODO: perhaps these methods could be housed elsewhere for neatness?!


def get_field_type(model_class, field_name):
    """Get Pydantic model class data type."""
    return model_class.model_fields[field_name].annotation


def type_to_textual(field_type):
    """Convert data type to str which Textual can interpret for type = setting in Input objects."""
    if field_type in (float, datetime.timedelta):
        return "number"
    elif field_type is int:
        return "integer"
    else:
        return "text"


# Pydantic field constraint attributes used for validation and introspection
FIELD_CONSTRAINT_ATTRS = ("gt", "ge", "lt", "le")


def get_field_conditions(model_class, field_name):
    """Determine and return what conditions (and associated reference value) a Pydantic model sets on inputs."""
    field_info = model_class.model_fields[field_name]
    conditions = {}
    for meta in field_info.metadata:
        for attr in dir(meta):
            if not attr.startswith("_") and getattr(meta, attr) is not None:
                if attr in FIELD_CONSTRAINT_ATTRS:
                    conditions[attr] = getattr(meta, attr)
                else:
                    raise ValueError(
                        f"Unexpected constraint '{attr}' found on field '{field_name}'. "
                        f"Allowed constraints: {FIELD_CONSTRAINT_ATTRS}"
                    )
    return list(conditions.keys()), list(conditions.values())


def make_validator(condition, reference, value_type):
    """
    Make a validator function based on the Pydantic model field conditions returned by get_field_conditions().

    TODO: Textual validator tools do not currently support additional arguments (such as 'reference') being fed into the validator functions (such as is_gt0) at present.
    TODO: Therefore, reference values cannot be fed in dynamically and necessitates hard coding depending onthe condition and reference value combination.
    TODO: At present, Pydantic models only require gt/ge/lt/le relative to **0.0** so `reference` is always checked as being == 0.0
    TODO: Additional custom conditions can be "hard-coded" as new condition and reference combinations
    TODO: if Pydantic model specifications change in the future and/or new instruments are added to VirtualShip etc.
    TODO: Perhaps there's scope here though for a more robust implementation in a future PR...

    Note, docstrings describing the conditional are required in the child functions (e.g. is_gt0), and is checked by require_docstring().
    Docstrings will be used to generate informative UI invalid entry messages, so them being informative and accurate is important!

    """

    def require_docstring(func):
        if func.__doc__ is None or not func.__doc__.strip():
            raise ValueError(f"Function '{func.__name__}' must have a docstring.")
        return func

    def convert(value):
        try:
            return value_type(value)
        except Exception:
            return None

    if value_type in (float, int) and reference == 0.0:
        ref_zero = 0.0
    elif value_type is datetime.timedelta and reference == datetime.timedelta():
        ref_zero = datetime.timedelta()
    else:
        raise ValueError(
            f"Unsupported value_type/reference combination: {value_type}, {reference}"
        )

    if condition == "gt" and reference == ref_zero:

        @require_docstring
        def is_gt0(value: str) -> bool:
            """Greater than 0."""
            v = convert(value)
            return v is not None and v > ref_zero

        return is_gt0

    if condition == "ge" and reference == ref_zero:

        @require_docstring
        def is_ge0(value: str) -> bool:
            """Greater than or equal to 0."""
            v = convert(value)
            return v is not None and v >= ref_zero

        return is_ge0

    if condition == "lt" and reference == ref_zero:

        @require_docstring
        def is_lt0(value: str) -> bool:
            """Less than 0."""
            v = convert(value)
            return v is not None and v < ref_zero

        return is_lt0

    if condition == "le" and reference == ref_zero:

        @require_docstring
        def is_le0(value: str) -> bool:
            """Less than or equal to 0."""
            v = convert(value)
            return v is not None and v <= ref_zero

        return is_le0

    else:
        raise ValueError(
            f"Unknown condition: {condition} and reference value: {reference} combination."
        )


def group_validators(model, attr):
    """Bundle all validators for Input into singular list."""
    return [
        make_validator(cond, ref, get_field_type(model, attr))
        for cond, ref in zip(
            *get_field_conditions(model, attr),
            strict=False,
        )
    ]


class ConfigEditor(Container):
    DEFAULT_ADCP_CONFIG: ClassVar[dict[str, float]] = {
        "num_bins": 40,
        "period_minutes": 5.0,
    }

    DEFAULT_TS_CONFIG: ClassVar[dict[str, float]] = {"period_minutes": 5.0}

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

            with Collapsible(title="[b]Ship Speed & Onboard Measurements[/b]"):
                attr = "ship_speed_knots"
                validators = group_validators(ShipConfig, attr)
                with Horizontal(classes="ship_speed"):
                    yield Label("[b]Ship Speed (knots):[/b]")
                    yield Input(
                        id="speed",
                        type=type_to_textual(get_field_type(ShipConfig, attr)),
                        validators=[
                            Function(
                                validator,
                                f"*INVALID*: entry must be {validator.__doc__.lower()}",
                            )
                            for validator in validators
                        ],
                        classes="ship_speed_input",
                        placeholder="knots",
                        value=str(
                            self.config.ship_speed_knots
                            if self.config.ship_speed_knots
                            else ""
                        ),
                    )
                yield Label("", id="validation-failure-label", classes="-hidden")

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
                with Collapsible(
                    title="[b]Onboard ADCP Configuration[/b]", collapsed=True
                ):
                    with Container(classes="instrument-config"):
                        attr = "num_bins"
                        validators = group_validators(ADCPConfig, attr)
                        yield Label("Number of Bins:")
                        yield Input(
                            id="adcp_num_bins",
                            type=type_to_textual(get_field_type(ADCPConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.adcp_config.num_bins
                                if self.config.adcp_config
                                else ""
                            ),
                        )

                        attr = "period"
                        validators = group_validators(ADCPConfig, attr)
                        yield Label("Period (minutes):")
                        yield Input(
                            id="adcp_period",
                            type=type_to_textual(get_field_type(ADCPConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
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
                        attr = "period"
                        validators = group_validators(ShipUnderwaterSTConfig, attr)
                        yield Label("Period (minutes):")
                        yield Input(
                            id="ts_period",
                            type=type_to_textual(
                                get_field_type(ShipUnderwaterSTConfig, attr)
                            ),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ship_underwater_st_config.period.total_seconds()
                                / 60.0
                                if self.config.ship_underwater_st_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]CTD Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        attr = "max_depth_meter"
                        validators = group_validators(CTDConfig, attr)
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="ctd_max_depth",
                            type=type_to_textual(get_field_type(CTDConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ctd_config.max_depth_meter
                                if self.config.ctd_config
                                else ""
                            ),
                        )
                        attr = "min_depth_meter"
                        validators = group_validators(CTDConfig, attr)
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="ctd_min_depth",
                            type=type_to_textual(get_field_type(CTDConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ctd_config.min_depth_meter
                                if self.config.ctd_config
                                else ""
                            ),
                        )
                        attr = "stationkeeping_time"
                        validators = group_validators(CTDConfig, attr)
                        yield Label("Stationkeeping Time (minutes):")
                        yield Input(
                            id="ctd_stationkeeping_time",
                            type=type_to_textual(get_field_type(CTDConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ctd_config.stationkeeping_time.total_seconds()
                                / 60.0
                                if self.config.ctd_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]CTD-BGC Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        attr = "max_depth_meter"
                        validators = group_validators(CTD_BGCConfig, attr)
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="ctd_bgc_max_depth",
                            type=type_to_textual(get_field_type(CTD_BGCConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ctd_bgc_config.max_depth_meter
                                if self.config.ctd_bgc_config
                                else ""
                            ),
                        )
                        attr = "min_depth_meter"
                        validators = group_validators(CTD_BGCConfig, attr)
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="ctd_bgc_min_depth",
                            type=type_to_textual(get_field_type(CTD_BGCConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ctd_bgc_config.min_depth_meter
                                if self.config.ctd_bgc_config
                                else ""
                            ),
                        )
                        attr = "stationkeeping_time"
                        validators = group_validators(CTD_BGCConfig, attr)
                        yield Label("Stationkeeping Time (minutes):")
                        yield Input(
                            id="ctd_bgc_stationkeeping_time",
                            type=type_to_textual(get_field_type(CTD_BGCConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.ctd_bgc_config.stationkeeping_time.total_seconds()
                                / 60.0
                                if self.config.ctd_bgc_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]XBT Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        attr = "max_depth_meter"
                        validators = group_validators(XBTConfig, attr)
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="xbt_max_depth",
                            type=type_to_textual(get_field_type(XBTConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.xbt_config.max_depth_meter
                                if self.config.xbt_config
                                else ""
                            ),
                        )
                        attr = "min_depth_meter"
                        validators = group_validators(XBTConfig, attr)
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="xbt_min_depth",
                            type=type_to_textual(get_field_type(XBTConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.xbt_config.min_depth_meter
                                if self.config.xbt_config
                                else ""
                            ),
                        )
                        attr = "fall_speed_meter_per_second"
                        validators = group_validators(XBTConfig, attr)
                        yield Label("Fall Speed (meters/second):")
                        yield Input(
                            id="xbt_fall_speed",
                            type=type_to_textual(get_field_type(XBTConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.xbt_config.fall_speed_meter_per_second
                                if self.config.xbt_config
                                else ""
                            ),
                        )
                        attr = "deceleration_coefficient"
                        validators = group_validators(XBTConfig, attr)
                        yield Label("Deceleration Coefficient:")
                        yield Input(
                            id="xbt_decel_coeff",
                            type=type_to_textual(get_field_type(XBTConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
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
                        attr = "cycle_days"
                        validators = group_validators(ArgoFloatConfig, attr)
                        yield Label("Cycle Days:")
                        yield Input(
                            id="argo_cycle_days",
                            type=type_to_textual(get_field_type(ArgoFloatConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.argo_float_config.cycle_days
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        attr = "drift_days"
                        validators = group_validators(ArgoFloatConfig, attr)
                        yield Label("Drift Days:")
                        yield Input(
                            id="argo_drift_days",
                            type=type_to_textual(get_field_type(ArgoFloatConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.argo_float_config.drift_days
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        attr = "drift_depth_meter"
                        validators = group_validators(ArgoFloatConfig, attr)
                        yield Label("Drift Depth (meters):")
                        yield Input(
                            id="argo_drift_depth",
                            type=type_to_textual(get_field_type(ArgoFloatConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.argo_float_config.drift_depth_meter
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        attr = "max_depth_meter"
                        validators = group_validators(ArgoFloatConfig, attr)
                        yield Label("Maximum Depth (meters):")
                        yield Input(
                            id="argo_max_depth",
                            type=type_to_textual(get_field_type(ArgoFloatConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.argo_float_config.max_depth_meter
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        attr = "min_depth_meter"
                        validators = group_validators(ArgoFloatConfig, attr)
                        yield Label("Minimum Depth (meters):")
                        yield Input(
                            id="argo_min_depth",
                            type=type_to_textual(get_field_type(ArgoFloatConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.argo_float_config.min_depth_meter
                                if self.config.argo_float_config
                                else ""
                            ),
                        )
                        attr = "vertical_speed_meter_per_second"
                        validators = group_validators(ArgoFloatConfig, attr)
                        yield Label("Vertical Speed (meters/second):")
                        yield Input(
                            id="argo_vertical_speed",
                            type=type_to_textual(get_field_type(ArgoFloatConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.argo_float_config.vertical_speed_meter_per_second
                                if self.config.argo_float_config
                                else ""
                            ),
                        )

                with Collapsible(title="[b]Drifter Configuration[/b]", collapsed=True):
                    with Container(classes="instrument-config"):
                        attr = "depth_meter"
                        validators = group_validators(DrifterConfig, attr)
                        yield Label("Depth (meters):")
                        yield Input(
                            id="drifter_depth",
                            type=type_to_textual(get_field_type(DrifterConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.drifter_config.depth_meter
                                if self.config.drifter_config
                                else ""
                            ),
                        )
                        attr = "lifetime"
                        validators = group_validators(DrifterConfig, attr)
                        yield Label("Lifetime (minutes):")
                        yield Input(
                            id="drifter_lifetime",
                            type=type_to_textual(get_field_type(DrifterConfig, attr)),
                            validators=[
                                Function(
                                    validator,
                                    f"*INVALID*: entry must be {validator.__doc__.lower()}",
                                )
                                for validator in validators
                            ],
                            value=str(
                                self.config.drifter_config.lifetime.total_seconds()
                                / 60.0
                                if self.config.drifter_config
                                else ""
                            ),
                        )

        except Exception as e:
            yield Label(f"Error loading ship config: {e!s}")

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        label = self.query_one("#validation-failure-label", Label)
        if not event.validation_result.is_valid:
            message = (
                "\n".join(event.validation_result.failure_descriptions)
                if isinstance(event.validation_result.failure_descriptions, list)
                else str(event.validation_result.failure_descriptions)
            )
            label.update(message)
            label.remove_class("-hidden")
            label.add_class("validation-failure")
        else:
            label.update("")
            label.add_class("-hidden")
            label.remove_class("validation-failure")

    def on_mount(self) -> None:
        self.show_hide_adcp_type(bool(self.config.adcp_config))

    def show_hide_adcp_type(self, show: bool) -> None:
        container = self.query_one("#adcp_type_container")
        if show:
            container.remove_class("-hidden")
        else:
            container.add_class("-hidden")

    def _set_adcp_default_values(self):
        self.query_one("#adcp_num_bins").value = str(
            self.DEFAULT_ADCP_CONFIG["num_bins"]
        )
        self.query_one("#adcp_period").value = str(
            self.DEFAULT_ADCP_CONFIG["period_minutes"]
        )
        self.query_one("#adcp_shallow").value = True
        self.query_one("#adcp_deep").value = False

    def _set_ts_default_values(self):
        self.query_one("#ts_period").value = str(
            self.DEFAULT_TS_CONFIG["period_minutes"]
        )

    @on(Switch.Changed, "#has_adcp")
    def on_adcp_toggle(self, event: Switch.Changed) -> None:
        self.show_hide_adcp_type(event.value)
        if event.value and not self.config.adcp_config:
            # ADCP was turned on and was previously null
            self._set_adcp_default_values()

    @on(Switch.Changed, "#has_onboard_ts")
    def on_ts_toggle(self, event: Switch.Changed) -> None:
        if event.value and not self.config.ship_underwater_st_config:
            # T/S was turned on and was previously null
            self._set_ts_default_values()

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

    def _try_create_config(self, config_class, input_values, config_name):
        """Helper to create config with error handling."""
        try:
            return config_class(**input_values)
        except ValueError as e:
            field = (
                str(e).split()[0] if str(e).split() else "unknown field"
            )  # extract field name from Pydantic error
            raise UserError(
                f"Invalid {config_name} configuration: {field} - {e!s}"
            ) from e

    def save_changes(self) -> bool:
        # TODO: SAVE_CHANGES() NEEDS TO BE LARGELY RE-WORKED NOW THAT MORE VALIDATION IS BUILT INTO THE INPUTS
        # TODO: and should proabably now be more focussed on .verify() methods
        """Save changes to ship_config.yaml."""
        try:
            # ship speed
            try:
                speed = float(self.query_one("#speed").value)
                if speed <= 0:
                    raise UserError("Ship speed must be greater than 0")
                self.config.ship_speed_knots = speed
            except ValueError:
                raise UserError("Ship speed must be a valid number") from None

            # ADCP config
            has_adcp = self.query_one("#has_adcp", Switch).value
            if has_adcp:
                try:
                    self.config.adcp_config = self._try_create_config(
                        ADCPConfig,
                        {
                            "max_depth_meter": -1000.0
                            if self.query_one("#adcp_deep", Switch).value
                            else -150.0,
                            "num_bins": self.query_one("#adcp_num_bins").value,
                            "period": float(
                                self.query_one("#adcp_period").value
                            ),  # must be inputted as float, "period" in ADCPConfig will not handle str (to convert to timedelta), Pydantic will try to coerce the str to the relevant type in case of other params e.g. num_bins
                        },
                        "ADCP",
                    )
                except (ValueError, ValidationError, TypeError) as e:
                    raise UserError(f"Invalid ADCP configuration: {e!s}") from e
            else:
                self.config.adcp_config = None

            # T/S config
            has_ts = self.query_one("#has_onboard_ts", Switch).value
            if has_ts:
                try:
                    self.config.ship_underwater_st_config = self._try_create_config(
                        ShipUnderwaterSTConfig,
                        {"period": float(self.query_one("#ts_period").value)},
                        "Temperature/Salinity",
                    )
                except (ValueError, ValidationError, TypeError) as e:
                    raise UserError(
                        f"Invalid Onboard Temperature/Salinity configuration: {e!s}"
                    ) from e
            else:
                self.config.ship_underwater_st_config = None

            # CTD config
            try:
                self.config.ctd_config = CTDConfig(
                    max_depth_meter=self.query_one("#ctd_max_depth").value,
                    min_depth_meter=self.query_one("#ctd_min_depth").value,
                    stationkeeping_time=float(
                        self.query_one("#ctd_stationkeeping_time").value
                    ),
                )
            except (ValueError, ValidationError, TypeError) as e:
                raise UserError(f"Invalid CTD configuration: {e!s}") from e

            # CTD-BGC config
            try:
                self.config.ctd_bgc_config = CTD_BGCConfig(
                    max_depth_meter=self.query_one("#ctd_bgc_max_depth").value,
                    min_depth_meter=self.query_one("#ctd_bgc_min_depth").value,
                    stationkeeping_time=float(
                        self.query_one("#ctd_bgc_stationkeeping_time").value
                    ),
                )
            except (ValueError, ValidationError, TypeError) as e:
                raise UserError(f"Invalid CTD-BGC configuration: {e!s}") from e

            # XBT config
            try:
                self.config.xbt_config = XBTConfig(
                    min_depth_meter=self.query_one("#xbt_min_depth").value,
                    max_depth_meter=self.query_one("#xbt_max_depth").value,
                    fall_speed_meter_per_second=self.query_one("#xbt_fall_speed").value,
                    deceleration_coefficient=self.query_one("#xbt_decel_coeff").value,
                )
            except (ValueError, ValidationError, TypeError) as e:
                raise UserError(f"Invalid XBT configuration: {e!s}") from e

            # Argo config
            try:
                self.config.argo_float_config = ArgoFloatConfig(
                    min_depth_meter=self.query_one("#argo_min_depth").value,
                    max_depth_meter=self.query_one("#argo_max_depth").value,
                    drift_depth_meter=self.query_one("#argo_drift_depth").value,
                    vertical_speed_meter_per_second=self.query_one(
                        "#argo_vertical_speed"
                    ).value,
                    cycle_days=self.query_one("#argo_cycle_days").value,
                    drift_days=self.query_one("#argo_drift_days").value,
                )
            except (ValueError, ValidationError, TypeError) as e:
                raise UserError(f"Invalid Argo Float configuration: {e!s}") from e

            # Drifter config
            try:
                self.config.drifter_config = DrifterConfig(
                    depth_meter=self.query_one("#drifter_depth").value,
                    lifetime=self.query_one("#drifter_lifetime").value,
                )
            except (ValueError, ValidationError, TypeError) as e:
                raise UserError(f"Invalid Drifter configuration: {e!s}") from e

            # save
            self.config.to_yaml(f"{self.path}/ship_config.yaml")
            return True

        # TODO: error message here which says "Unexpected error, quitting application in x seconds, please report issue and traceback on GitHub"
        except Exception:
            self.notify(
                "An unexpected error occurred. The application will quit in 10 seconds.\n"
                "Please report this issue and the traceback on the VirtualShip issue tracker at: xyz.com",
                severity="error",
                timeout=10,
            )
            import asyncio

            async def quit_app():
                await asyncio.sleep(10)
                self.app.exit()

            self._quit_task = asyncio.create_task(quit_app())
            return False


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
            config_saved = config_editor.save_changes()
            schedule_saved = schedule_editor.save_changes()

            # TODO: don't need this error handling here if it's handled in the respective save_changes() functions for ship and schedule configs?!

            if config_saved and schedule_saved:
                self.notify(
                    "Changes saved successfully", severity="information", timeout=20
                )
        except Exception as e:
            self.notify(
                f"Error saving changes: {e!s}",
                severity="error",
                timeout=60,
                markup=False,
            )


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

    Input.-valid {
        border: tall $success 60%;
    }
    Input.-valid:focus {
        border: tall $success;
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

    Label.validation-failure {
        color: $error;
    }
    """

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def on_mount(self) -> None:
        self.push_screen(ScheduleScreen(self.path))
        self.theme = "textual-light"


if __name__ == "__main__":
    # parse path
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        raise ValueError("No path argument provided")

    # run app
    app = ScheduleApp(path)
    app.run()
