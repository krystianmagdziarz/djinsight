import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict

from django.template.loader import render_to_string

from djinsight.models import PageViewStatistics, StatsQueryMixin


class BaseRenderer(ABC):
    def __init__(self, obj, metric, period, output, context, **kwargs):
        self.obj = obj
        self.metric = metric
        self.period = period
        self.output = output
        self.context = context
        self.kwargs = kwargs
        self.stats = PageViewStatistics.get_for_object(obj)

    @abstractmethod
    def render(self) -> str:
        pass

    def get_data(self) -> Dict[str, Any]:
        if not self.stats:
            return {}

        period_map = {
            "total": self._get_total_data,
            "today": self._get_today_data,
            "week": self._get_week_data,
            "month": self._get_month_data,
            "year": self._get_year_data,
            "custom": self._get_custom_data,
        }

        handler = period_map.get(self.period, self._get_total_data)
        return handler()

    def _get_total_data(self) -> Dict[str, Any]:
        return {
            "total_views": self.stats.total_views,
            "unique_views": self.stats.unique_views,
            "first_viewed_at": self.stats.first_viewed_at,
            "last_viewed_at": self.stats.last_viewed_at,
        }

    def _get_today_data(self) -> Dict[str, Any]:
        chart_data = self.output in ["chart", "widget"]
        views = StatsQueryMixin.get_views_today(self.obj, chart_data=chart_data)
        return {"views": views, "period": "today"}

    def _get_week_data(self) -> Dict[str, Any]:
        chart_data = self.output in ["chart", "widget"]
        views = StatsQueryMixin.get_views_week(self.obj, chart_data=chart_data)
        return {"views": views, "period": "week"}

    def _get_month_data(self) -> Dict[str, Any]:
        chart_data = self.output in ["chart", "widget"]
        views = StatsQueryMixin.get_views_month(self.obj, chart_data=chart_data)
        return {"views": views, "period": "month"}

    def _get_year_data(self) -> Dict[str, Any]:
        chart_data = self.output in ["chart", "widget"]
        views = StatsQueryMixin.get_views_year(self.obj, chart_data=chart_data)
        return {"views": views, "period": "year"}

    def _get_custom_data(self) -> Dict[str, Any]:
        start_date = self.kwargs.get("start_date")
        end_date = self.kwargs.get("end_date")
        if not start_date or not end_date:
            return {}

        unique = self.metric == "unique_views"
        views = self.stats.get_views_for_period(start_date, end_date, unique=unique)
        return {
            "views": views,
            "period": "custom",
            "start_date": start_date,
            "end_date": end_date,
        }


class DefaultWidgetRenderer(BaseRenderer):
    def render(self) -> str:
        data = self.get_data()
        if not data:
            return ""

        output_map = {
            "text": self._render_text,
            "chart": self._render_chart,
            "json": self._render_json,
            "widget": self._render_widget,
            "badge": self._render_badge,
        }

        renderer = output_map.get(self.output, self._render_text)
        return renderer(data)

    def _render_text(self, data: Dict[str, Any]) -> str:
        value = data.get(self.metric)
        if value is not None:
            return str(value)

        if self.period == "total":
            return str(data.get("total_views", 0))
        return str(data.get("views", 0))

    def _render_chart(self, data: Dict[str, Any]) -> str:
        from djinsight.conf import djinsight_settings

        chart_renderer_class = djinsight_settings.get_chart_renderer()
        chart_renderer = chart_renderer_class(
            data=data,
            chart_type=self.kwargs.get("chart_type", "line"),
            chart_color=self.kwargs.get("chart_color"),
            chart_id=f"chart-{uuid.uuid4().hex[:8]}",
        )
        return chart_renderer.render()

    def _render_json(self, data: Dict[str, Any]) -> str:
        return json.dumps(data)

    def _render_widget(self, data: Dict[str, Any]) -> str:
        return render_to_string(
            "djinsight/widgets/stats_widget.html",
            {
                "data": data,
                "obj": self.obj,
                "metric": self.metric,
                "period": self.period,
                "stats": self.stats,
            },
        )

    def _render_badge(self, data: Dict[str, Any]) -> str:
        return render_to_string(
            "djinsight/widgets/stats_badge.html",
            {
                "data": data,
                "obj": self.obj,
                "metric": self.metric,
                "period": self.period,
            },
        )


class DefaultChartRenderer:
    def __init__(self, data, chart_type="line", chart_color=None, chart_id=None):
        self.data = data
        self.chart_type = chart_type
        self.chart_color = chart_color or "#007bff"
        self.chart_id = chart_id or f"chart-{uuid.uuid4().hex[:8]}"
        self.chart_data_json = json.dumps(data.get("views", []))

    def render(self) -> str:
        views_data = self.data.get("views", [])
        if not isinstance(views_data, list):
            return ""

        return render_to_string(
            "djinsight/charts/default_chart.html",
            {
                "chart_data": self.chart_data_json,
                "chart_type": self.chart_type,
                "chart_color": self.chart_color,
                "chart_id": self.chart_id,
            },
        )
