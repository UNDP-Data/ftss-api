"""
Utility classes that define valid string options.
"""

from enum import StrEnum

__all__ = [
    "Role",
    "Status",
    "Steep",
    "Signature",
    "Goal",
    "Score",
    "Horizon",
    "Rating",
    "Bureau",
]


class Role(StrEnum):
    """
    User roles for RBAC. Admins, curators and users are actual users logged in
    to the platform who authenticate via JWT. Visitor role is assigned to
    a dummy user authenticated with an API key.
    """

    ADMIN = "Admin"  # curator + can change the roles of other users
    CURATOR = "Curator"  # user + can edit and approve signals and trends
    USER = "User"  # visitor + can submit signals
    VISITOR = "Visitor"  # can only view signals and trends


class Status(StrEnum):
    """Signal/trend review statuses."""

    DRAFT = "Draft"
    NEW = "New"
    APPROVED = "Approved"
    ARCHIVED = "Archived"


class Steep(StrEnum):
    """Categories in terms of Steep-V methodology."""

    SOCIAL = "Social – Issues related to human culture, demography, communication, movement and migration, work and education"
    TECHNOLOGICAL = "Technological – Made culture, tools, devices, systems, infrastructure and networks"
    ECONOMIC = "Economic – Issues of value, money, financial tools and systems, business and business models, exchanges and transactions"
    ENVIRONMENTAL = "Environmental – The natural world, living environment, sustainability, resources, climate and health"
    POLITICAL = "Political – Legal issues, policy, governance, rules and regulations and organizational systems"
    VALUES = "Values – Ethics, spirituality, ideology or other forms of values"


class Signature(StrEnum):
    """The six Signature Solutions of the United Nations Development Programme."""

    POVERTY = "Poverty and Inequality"
    GOVERNANCE = "Governance"
    RESILIENCE = "Resilience"
    ENVIRONMENT = "Environment"
    ENERGY = "Energy"
    GENDER = "Gender Equality"
    # 3 enables
    INNOVATION = "Strategic Innovation"
    DIGITALISATION = "Digitalisation"
    FINANCING = "Development Financing"


class Goal(StrEnum):
    """The 17 United Nations Sustainable Development Goals."""

    G1 = "GOAL 1: No Poverty"
    G2 = "GOAL 2: Zero Hunger"
    G3 = "GOAL 3: Good Health and Well-being"
    G4 = "GOAL 4: Quality Education"
    G5 = "GOAL 5: Gender Equality"
    G6 = "GOAL 6: Clean Water and Sanitation"
    G7 = "GOAL 7: Affordable and Clean Energy"
    G8 = "GOAL 8: Decent Work and Economic Growth"
    G9 = "GOAL 9: Industry, Innovation and Infrastructure"
    G10 = "GOAL 10: Reduced Inequality"
    G11 = "GOAL 11: Sustainable Cities and Communities"
    G12 = "GOAL 12: Responsible Consumption and Production"
    G13 = "GOAL 13: Climate Action"
    G14 = "GOAL 14: Life Below Water"
    G15 = "GOAL 15: Life on Land"
    G16 = "GOAL 16: Peace and Justice Strong Institutions"
    G17 = "GOAL 17: Partnerships to achieve the Goal"


class Score(StrEnum):
    """Signal novelty scores."""

    ONE = "1 — Non-novel (known, but potentially notable in particular context)"
    TWO = "2"
    THREE = "3 — Potentially novel or uncertain, but not clear in its potential impact"
    FOUR = "4"
    FIVE = "5 — Something that introduces or points to a potentially interesting or consequential change in direction of trends"


class Horizon(StrEnum):
    """Trend impact horizons."""

    SHORT = "Horizon 1 (0-3 years)"
    MEDIUM = "Horizon 2 (3-7 years)"
    LONG = "Horizon 3 (7-10 years)"


class Rating(StrEnum):
    """Trend impact rating."""

    LOW = "1 – Low"
    MODERATE = "2 – Moderate"
    HIGH = "3 – Significant"


class Bureau(StrEnum):
    """Bureaus of the United Nations Development Programme."""

    RBA = "RBA"
    RBAP = "RBAP"
    RBAS = "RBAS"
    RBEC = "RBEC"
    RBLAC = "RBLAC"
