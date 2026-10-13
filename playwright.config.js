// Сквозные тесты: tests/e2e/, против уже запущенного `python -m engine serve`
// (после `python -m engine build`). Сами тесты появятся в P08.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  use: {
    // Порт можно сменить: E2E_BASE_URL=http://127.0.0.1:8765 (несколько серверов параллельно).
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:8000",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Необязательно: свой Chromium вместо скачанного `playwright install`
        // (например, предустановленный в облачном окружении).
        ...(process.env.PW_CHROMIUM_PATH
          ? { launchOptions: { executablePath: process.env.PW_CHROMIUM_PATH } }
          : {}),
      },
    },
  ],
});
