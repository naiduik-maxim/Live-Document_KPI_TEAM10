/** Пагінація списків API з типовим page_size=20; навігація належить сторінці. */
export function Pagination({
  page,
  count,
  onChange,
}: {
  page: number;
  count: number;
  onChange: (page: number) => void;
}) {
  return (
    <div className="pagination">
      <span>Усього: {count}</span>
      <div>
        <button disabled={page <= 1} onClick={() => onChange(page - 1)}>
          ← Назад
        </button>
        <span>
          Сторінка {page} / {Math.max(1, Math.ceil(count / 20))}
        </span>
        <button
          disabled={page * 20 >= count}
          onClick={() => onChange(page + 1)}
        >
          Далі →
        </button>
      </div>
    </div>
  );
}
