import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../../shared/api/client";
import { useUser } from "../../auth/context/SessionContext";
import { Empty, ErrorBox, Heading, Loading } from "../../../shared/ui";
import { duration } from "../../../shared/utils/format";
import { statuses, type Analytics, type Status } from "../../../shared/types";

/** Відображає обчислені Backend агрегати для доступних користувачу документів. */
export function AnalyticsPage() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const data = useQuery({
    // Період — частина ключа; після операцій із документами скидаємо весь prefix.
    queryKey: ["analytics", from, to],
    queryFn: () => api<Analytics>(`analytics/?date_from=${from}&date_to=${to}`),
  });
  const user = useUser();
  const a = data.data;
  return (
    <>
      <Heading
        title="Огляд робочого простору"
        description={`Вітаємо, ${user.first_name || user.username}. ${user.role === "teacher" ? "Тут зібрано ваші документи." : "Стан документообігу кафедри в одному місці."}`}
      >
        <Link className="button primary" to="/templates">
          ＋ Створити документ
        </Link>
      </Heading>
      <ErrorBox error={data.error} />
      {data.isLoading ? (
        <Loading />
      ) : (
        a && (
          <>
            <div className="stats-grid">
              {[
                ["Усього документів", a.total, "Доступні вашій ролі"],
                [
                  "Очікують погодження",
                  a.pending_approval,
                  "Потребують рішення",
                ],
                [
                  "Завершено за період",
                  a.completed_in_period,
                  "У вибраному проміжку",
                ],
                [
                  "Середній цикл",
                  a.average_cycle_seconds === null
                    ? "—"
                    : duration(a.average_cycle_seconds),
                  "Для завершених документів",
                ],
              ].map(([label, value, hint]) => (
                <section className="panel stat" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                  <small>{hint}</small>
                </section>
              ))}
            </div>
            <div className="period panel">
              <strong>Період аналітики</strong>
              <label>
                Від
                <input
                  type="date"
                  value={from}
                  onChange={(e) => setFrom(e.target.value)}
                />
              </label>
              <label>
                До
                <input
                  type="date"
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                />
              </label>
            </div>
            <div className="charts">
              <section className="panel">
                <h2>Розподіл за статусами</h2>
                <p className="muted small">Усі доступні документи</p>
                <div className="status-chart">
                  {Object.entries(statuses).map(([key, label]) => (
                    <div key={key}>
                      <div>
                        <span>{label}</span>
                        <strong>{a.by_status[key as Status] || 0}</strong>
                      </div>
                      <div className="bar-track">
                        <div
                          className={`bar ${key}`}
                          style={{
                            width: `${a.total ? ((a.by_status[key as Status] || 0) / a.total) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
              <section className="panel">
                <h2>Динаміка створення</h2>
                <p className="muted small">Кількість документів за датою</p>
                {a.creation_trend.length ? (
                  <div
                    className="trend"
                    role="img"
                    aria-label={a.creation_trend
                      .map((item) => `${item.date}: ${item.count}`)
                      .join(", ")}
                  >
                    {a.creation_trend.map((item) => (
                      <div className="trend-item" key={item.date}>
                        <strong>{item.count}</strong>
                        <div
                          style={{
                            height: `${20 + (item.count / Math.max(...a.creation_trend.map((x) => x.count))) * 120}px`,
                          }}
                        />
                        <small>{item.date.slice(5)}</small>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty>За цей період документів ще немає.</Empty>
                )}
              </section>
            </div>
            <section className="panel quick-start">
              <div>
                <h2>Почніть із готового шаблону</h2>
                <p className="muted">
                  Заяви, протоколи, звіти та інші документи — зі збереженням
                  історії.
                </p>
              </div>
              <Link className="button" to="/templates">
                Відкрити бібліотеку →
              </Link>
            </section>
          </>
        )
      )}
    </>
  );
}
