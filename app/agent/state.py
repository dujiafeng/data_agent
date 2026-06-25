from typing import TypedDict

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class ColumnInfoState(TypedDict):
    name: str
    type: str
    role: str
    examples: list[str]
    description: str
    alias: list[str]


class TableInfoState(TypedDict):
    name: str
    role: str
    description: str
    columns: list[ColumnInfoState]


class MetricInfoState(TypedDict):
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


class DataAgentState(TypedDict):
    query: str  # 用户输入的查询
    keywords: list[str]  # 抽取的关键词

    # 召回之后的信息
    retrieved_column_infos: list[ColumnInfo]  # 检索到的字段信息
    retrieved_metric_infos: list[MetricInfo]  # 检索到的指标信息
    retrieved_value_infos: list[ValueInfo]  # 检索到的关键词召回信息

    # 合并之后信息
    table_infos: list[TableInfoState]
    metric_infos: list[MetricInfoState]

    error: str  # 校验SQL时出现的错误信息
