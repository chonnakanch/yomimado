// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { BubbleTranslation } from "./BubbleTranslation";

afterEach(() => vi.restoreAllMocks());

it("shrinks text only to a readable minimum and uses an explicit overflow marker instead of truncating the sentence", async () => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(60);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(40);
  vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(52);
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(
    function (this: HTMLElement) {
      return Number.parseInt(this.style.fontSize) >= 14 ? 50 : 30;
    },
  );
  const container = document.createElement("div");
  const root = createRoot(container);
  const render = (text: string) =>
    root.render(
      <svg>
        <BubbleTranslation
          text={text}
          bounds={{ x: 0, y: 0, width: 60, height: 40 }}
          elementRef={() => {}}
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
  ).toContain("Click to read in the learning popup");
  expect(container.querySelector("span")?.textContent).toBe(
    "A much longer sentence that cannot possibly fit.",
  );
  await act(async () => root.unmount());
});
