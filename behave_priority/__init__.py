"""behave-priority: Priority-based execution for Behave BDD."""

import logging

from behave_priority.config import PriorityConfig, ReportFormat
from behave_priority.exceptions import (
    PriorityError,
    PriorityParseError,
)
from behave_priority.hooks import (
    after_scenario_hook,
    before_scenario_hook,
    cleanup_parallel_coord,
    get_report,
    priority_report,
    setup_priority,
)
from behave_priority.parallel import (
    ParallelCoordinator,
    cleanup_coordinator,
    create_coordinator,
)
from behave_priority.parser import (
    is_critical,
    parse_feature_priority,
    parse_priority,
    resolve_priority,
)
from behave_priority.report import PriorityReport, ReportEntry, ReportSummary
from behave_priority.sorter import ScenarioSorter

logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "1.0.0"

__all__ = [
    "PriorityConfig",
    "ReportFormat",
    "parse_priority",
    "parse_feature_priority",
    "resolve_priority",
    "is_critical",
    "ScenarioSorter",
    "setup_priority",
    "before_scenario_hook",
    "after_scenario_hook",
    "get_report",
    "priority_report",
    "cleanup_parallel_coord",
    "ParallelCoordinator",
    "cleanup_coordinator",
    "create_coordinator",
    "PriorityReport",
    "ReportEntry",
    "ReportSummary",
    "PriorityError",
    "PriorityParseError",
    "__version__",
]
