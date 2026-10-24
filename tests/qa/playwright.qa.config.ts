// Отдельный конфиг независимой проверки (QA). Не входит в общий testDir (tests/e2e).
// Запуск из корня репозитория, после build + dump-answers и `python -m engine serve --port <P>`:
//   E2E_BASE_URL=http://127.0.0.1:<P> PW_CHROMIUM_PATH=... npx playwright test -c tests/qa/playwright.qa.config.ts [файл]
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: /qa_.*\.spec\.ts$/,
  timeout: 300_000,
  workers: Number(process.env.QA_WORKERS || 3),
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:8771",
    // Зависшее действие (локатора нет на странице) падает за 20 с, а не за таймаут теста (5 мин).
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ...(process.env.PW_CHROMIUM_PATH ? { launchOptions: { executablePath: process.env.PW_CHROMIUM_PATH } } : {}),
      },
    },
  ],
});
