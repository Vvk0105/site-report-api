from enum import Enum


class ReportStatus(str, Enum):

    DRAFT = "draft"

    COMPLETED = "completed"