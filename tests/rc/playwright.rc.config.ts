// Предрелизный ручной проход (RC): полная игра и обход всех вымышленных страниц со скриншотами.
// Запуск (после build + dump-answers, сервер на :8000):
//   RC_SHOTS=<папка> PW_CHROMIUM_PATH=... npx playwright test -c tests/rc/playwright.rc.config.ts --workers=1
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: /rc_.*\.spec\.ts$/,
  timeout: 600_000,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:8000" },
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
