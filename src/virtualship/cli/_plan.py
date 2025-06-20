import datetime
import os
import sys
import traceback
from typing import ClassVar

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

from virtualship.errors import UnexpectedError
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

# TODO: check: how does it handle (all) the fields being empty upon reading-in? Need to add redundancy here...?
# - currently the application fails on start-up if something is missing or null (apart from ADCP and ST)
# - there is also a bug where if ADCP is null on start up, and then you switch it on in the UI then it crashes, so this bug fix is TODO!
# - otherwise, in terms of missing data on start up handling, best to throw an error to the user stating that x field is missing a value

# TODO: need to do a big round of edits where tidy up all the error messaging.
# - given a lot of the validation of entry is done natively now in textual, this should mean that all other
#   errors associated with inputting to the app should be 'unexpected' and therefore call to the report-to-GitHub workflow
# - errors associated with ship_config and schedule.verify() should, however, provide in-UI messaging ideally
#   to notify the user that their selections are not valid...

# TODO: add TEXTUAL_SERVE dependency if end up using it...

# TODO: add a flag to the `virtualship plan` command which allows toggle between hosting the UI in terminal or web browser..defo useful for when/if hosted on cloud based JupyterLab type environments/terminals...

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
                    "Copy Time & Instruments from Previous",
                    id=f"wp{self.index}_copy",
                    variant="warning",
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


