import { expect, test } from "@playwright/test";

const mockItinerary = {
  destination: "北京",
  budget: 3000,
  total_cost: 980,
  summary: "北京 3 天历史文化测试行程。",
  generation_source: {
    kind: "test_mock",
    label: "E2E Mock SSE",
    detail: "前端端到端测试使用的固定 SSE 数据。",
    tools: ["mock_sse"],
    is_fallback: false,
  },
  days: [
    {
      day: 1,
      date: "第 1 天",
      weather: {
        condition: "晴",
        advice: "适合城市步行，注意补水。",
      },
      activities: [
        {
          time_slot: "09:00-11:00",
          place_name: "天安门广场",
          place_type: "景点",
          lng: 116.397,
          lat: 39.908,
          description: "从城市中轴线开始历史文化行程。",
          cost: 0,
          address: "北京市东城区东长安街",
          rating: 4.8,
          source: "高德 POI 验证",
          source_refs: ["POI: 天安门广场"],
          is_verified: true,
          warnings: [],
        },
      ],
    },
    {
      day: 2,
      date: "第 2 天",
      activities: [
        {
          time_slot: "14:00-16:00",
          place_name: "中国国家博物馆",
          place_type: "景点",
          lng: 116.401,
          lat: 39.905,
          description: "结合故宫和中轴线理解历史脉络。",
          cost: 0,
          address: "北京市东城区东长安街16号",
          rating: 4.7,
          source: "高德 POI 验证",
          source_refs: ["POI: 中国国家博物馆"],
          is_verified: true,
          warnings: [],
        },
      ],
    },
    {
      day: 3,
      date: "第 3 天",
      activities: [
        {
          time_slot: "09:00-12:00",
          place_name: "颐和园",
          place_type: "景点",
          lng: 116.273,
          lat: 39.999,
          description: "皇家园林作为行程收尾。",
          cost: 30,
          address: "北京市海淀区新建宫门路19号",
          rating: 4.8,
          source: "高德 POI 验证",
          source_refs: ["POI: 颐和园"],
          is_verified: true,
          warnings: [],
        },
      ],
    },
  ],
};

function sse(event: string, data: unknown) {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/chat", async (route) => {
    const body = [
      sse("thinking", { step: "正在分析您的旅行需求..." }),
      sse("source", {
        kind: "test_mock",
        label: "E2E Mock SSE",
        detail: "前端测试固定数据。",
        tools: ["mock_sse"],
      }),
      sse("content", {
        text: "已生成一版测试行程，右侧已同步行程卡片。",
      }),
      sse("itinerary", { itinerary: mockItinerary }),
      sse("done", {}),
    ].join("");

    await route.fulfill({
      body,
      contentType: "text/event-stream; charset=utf-8",
      status: 200,
    });
  });

  await page.route("**/api/v1/session/**", async (route) => {
    const request = route.request();
    if (request.method() === "DELETE") {
      await route.fulfill({
        body: JSON.stringify({ cleared: true, session_id: "mock-session" }),
        contentType: "application/json",
        status: 200,
      });
      return;
    }

    await route.fulfill({
      body: JSON.stringify({
        itinerary: null,
        message_count: 0,
        messages: [],
        session_id: "mock-session",
        updated_at: null,
        user_profile: null,
      }),
      contentType: "application/json",
      status: 200,
    });
  });
});

test("renders mock SSE itinerary and manages recent sessions", async ({ page }) => {
  await page.goto("/chat");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();

  await page.getByRole("button", { name: "北京3天历史文化路线" }).click();
  await page.getByRole("button", { name: "发送消息" }).click();

  await expect(page.getByText("已生成一版测试行程").first()).toBeVisible();
  await expect(page.getByText("行程概览")).toBeVisible();
  await expect(page.getByText("天安门广场").first()).toBeVisible();

  await page.reload();
  await expect(page.getByText("行程概览")).toBeVisible();
  await expect(page.getByText("天安门广场").first()).toBeVisible();

  await page.getByRole("button", { name: "历史会话" }).click();
  await expect(page.getByRole("dialog").getByText("北京行程")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "新建会话" }).click();
  await expect(page.getByText("还没有生成行程")).toBeVisible();

  await page.getByRole("button", { name: "历史会话" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /^北京行程/ }).click();
  await expect(page.getByText("行程概览")).toBeVisible();
  await expect(page.getByText("天安门广场").first()).toBeVisible();

  await page.getByRole("button", { name: "历史会话" }).click();
  await page.getByRole("button", { name: "删除 北京行程" }).click();
  await expect(page.getByRole("dialog").getByText("北京行程")).toHaveCount(0);
});
