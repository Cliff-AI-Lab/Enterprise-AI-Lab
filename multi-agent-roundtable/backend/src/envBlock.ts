function nowInTimeZone(tz: string, now: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: tz,
    year: "numeric",
    month: "numeric",
    day: "numeric",
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(now);
  const pick = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${pick("year")}年${pick("month")}月${pick("day")}日 ${pick("weekday")} ${pick("hour")}:${pick("minute")} (${tz})`;
}

export function buildEnvBlock(): string {
  const tz = process.env.TELEGRAM_AGENT_TZ ?? "Asia/Shanghai";
  return [
    "<env>",
    `当前时间: ${nowInTimeZone(tz)}`,
    "</env>",
    "",
    "被问到日期 / 时间 / 星期时，按 <env> 里的值回答，不要凭训练记忆猜。",
  ].join("\n");
}
