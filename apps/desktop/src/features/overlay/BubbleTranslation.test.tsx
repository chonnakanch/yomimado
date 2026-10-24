// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { BubbleTranslation } from "./BubbleTranslation";

afterEach(() => vi.restoreAllMocks());

it("keeps overflowing translations available to scroll at a readable minimum", async () => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(60);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(40);
  vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(52);
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(
    function (this: HTMLElement) {
      return Number.parseInt(this.style.fontSize) >= 14 ? 50 : 20;
    },
  );
  const container = document.createElement("div");
  const root = createRoot(container);
  const activate = vi.fn();
  const render = (text: string) =>
    root.render(
      <svg>
        <BubbleTranslation
          text={text}
          bounds={{ x: 0, y: 0, width: 60, height: 40 }}
          elementRef={() => {}}
          onActivate={activate}
          needsReview
          selected
        />
      </svg>,
    );
  await act(async () => render("School tomorrow."));
  expect(container.querySelector("span")?.style.fontSize).toBe("13px");
  expect(container.querySelector(".is-overflowing")).toBeNull();
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(500);
  await act(async () =>
    render("A much longer sentence that cannot possibly fit."),
  );
  expect(container.querySelector("span")?.style.fontSize).toBe("11px");
  expect(
    container.querySelector(".is-overflowing")?.getAttribute("title"),
  ).toContain("Scroll to read more");
  expect(container.querySelector("span")?.textContent).toBe(
    "A much longer sentence that cannot possibly fit.",
  );
  expect(container.querySelector("span")?.hidden).toBe(false);
  expect(container.querySelector(".needs-review.active")).not.toBeNull();
  container.querySelector<HTMLElement>(".bubble-translation-text")!.click();
  expect(activate).toHaveBeenCalledOnce();
  await act(async () => root.unmount());
});

it("uses available width and height before shrinking the font, and keeps short text compact", async () => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(
    function (this: HTMLElement) {
      return Number.parseFloat(this.style.width) - 4;
    },
  );
  vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(30);
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(
    function (this: HTMLElement) {
      if (this.textContent === "Hi.") return 22;
      return Number.parseFloat(this.parentElement!.style.width) >= 140
        ? 90
        : 180;
    },
  );
  const container = document.createElement("div");
  const root = createRoot(container);
  const render = (text: string) =>
    root.render(
      <svg>
        <BubbleTranslation
          text={text}
          bounds={{ x: 50, y: 50, width: 50, height: 40 }}
          availableBounds={{ x: 0, y: 0, width: 150, height: 160 }}
          elementRef={() => {}}
          onActivate={() => {}}
        />
      </svg>,
    );
  await act(async () =>
    render("We should gather the remaining members together."),
  );
  const panel = container.querySelector("foreignObject")!;
  expect(panel.getAttribute("width")).toBe("150");
  expect(panel.getAttribute("height")).toBe("102");
  expect(container.querySelector("span")!.style.fontSize).toBe("18px");
  expect(container.querySelector(".is-overflowing")).toBeNull();
  await act(async () => render("Hi."));
  expect(panel.getAttribute("width")).toBe("50");
  expect(panel.getAttribute("height")).toBe("40");
  await act(async () => root.unmount());
});