class ConfigEditor(Container):
    DEFAULT_ADCP_CONFIG: ClassVar[dict[str, float]] = {
        "num_bins": 40,
        "period_minutes": 5.0,
    }

    DEFAULT_TS_CONFIG: ClassVar[dict[str, float]] = {"period_minutes": 5.0}

    INSTRUMENT_FIELDS: ClassVar[dict[str, dict]] = {
        "adcp_config": {
            "class": ADCPConfig,
            "title": "Onboard ADCP",
            "attributes": [
                {"name": "num_bins"},
                {"name": "period", "minutes": True},
            ],
        },
        "ship_underwater_st_config": {
            "class": ShipUnderwaterSTConfig,
            "title": "Onboard Temperature/Salinity",
            "attributes": [
                {"name": "period", "minutes": True},
            ],
        },
        "ctd_config": {
            "class": CTDConfig,
            "title": "CTD",
            "attributes": [
                {"name": "max_depth_meter"},
                {"name": "min_depth_meter"},
                {"name": "stationkeeping_time", "minutes": True},
            ],
        },
        "ctd_bgc_config": {
            "class": CTD_BGCConfig,
            "title": "CTD-BGC",
            "attributes": [
                {"name": "max_depth_meter"},
                {"name": "min_depth_meter"},
                {"name": "stationkeeping_time", "minutes": True},
            ],
        },
        "xbt_config": {
            "class": XBTConfig,
            "title": "XBT",
            "attributes": [
                {"name": "min_depth_meter"},
                {"name": "max_depth_meter"},
                {"name": "fall_speed_meter_per_second"},
                {"name": "deceleration_coefficient"},
            ],
        },
        "argo_float_config": {
            "class": ArgoFloatConfig,
            "title": "Argo Float",
            "attributes": [
                {"name": "min_depth_meter"},
                {"name": "max_depth_meter"},
                {"name": "drift_depth_meter"},
                {"name": "vertical_speed_meter_per_second"},
                {"name": "cycle_days"},
                {"name": "drift_days"},
            ],
        },
        "drifter_config": {
            "class": DrifterConfig,
            "title": "Drifter",
            "attributes": [
                {"name": "depth_meter"},
                {"name": "lifetime", "minutes": True},
            ],
        },
    }

    FIELD_CONSTRAINT_ATTRS: ClassVar[tuple] = (
        "gt",
        "ge",
        "lt",
        "le",
    )  # Pydantic field constraint attributes used for validation and introspection

    # TODO: Also incorporate verify methods!

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.config = None

    def compose(self) -> ComposeResult:
        try:
            ## SECTION: "Ship Speed & Onboard Measurements"

            self.config = ShipConfig.from_yaml(f"{self.path}/ship_config.yaml")
            yield Label("[b]Ship Config Editor[/b]", id="title", markup=True)
            yield Rule(line_style="heavy")

            with Collapsible(title="[b]Ship Speed & Onboard Measurements[/b]"):
                attr = "ship_speed_knots"
                validators = self.group_validators(ShipConfig, attr)
                with Horizontal(classes="ship_speed"):
                    yield Label("[b]Ship Speed (knots):[/b]")
                    yield Input(
                        id="speed",
                        type=self.type_to_textual(
                            self.get_field_type(ShipConfig, attr)
                        ),
                        validators=[
                            Function(
                                validator,
                                f"INVALID: value must be {validator.__doc__.lower()}",
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
                yield Label("", id="validation-failure-label-speed", classes="-hidden")

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

            ## SECTION: "Instrument Configurations (advanced users only)""

            with Collapsible(
                title="[b]Instrument Configurations[/b] (advanced users only)",
                collapsed=True,
            ):
                for instrument_name, info in self.INSTRUMENT_FIELDS.items():
                    config_class = info["class"]
                    attributes = info["attributes"]
                    config_instance = getattr(self.config, instrument_name, None)
                    title = info.get("title", instrument_name.replace("_", " ").title())

                    with Collapsible(
                        title=f"[b]{title}[/b]",
                        collapsed=True,
                    ):
                        with Container(classes="instrument-config"):
                            for attr_meta in attributes:
                                attr = attr_meta["name"]
                                is_minutes = attr_meta.get("minutes", False)
                                validators = self.group_validators(config_class, attr)
                                if config_instance:
                                    raw_value = getattr(config_instance, attr, "")
                                    if is_minutes and raw_value != "":
                                        try:
                                            value = str(
                                                raw_value.total_seconds() / 60.0
                                            )
                                        except AttributeError:
                                            value = str(raw_value)
                                    else:
                                        value = str(raw_value)
                                else:
                                    value = ""
                                yield Label(f"{attr.replace('_', ' ').title()}:")
                                yield Input(
                                    id=f"{instrument_name}_{attr}",
                                    type=self.type_to_textual(
                                        self.get_field_type(config_class, attr)
                                    ),
                                    validators=[
                                        Function(
                                            validator,
                                            f"INVALID: value must be {validator.__doc__.lower()}",
                                        )
                                        for validator in validators
                                    ],
                                    value=value,
                                )
                                yield Label(
                                    "",
                                    id=f"validation-failure-label-{instrument_name}_{attr}",
                                    classes="-hidden validation-failure",
                                )

        except Exception as e:
            yield Label(f"Error loading ship config: {e!s}")

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        input_id = event.input.id
        label_id = f"validation-failure-label-{input_id}"
        label = self.query_one(f"#{label_id}", Label)
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

    def get_field_type(self, model_class, field_name):
        """Get Pydantic model class data type."""
        return model_class.model_fields[field_name].annotation

    def type_to_textual(self, field_type):
        """Convert data type to str which Textual can interpret for type = setting in Input objects."""
        if field_type in (float, datetime.timedelta):
            return "number"
        elif field_type is int:
            return "integer"
        else:
            return "text"

    def get_field_conditions(self, model_class, field_name):
        """Determine and return what conditions (and associated reference value) a Pydantic model sets on inputs."""
        field_info = model_class.model_fields[field_name]
        conditions = {}
        for meta in field_info.metadata:
            for attr in dir(meta):
                if not attr.startswith("_") and getattr(meta, attr) is not None:
                    if attr in self.FIELD_CONSTRAINT_ATTRS:
                        conditions[attr] = getattr(meta, attr)
                    else:
                        raise ValueError(
                            f"Unexpected constraint '{attr}' found on field '{field_name}'. "
                            f"Allowed constraints: {self.FIELD_CONSTRAINT_ATTRS}"
                        )
        return list(conditions.keys()), list(conditions.values())

    def make_validator(self, condition, reference, value_type):
        """
        Make a validator function based on the Pydantic model field conditions returned by get_field_conditions().

        N.B. #1 Textual validator tools do not currently support additional arguments (such as 'reference') being fed into the validator functions (such as is_gt0) at present.
        Therefore, reference values cannot be fed in dynamically and necessitates hard coding depending onthe condition and reference value combination.
        At present, Pydantic models only require gt/ge/lt/le relative to **0.0** so `reference` is always checked as being == 0.0
        Additional custom conditions can be "hard-coded" as new condition and reference combinations if Pydantic model specifications change in the future and/or new instruments are added to VirtualShip etc.
        TODO: Perhaps there's scope here though for a more robust implementation in a future PR...

        N.B. #2, docstrings describing the conditional are required in the child functions (e.g. is_gt0), and presence is checked by require_docstring().
        Docstrings will be used to generate informative UI invalid entry messages, so them being informative and accurate is important!

        """

        def require_docstring(func):
            if func.__doc__ is None or not func.__doc__.strip():
                raise ValueError(f"Function '{func.__name__}' must have a docstring.")
            return func

        def convert(value):
            try:
                if value_type is datetime.timedelta:
                    return datetime.timedelta(minutes=float(value))
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

    def group_validators(self, model, attr):
        """Bundle all validators for Input into singular list."""
        return [
            self.make_validator(cond, ref, self.get_field_type(model, attr))
            for cond, ref in zip(
                *self.get_field_conditions(model, attr),
                strict=False,
            )
        ]

    def save_changes(self) -> bool:
        """Save changes to ship_config.yaml."""
        try:
            # ship speed
            attr = "ship_speed_knots"
            field_type = self.get_field_type(self.config, attr)
            value = field_type(self.query_one("#speed").value)
            ShipConfig.model_validate(
                {**self.config.model_dump(), attr: value}
            )  # validate using a temporary model (raises if invalid)
            self.config.ship_speed_knots = value

            # individual instrument configurations
            for instrument_name, info in self.INSTRUMENT_FIELDS.items():
                config_class = info["class"]
                attributes = info["attributes"]
                kwargs = {}
                for attr_meta in attributes:
                    attr = attr_meta["name"]
                    is_minutes = attr_meta.get("minutes", False)
                    input_id = f"{instrument_name}_{attr}"
                    value = self.query_one(f"#{input_id}").value
                    field_type = self.get_field_type(config_class, attr)
                    if is_minutes and field_type is datetime.timedelta:
                        value = datetime.timedelta(minutes=float(value))
                    else:
                        value = field_type(value)
                    kwargs[attr] = value

                # TODO: the special handling does not seem to work for both instruments
                # TODO: in the ADCP case it causes an error, in the T/S case it saves but doesn't actually write anything...

                # special handling for onboard ADCP, conditional on whether it's selected by user in Switch (overwrite with None if switch is off)
                if instrument_name == "adcp_config":
                    has_adcp = self.query_one("#has_adcp", Switch).value
                    if has_adcp:  # determine max_depth_meter value based on sub-Switch selection by user, i.e. deep or shallow ADCP
                        if self.query_one("#adcp_deep", Switch).value:
                            kwargs["max_depth_meter"] = -1000.0
                        else:
                            kwargs["max_depth_meter"] = -150.0
                    else:
                        setattr(self.config, instrument_name, None)

                # special handling for onboard T/S, conditional on whether it's selected by user (overwrite with None if switch is off)
                if instrument_name == "ship_underwater_st_config":
                    has_ts = self.query_one("#has_onboard_ts", Switch).value
                    if not has_ts:
                        setattr(self.config, instrument_name, None)

                setattr(self.config, instrument_name, config_class(**kwargs))

            # save
            self.config.to_yaml(f"{self.path}/ship_config.yaml")
            return True

        except Exception as e:
            # write error log
            error_log_path = os.path.join(self.path, "virtualship_error.txt")
            with open(error_log_path, "w") as f:
                f.write("Error saving ship config:\n")
                traceback.print_exception(
                    type(e), e, e.__traceback__, file=f, chain=True
                )
                f.write("\n")

            raise UnexpectedError(
                "\n1) Please ensure that all entries are valid (all typed entry boxes must have green borders and no warnings).\n"
                "\n2) If the problem persists, please report this issue, with a description and the traceback, "
                "to the VirtualShip issue tracker at: https://github.com/OceanParcels/virtualship/issues"
            ) from None


class ScheduleScreen(Screen):
    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield ConfigEditor(self.path)
            yield ScheduleEditor(self.path)
            with Horizontal():
                yield Button("Save Changes", id="save_button", variant="success")
                yield Button("Exit", id="exit_button", variant="error")

    @on(Button.Pressed, "#exit_button")
    def exit_pressed(self) -> None:
        self.app.exit()

    @on(Button.Pressed, "#save_button")
    def save_pressed(self) -> None:
        """Save button press."""
        config_editor = self.query_one(ConfigEditor)
        schedule_editor = self.query_one(ScheduleEditor)

        try:
            config_saved = config_editor.save_changes()
            schedule_saved = schedule_editor.save_changes()

            if config_saved and schedule_saved:
                self.notify(
                    "Changes saved successfully", severity="information", timeout=20
                )

        except Exception as e:
            self.notify(
                f"*** Error saving changes ***:\n\n{e}\n\nTraceback will be logged in `{self.path}/virtualship_error.txt`. Please copy the file and/or its contents when submitting an issue.",
                severity="error",
                timeout=20,
            )
            return False


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
