"""Risk rule registry (evaluated in ``order``)."""

from app.risk.base import RiskRule
from app.risk.rules.capital import (
    BuyingPowerRule,
    ConfidenceRule,
    RewardRiskRule,
    StopLossRule,
)
from app.risk.rules.exposure import (
    AssetClassExposureRule,
    OpenPositionsRule,
    PortfolioExposureRule,
    PositionLimitRule,
    SectorExposureRule,
)
from app.risk.rules.loss import DailyLossRule, DrawdownRule, TradeFrequencyRule
from app.risk.rules.system import MarketFreshnessRule, RequestValidityRule, TradingStateRule


def default_rules() -> list[RiskRule]:
    rules: list[RiskRule] = [
        TradingStateRule(),
        MarketFreshnessRule(),
        RequestValidityRule(),
        BuyingPowerRule(),
        StopLossRule(),
        RewardRiskRule(),
        PositionLimitRule(),
        PortfolioExposureRule(),
        OpenPositionsRule(),
        SectorExposureRule(),
        AssetClassExposureRule(),
        DailyLossRule(),
        DrawdownRule(),
        TradeFrequencyRule(),
        ConfidenceRule(),
    ]
    return sorted(rules, key=lambda rule: rule.order)


__all__ = [
    "AssetClassExposureRule",
    "BuyingPowerRule",
    "ConfidenceRule",
    "DailyLossRule",
    "DrawdownRule",
    "MarketFreshnessRule",
    "OpenPositionsRule",
    "PortfolioExposureRule",
    "PositionLimitRule",
    "RequestValidityRule",
    "RewardRiskRule",
    "SectorExposureRule",
    "StopLossRule",
    "TradeFrequencyRule",
    "TradingStateRule",
    "default_rules",
]
