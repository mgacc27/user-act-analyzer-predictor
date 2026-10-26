import { useEffect, useState } from "react";
import { ResponsiveContainer, ComposedChart, Line, XAxis, YAxis,
         CartesianGrid, Tooltip, Legend, ReferenceDot } from "recharts";
import { api } from "./api";

export default function Dashboard() {
  const [data, setData] = useState([]);
  const [m, setM] = useState(null);
  const [fc, setFc] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = async () => {
    try {
      const [hist, forecast, metrics] = await Promise.all(
        [api.history(), api.forecast(14), api.metrics()]);
      setM(metrics); setFc(forecast);
      const map = new Map(hist.map((p) => [p.date, { ...p }]));
      forecast.points.forEach((p) => map.set(p.date,
        { ...map.get(p.date), date: p.date, forecast: p.value, overload: p.is_overload_risk }));
      setData([...map.values()].sort((a, b) => a.date.localeCompare(b.date)));
    } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  const onImport = async (e) => {
    setError(""); setNotice("");
    try { const r = await api.importLogs(e.target.files[0]);
      setNotice(`Импортировано записей: ${r.imported}, помечено аномалий: ${r.anomalies_marked}`);
      await load();
    } catch (err) { setError(err.message); }      
  };
  const onExport = async (fmt) => {
    const blob = await api.report(fmt);
    const a = Object.assign(document.createElement("a"),
      { href: URL.createObjectURL(blob), download: `report.${fmt}` });
    a.click();
  };

  return (
    <main style={{ minWidth: 1280, padding: 16 }}>
      <h1>Панель аналитики пользовательской активности Голяков ПИбп-2206е</h1>
      {m && <section className="kpi">
        <b>DAU:</b> {m.dau} | <b>MAU:</b> {m.mau} | <b>Сессия, с:</b> {m.avg_session_sec ?? "—"} |
        <b style={{ color: fc?.is_acceptable ? "green" : "red" }}>
          MAPE: {fc?.mape}% (цель ≤ 8%)</b> | RMSE: {fc?.rmse}
      </section>}
      {error && <p role="alert" style={{ color: "crimson" }}>Ошибка: {error}</p>}
      {notice && <p style={{ color: "green" }}>{notice}</p>}
      <input type="file" accept=".csv,.json" onChange={onImport} />
      <button onClick={() => onExport("pdf")}>Скачать PDF</button>
      <button onClick={() => onExport("xlsx")}>Скачать XLSX</button>
      <ResponsiveContainer width="100%" height={420}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="value" name="История" stroke="#1f77b4" dot={false} />
          <Line type="monotone" dataKey="forecast" name="Прогноз (14 дней)"
                stroke="#ff7f0e" strokeDasharray="6 3" connectNulls />
          {data.filter((d) => d.overload).map((d) =>
            <ReferenceDot key={d.date} x={d.date} y={d.forecast} r={6} fill="red" />)}
        </ComposedChart>
      </ResponsiveContainer>
    </main>
  );
}