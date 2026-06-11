import { describe, expect, it } from "vitest";

import { slugify } from "./index";

describe("slugify", () => {
  it("turns a title into a url slug", () => {
    expect(slugify("Hello, World!")).toBe("hello-world");
  });
});
