/** Показує ISO-час сервера в Europe/Kyiv незалежно від часового поясу пристрою. */
export const date = (value: string) =>
  new Intl.DateTimeFormat("uk-UA", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Kyiv",
  }).format(new Date(value));
/** Форматує серверний age_seconds; для completed його вже зупинив Backend. */
export const duration = (seconds: number) =>
  seconds < 60
    ? "менше хвилини"
    : seconds < 86400
      ? `${Math.floor(seconds / 3600)} год ${Math.floor((seconds % 3600) / 60)} хв`
      : `${Math.floor(seconds / 86400)} дн ${Math.floor((seconds % 86400) / 3600)} год`;
