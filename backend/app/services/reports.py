"""Экспорт отчетности в .pdf и .xlsx."""
import io
from openpyxl import Workbook

ALLOWED = {"pdf", "xlsx"}

class ReportError(ValueError): ...

def build_xlsx(metrics: dict, points: list[dict], bt) -> bytes:
    wb = Workbook()
    ws = wb.active; ws.title = "Метрики"
    ws.append(["Показатель", "Значение"])
    for k in ("period_start", "period_end", "dau", "mau", "avg_session_sec", "peak_hour", "is_overload"):
        ws.append([k, metrics.get(k)])
    ws2 = wb.create_sheet("Прогноз")
    ws2.append(["Дата", "Прогноз", "Риск перегрузки"])
    for p in points:
        ws2.append([p["date"], p["value"], p["is_overload_risk"]])
    ws2.append([]); ws2.append(["MAPE, %", bt.mape]); ws2.append(["RMSE", bt.rmse])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()
    
def build_pdf(metrics: dict, points: list[dict], bt, history: list[float],
              history_dates: list[str]) -> bytes:
    import matplotlib; matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(10, 5))
        # Ось X — реальные даты, а не индексы 0, 1, 2...
        ax.plot(history_dates, history, label="История (с интерполяцией аномалий)")
        # Для прогноза генерируем даты, идущие сразу после последней даты истории
        forecast_dates = [points[i]["date"] for i in range(len(points))]
        ax.plot(forecast_dates,
                [p["value"] for p in points], "o--", label="Прогноз")
        for i, p in enumerate(points):
            if p["is_overload_risk"]:
                ax.axvline(forecast_dates[i], color="red", alpha=0.35)
        ax.set_title(f"Прогноз активности, MAPE={bt.mape}% / RMSE={bt.rmse}")
        ax.legend(); fig.autofmt_xdate(); fig.tight_layout()
        pdf.savefig(fig); plt.close(fig)

        fig2, ax2 = plt.subplots(figsize=(8, 4)); ax2.axis("off")
        ax2.table(cellText=[[p["date"], p["value"], "да" if p["is_overload_risk"] else "нет"] for p in points],
                  colLabels=["Дата", "Прогноз", "Перегрузка"], loc="center")
        pdf.savefig(fig2); plt.close(fig2)
    return buf.getvalue()