// @vitest-environment jsdom
import { beforeEach, expect, it } from "vitest";
import {
  readReadingOrderEnabled,
  saveReadingOrderEnabled,
} from "./reading-order-setting";

beforeEach(() => window.localStorage.clear());

it("keeps reading-order controls off until explicitly enabled", () => {
  expect(readReadingOrderEnabled()).toBe(false);
  saveReadingOrderEnabled(true);
  expect(readReadingOrderEnabled()).toBe(true);
  saveReadingOrderEnabled(false);
  expect(readReadingOrderEnabled()).toBe(false);
});
