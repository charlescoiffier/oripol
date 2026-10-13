import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const html = readFileSync(new URL("./app.html", import.meta.url), "utf8");

describe("statistiques de visite (Umami)", () => {
  it("la balise est présente, limitée à oripol.charlescoiffier.fr et respecte Do Not Track", () => {
    const tag = html.match(/<script[^>]*src="https:\/\/stats\.charlescoiffier\.fr\/script\.js"[^>]*>/);
    expect(tag).not.toBeNull();
    expect(tag![0]).toMatch(/\bdefer\b/);
    expect(tag![0]).toContain('data-website-id="7c657023-5cc9-4551-9738-ff6460a115cb"');
    expect(tag![0]).toContain('data-domains="oripol.charlescoiffier.fr"');
    expect(tag![0]).toContain('data-do-not-track="true"');
  });
});
