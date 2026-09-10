import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "../src/app/page";

describe("HomePage", () => {
  it("renders the application name", () => {
    const html = renderToStaticMarkup(<HomePage />);

    expect(html).toContain("CyVerse Internal Tools");
  });
});
